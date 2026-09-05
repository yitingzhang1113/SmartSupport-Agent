# Licensed under the MIT License

"""A module containing load method for PDF files."""

import logging
import re
from pathlib import Path
import tempfile
import base64
import requests
from tqdm import tqdm
import zipfile
import os

import pandas as pd
from io import BytesIO

from graphrag.config.models.input_config import InputConfig
from graphrag.index.utils.hashing import gen_sha512_hash
from graphrag.index.input.util import load_files, generate_image_descriptions, generate_image_descriptions_sync
from graphrag.logger.base import ProgressLogger
from graphrag.storage.pipeline_storage import PipelineStorage

log = logging.getLogger(__name__)


def to_b64(file_path):
    try:
        with open(file_path, 'rb') as f:
            return base64.b64encode(f.read()).decode('utf-8')
    except Exception as e:
        raise Exception(f'File: {file_path} - Info: {e}')


def do_parse(file_path, url=None, **kwargs):
    try:
        if url:
            if not url.endswith('/'):
                url = url + '/'
            url = url + 'predict'

        response = requests.post(url, json={
            'file': to_b64(file_path),
            'kwargs': kwargs
        })

        if response.status_code == 200:
            output = response.json()
            output['file_path'] = file_path
            return output
        else:
            raise Exception(response.text)
    except Exception as e:
        log.error(f'File: {file_path} - Info: {e}')
        return None


async def download_output_files(url:str, output_dir:str, local_dir:str, doc_id:str):
    try:
        local_dir_path = Path(local_dir) / doc_id

        if url:
            if not url.endswith('/'):
                url = url + '/'
            url = url + 'download_output_files'

        clean_output_dir = output_dir.rstrip('/')

        full_path = f"{clean_output_dir}/{doc_id}"

        response = requests.get(url, params={'output_dir': full_path})
        
        if response.status_code == 200:
            with tempfile.NamedTemporaryFile(delete=False, suffix='.zip') as temp_file:
                temp_file.write(response.content)
                zip_path = temp_file.name

            zip_size = os.path.getsize(zip_path)
            
            if zip_size > 0:
                local_dir_path.mkdir(parents=True, exist_ok=True)

                temp_extract_dir = local_dir_path / "_temp_extract"
                temp_extract_dir.mkdir(parents=True, exist_ok=True)

                with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                    zip_ref.extractall(temp_extract_dir)

                auto_dir = None
                for root, dirs, files in os.walk(temp_extract_dir):
                    if os.path.basename(root) == "auto":
                        auto_dir = Path(root)
                        break
                
                if auto_dir and auto_dir.exists():
                    target_auto_dir = local_dir_path / "auto"
                    target_auto_dir.mkdir(parents=True, exist_ok=True)

                    import shutil
                    for item in auto_dir.iterdir():
                        if item.is_file():
                            shutil.copy2(item, target_auto_dir)
                        elif item.is_dir():
                            shutil.copytree(item, target_auto_dir / item.name, dirs_exist_ok=True)
                else:
                    for item in temp_extract_dir.iterdir():
                        if item.is_file():
                            shutil.copy2(item, local_dir_path)
                        elif item.is_dir() and item.name != "_temp_extract":
                            shutil.copytree(item, local_dir_path / item.name, dirs_exist_ok=True)
                
                shutil.rmtree(temp_extract_dir, ignore_errors=True)

                os.unlink(zip_path)
                
                return True
            else:
                os.unlink(zip_path)
        
        local_dir_path.mkdir(parents=True, exist_ok=True)

        with open(local_dir_path / "download_failed.txt", "w") as f:
            f.write(f"Download failure time: {pd.Timestamp.now().isoformat()}\n")
            f.write(f"Attempted path: {full_path}\n")
            f.write(f"Error message: Status code {response.status_code}\n")
        return False

    except Exception as e:
        import traceback

        log.error(traceback.format_exc())

        local_dir_path = Path(local_dir) / doc_id
        local_dir_path.mkdir(parents=True, exist_ok=True)

        with open(local_dir_path / "download_error.txt", "w") as f:
            f.write(f"Download error time: {pd.Timestamp.now().isoformat()}\n")
            f.write(f"Error message: {str(e)}\n")
            f.write(traceback.format_exc())
        
        return False


async def load_pdf(
    config: InputConfig,
    progress: ProgressLogger | None,
    storage: PipelineStorage,
) -> pd.DataFrame:
    """Load PDF inputs from a directory using remote parsing service."""

    if hasattr(config, "local_output_dir") and config.local_output_dir:
        local_output_dir = Path(config.local_output_dir)
    else:
        local_output_dir = Path("./pdf_outputs")

    local_output_dir.mkdir(parents=True, exist_ok=True)
    
    async def load_file(path: str, group: dict | None) -> pd.DataFrame:
        if group is None:
            group = {}
        try:
            buffer = BytesIO(await storage.get(path, as_bytes=True))

            with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as temp_file:
                temp_file.write(buffer.getvalue())
                file_path = temp_file.name

            result = do_parse(file_path, url=config.mineru_api_url)
            
            if not result or 'output_dir' not in result:
                data = pd.DataFrame([{
                    "text": f"[Parsing failed] {path}",
                    "title": Path(path).name,
                    "id": path
                }])
                return data

            output_dir = result['output_dir']
            if not output_dir.endswith('/auto'):
                output_dir = f"{output_dir}/auto"

            id_match = re.search(r'\/([^\/]+)\/auto$', output_dir)
            doc_id = id_match.group(1) if id_match else path

            doc_local_dir = local_output_dir / doc_id
            doc_local_dir.mkdir(parents=True, exist_ok=True)

            metadata = {
                "file_path": path,
                "output_dir": output_dir,
                "parse_time": pd.Timestamp.now().isoformat(),
                "doc_id": doc_id
            }
                
            try:
                download_success = await download_output_files(config.mineru_api_url, config.mineru_output_dir, config.local_output_dir, doc_id)
                metadata["local_output_dir"] = str(doc_local_dir)
                    
                if download_success:
                    auto_dir = doc_local_dir / "auto"
                    md_file_path = None
                    content_list_path = None

                    md_file_path = auto_dir / f"{doc_id}.md"

                    content_list_path = auto_dir / f"{doc_id}_content_list.json"

                    if md_file_path and md_file_path.exists():
                        try:
                            with open(md_file_path, 'r', encoding='utf-8') as md_file:
                                text_content = md_file.read()
                        except Exception as e:
                            log.error(f"读取MD文件失败: {str(e)}")
                            text_content = f"[读取MD文件失败] {path}: {str(e)}"
                    else:
                        log.error(f"MD文件不存在: {md_file_path}")
                        text_content = f"[MD文件不存在] {path}"
                else:
                    text_content = f"[下载文件失败] {path}"

                parse_content = {}

                parse_content['markdown_text'] = text_content

                data = pd.DataFrame([{
                    "text": text_content,
                    "title": Path(path).name,
                    "id": doc_id
                }])

                structured_info = await extract_tables_from_model_json(auto_dir if auto_dir.exists() else doc_local_dir, doc_id)

                if structured_info and structured_info.get("tables") and config.table_description_api_key and config.table_description_model:
                    structured_info = generate_descriptions_for_tables(auto_dir if auto_dir.exists() else doc_local_dir, structured_info, config)

                image_info = None
                if content_list_path and content_list_path.exists():
                    image_info = extract_images_from_content_list(auto_dir if auto_dir.exists() else doc_local_dir, doc_id)
                else:
                    log.error(f"content_list.json文件不存在: {content_list_path}")

                if image_info and image_info.get("images") and config.image_description_api_key and config.image_description_model:
                    image_info = generate_descriptions_for_images(auto_dir if auto_dir.exists() else doc_local_dir, image_info, config)

                enhanced_text = enhance_markdown_with_metadata(text_content, structured_info, image_info)

                data["text"] = [enhanced_text]

                content_elements = []

                if structured_info and structured_info.get("tables"):
                    for table in structured_info["tables"]:
                        content_elements.append({
                            "type": "table",
                            "page": table.get("page", 0),
                            "element_idx": table.get("table_idx", 0),
                            "html": table.get("html", ""),
                            "description": table.get("description", "")
                        })

                if image_info and image_info.get("images"):
                    for image in image_info["images"]:
                        content_elements.append({
                            "type": "image",
                            "page": image.get("page", 0),
                            "element_idx": image.get("image_idx", 0),
                            "path": image.get("path", ""),
                            "description": image.get("description", "")
                        })

                content_elements.sort(key=lambda x: (x["page"], x["element_idx"]))

                metadata["content_elements"] = content_elements

                content_types = {}
                if structured_info and structured_info.get("tables"):
                    content_types["table"] = len(structured_info["tables"])
                if image_info and image_info.get("images"):
                    content_types["image"] = len(image_info["images"])
                if not content_types:
                    content_types["default"] = "text"
                metadata["content_types"] = content_types

                data["metadata"] = [metadata]

                for key, value in group.items():
                    data[key] = value

                creation_date = await storage.get_creation_date(path)
                data["creation_date"] = creation_date

                try:
                    import os
                    csv_dir = Path('./data/pdf_csv_exports')
                    csv_dir.mkdir(parents=True, exist_ok=True)

                    csv_filename = f"{doc_id}_pdf_data.csv"
                    csv_path = csv_dir / csv_filename

                    data.to_csv(csv_path, index=False, encoding='utf-8')
                    log.info(f"PDF数据已导出到: {csv_path}")

                    if structured_info and structured_info.get("tables"):
                        tables_data = []
                        for table in structured_info.get("tables", []):
                            html_truncated = table.get("html", "")
                            if len(html_truncated) > 1000:
                                html_truncated = html_truncated[:1000] + "..."
                                
                            tables_data.append({
                                "table_idx": table.get("table_idx", ""),
                                "page": table.get("page", ""),
                                "caption": table.get("caption", ""),
                                "description": table.get("description", ""),
                                "html": html_truncated
                            })
                            
                        if tables_data:
                            tables_df = pd.DataFrame(tables_data)
                            tables_csv_path = csv_dir / f"{doc_id}_tables.csv"
                            tables_df.to_csv(tables_csv_path, index=False, encoding='utf-8')
                            log.info(f"表格数据已导出到: {tables_csv_path}")

                    if image_info and image_info.get("images"):
                        images_data = []
                        for img in image_info.get("images", []):
                            context_before = img.get("context_before", "")
                            if len(context_before) > 500:
                                context_before = context_before[:500] + "..."
                                
                            context_after = img.get("context_after", "")
                            if len(context_after) > 500:
                                context_after = context_after[:500] + "..."
                                
                            images_data.append({
                                "image_idx": img.get("image_idx", ""),
                                "page": img.get("page", ""),
                                "path": img.get("path", ""),
                                "caption": img.get("caption", ""),
                                "description": img.get("description", ""),
                                "context_before": context_before,
                                "context_after": context_after
                            })
                            
                        if images_data:
                            images_df = pd.DataFrame(images_data)
                            images_csv_path = csv_dir / f"{doc_id}_images.csv"
                            images_df.to_csv(images_csv_path, index=False, encoding='utf-8')
                            log.info(f"图片数据已导出到: {images_csv_path}")

                    import json
                    metadata_path = csv_dir / f"{doc_id}_metadata.json"

                    metadata_serializable = {}
                    for k, v in metadata.items():
                        if isinstance(v, (str, int, float, bool, list, dict)) or v is None:
                            metadata_serializable[k] = v
                        else:
                            metadata_serializable[k] = str(v)
                    
                    with open(metadata_path, 'w', encoding='utf-8') as f:
                        json.dump(metadata_serializable, f, ensure_ascii=False, indent=2)
                    log.info(f"元数据已导出到: {metadata_path}")
                    
                except Exception as e:
                    log.error(f"导出CSV时出错: {str(e)}")
                    import traceback
                    log.error(traceback.format_exc())
                

                return data

            except Exception as e:
                log.error(f"处理PDF文件时出错: {path}, 错误: {str(e)}")
                data = pd.DataFrame([{
                    "text": f"[处理错误] {path}: {str(e)}",
                    "title": Path(path).name,
                    "id": path
                }])

                for key, value in group.items():
                    data[key] = value

                try:
                    creation_date = await storage.get_creation_date(path)
                    data["creation_date"] = creation_date
                except:
                    data["creation_date"] = pd.Timestamp.now()
        
                return data

        except Exception as e:
            log.error(f"处理PDF文件时出错: {path}, 错误: {str(e)}")
            data = pd.DataFrame([{
                "text": f"[处理错误] {path}: {str(e)}",
                "title": Path(path).name,
                "id": path
            }])

            for key, value in group.items():
                data[key] = value

            try:
                creation_date = await storage.get_creation_date(path)
                data["creation_date"] = creation_date
            except:
                data["creation_date"] = pd.Timestamp.now()

            return data

    return await load_files(load_file, config, storage, progress)

async def extract_tables_from_model_json(doc_local_dir, doc_id):
    model_json_paths = [
        doc_local_dir / f"{doc_id}_model.json",
        doc_local_dir / "model.json",
    ]
    
    model_json_path = None
    for path in model_json_paths:
        if path.exists():
            model_json_path = path
            break
    
    if not model_json_path:
        log.info(f"model.json文件不存在，尝试了这些路径: {[str(p) for p in model_json_paths]}")
        return None
    
    structured_info = {
        "content_types": {},
        "tables": []
    }
    
    try:
        with open(model_json_path, 'r', encoding='utf-8') as f:
            import json
            model_json = json.load(f)
        
        for page_idx, page in enumerate(model_json):
            page_info = page.get('page_info', {})
            layout_dets = page.get('layout_dets', [])
            
            for obj in layout_dets:
                category_id = obj.get('category_id')

                if category_id == 5:
                    poly = obj.get('poly', [])
                    
                    if len(poly) >= 8:
                        x_coords = [poly[i] for i in range(0, len(poly), 2)]
                        y_coords = [poly[i+1] for i in range(0, len(poly), 2)]
                        bbox = [min(x_coords), min(y_coords), max(x_coords), max(y_coords)]
                        html_content = obj.get('html', "")

                        table_data = {
                            "page": page_info.get('page_no', page_idx+1),
                            "table_idx": len(structured_info["tables"]),
                            "bbox": bbox,
                            "score": obj.get('score', 0),
                            "html": html_content
                        }

                        for caption_obj in layout_dets:
                            if caption_obj.get('category_id') == 6:
                                caption_poly = caption_obj.get('poly', [])
                                if len(caption_poly) >= 8:
                                    caption_y_coords = [caption_poly[i+1] for i in range(0, len(caption_poly), 2)]
                                    caption_y_min = min(caption_y_coords)
                                    caption_y_max = max(caption_y_coords)

                                    if (abs(caption_y_min - bbox[1]) < 100 or abs(caption_y_max - bbox[3]) < 100):
                                        table_data["caption"] = caption_obj.get('text', "")

                        if "caption" not in table_data:
                            table_data["caption"] = ""

                        table_data["footnote"] = ""
                        
                        structured_info["tables"].append(table_data)

        if structured_info["tables"]:
            structured_info["content_types"] = {"table": len(structured_info["tables"])}
        else:
            structured_info["content_types"] = {"default": "text"}
        
        return structured_info
    
    except Exception as e:
        print(f"提取表格信息时出错: {str(e)}")
        import traceback
        print(traceback.format_exc())
        return {"content_types": {"default": "text"}, "tables": []}

def extract_images_from_content_list(doc_local_dir, doc_id):
    content_list_paths = [
        doc_local_dir / f"{doc_id}_content_list.json",
        doc_local_dir / "content_list.json",
    ]
    
    content_list_path = None
    for path in content_list_paths:
        if path.exists():
            content_list_path = path
            break
    
    if not content_list_path:
        print(f"content_list.json文件不存在，尝试了这些路径: {[str(p) for p in content_list_paths]}")
        return None
    
    structured_info = {
        "content_types": {},
        "images": []
    }
    
    try:
        with open(content_list_path, 'r', encoding='utf-8') as f:
            import json
            content_list = json.load(f)

        for idx, item in enumerate(content_list):
            if item.get('type') == 'image':
                image_data = {
                    "page": item.get('page_idx', 0),
                    "image_idx": len(structured_info["images"]),
                    "path": item.get('img_path', ''),
                    "caption": '',
                    "context_before": '',
                    "context_after": ''
                }

                img_caption = item.get('img_caption', [])
                if img_caption and isinstance(img_caption, list):
                    image_data["caption"] = ' '.join(img_caption)
                elif img_caption and isinstance(img_caption, str):
                    image_data["caption"] = img_caption

                if idx > 0:
                    prev_item = content_list[idx-1]
                    if prev_item.get('type') == 'text':
                        image_data["context_before"] = prev_item.get('text', '')

                if idx < len(content_list) - 1:
                    next_item = content_list[idx+1]
                    if next_item.get('type') == 'text':
                        image_data["context_after"] = next_item.get('text', '')

                if image_data["path"] and not image_data["path"].startswith('/'):
                    img_path = doc_local_dir / image_data["path"]
                
                structured_info["images"].append(image_data)

        if structured_info["images"]:
            structured_info["content_types"] = {"image": len(structured_info["images"])}
        else:
            structured_info["content_types"] = {"default": "text"}
        
        return structured_info
    
    except Exception as e:
        print(f"提取图片信息时出错: {str(e)}")
        import traceback
        print(traceback.format_exc())
        return {"content_types": {"default": "text"}, "images": []}

def generate_descriptions_for_images(doc_local_dir, image_info, config):
    if not image_info or not image_info.get("images"):
        return image_info
    
    try:
        image_paths = []
        for image_data in image_info["images"]:
            if image_data.get("path"):
                img_path = doc_local_dir / image_data["path"]
                if img_path.exists():
                    image_paths.append(img_path)
        
        if not image_paths:
            return image_info

        image_dir = image_paths[0].parent

        output_file = doc_local_dir / "image_descriptions.json"

        try:
            from graphrag.index.input.util import generate_image_descriptions_sync

            descriptions = generate_image_descriptions_sync(
                config=config,
                image_dir=image_dir,
                output_file=output_file,
                max_retries=3,
                retry_delay=2,
                image_info=image_info
            )

            for image_data in image_info["images"]:
                if image_data.get("path"):
                    img_path = str(doc_local_dir / image_data["path"])
                    if img_path in descriptions:
                        image_data["description"] = descriptions[img_path]
                    else:
                        rel_path = str(image_data["path"])
                        matching_keys = [k for k in descriptions.keys() if k.endswith(rel_path)]
                        if matching_keys:
                            image_data["description"] = descriptions[matching_keys[0]]
                        else:
                            img_name = Path(image_data["path"]).name
                            matching_keys = [k for k in descriptions.keys() if Path(k).name == img_name]
                            if matching_keys:
                                image_data["description"] = descriptions[matching_keys[0]]
                            else:
                                image_data["description"] = "无法生成图片描述"
                else:
                    image_data["description"] = "图片路径为空"
        
        except ImportError:
            log.error("无法导入generate_image_descriptions_sync函数，跳过描述生成")
            for image_data in image_info["images"]:
                image_data["description"] = "描述生成功能不可用"
        except Exception as e:
            log.error(f"生成图片描述时出错: {str(e)}")
            import traceback
            log.error(traceback.format_exc())
            for image_data in image_info["images"]:
                image_data["description"] = f"描述生成失败: {str(e)}"
        
        return image_info
    
    except Exception as e:
        log.error(f"处理图片描述时出错: {str(e)}")
        import traceback
        log.error(traceback.format_exc())
        return image_info

def generate_descriptions_for_tables(doc_local_dir, structured_info, config):
    if not structured_info or not structured_info.get("tables"):
        return structured_info
    
    try:
        tables_data = []
        for table_data in structured_info["tables"]:
            if table_data.get("html"):
                tables_data.append({
                    "index": table_data.get("table_idx", 0),
                    "html": table_data.get("html", ""),
                    "caption": table_data.get("caption", "")
                })
        
        if not tables_data:
            return structured_info

        output_file = doc_local_dir / "table_descriptions.json"

        try:
            import os
            import json
            import time
            from openai import OpenAI

            api_key = config.table_description_api_key
            base_url = config.base_url if hasattr(config, "base_url") else "https://api.deepseek.com"
            model = config.table_description_model

            max_retries = 3
            retry_delay = 2
            max_tokens = 300
            temperature = 0.7

            client = OpenAI(
                api_key=api_key,
                base_url=base_url,
            )

            descriptions = {}
            for table_info in tables_data:
                table_idx = table_info["index"]
                html_content = table_info["html"]
                caption = table_info["caption"]

                prompt_text = """你是一个助理，负责总结表格和文本。给出表格或文本的简明摘要。表格的格式为HTML"""

                user_message = f"请总结以下表格内容:\n\n{html_content}"
                if caption:
                    user_message = f"表格标题: {caption}\n\n{user_message}"

                messages = [
                    {"role": "system", "content": prompt_text},
                    {"role": "user", "content": user_message}
                ]

                success = False
                for attempt in range(max_retries):
                    try:
                        response = client.chat.completions.create(
                            model=model,
                            messages=messages,
                            max_tokens=max_tokens,
                            temperature=temperature
                        )

                        description = response.choices[0].message.content
                        descriptions[table_idx] = description
                        success = True
                        break
                        
                    except Exception as e:
                        log.error(f"处理表格时出错 (尝试 {attempt+1}/{max_retries}): {str(e)}")
                        if attempt < max_retries - 1:
                            time.sleep(retry_delay * (attempt + 1))
                
                if not success:
                    descriptions[table_idx] = f"[描述生成失败: 多次尝试后仍然失败]"

                with open(output_file, 'w', encoding='utf-8') as f:
                    json.dump(descriptions, f, ensure_ascii=False, indent=2)

                time.sleep(1)

            for table_data in structured_info["tables"]:
                table_idx = table_data.get("table_idx", 0)
                if table_idx in descriptions:
                    table_data["description"] = descriptions[table_idx]
                else:
                    table_data["description"] = "未生成描述"
        
        except ImportError:
            log.error("导入OpenAI模块失败，无法生成表格描述")
            for table_data in structured_info["tables"]:
                table_data["description"] = "描述生成功能不可用"
        except Exception as e:
            log.error(f"生成表格描述时出错: {str(e)}")
            import traceback
            log.error(traceback.format_exc())
            for table_data in structured_info["tables"]:
                table_data["description"] = f"描述生成失败: {str(e)}"
        
        return structured_info
    
    except Exception as e:
        log.error(f"处理表格描述时出错: {str(e)}")
        import traceback
        log.error(traceback.format_exc())
        return structured_info

def enhance_markdown_with_metadata(text, structured_info, image_info):
    import json
    import re

    if (not structured_info or not structured_info.get("tables")) and (not image_info or not image_info.get("images")):
        return text

    table_pattern = re.compile(r'<table>.*?</table>', re.DOTALL)

    image_pattern = re.compile(r'!\[.*?\]\((.*?)\)', re.DOTALL)

    lines = text.split('\n')
    enhanced_lines = []

    if structured_info and structured_info.get("tables"):
        tables = structured_info["tables"]
        for i, line in enumerate(lines):
            enhanced_lines.append(line)

            table_matches = table_pattern.findall(line)
            if table_matches:
                for table_html in table_matches:
                    for table in tables:
                        if table.get("html") and table_html in table.get("html"):
                            metadata = {
                                "type": "table",
                                "page": table.get("page", 0),
                                "element_idx": table.get("table_idx", 0),
                                "description": table.get("description", "")
                            }

                            metadata_str = json.dumps(metadata, ensure_ascii=False, indent=4)
                            enhanced_lines.insert(enhanced_lines.index(line), f"<!-- METADATA\n{metadata_str}\n-->")
                            break

    if image_info and image_info.get("images"):
        images = image_info["images"]
        result = []
        
        for line in enhanced_lines:
            image_matches = image_pattern.findall(line)
            if image_matches:
                for img_path in image_matches:
                    for image in images:
                        if image.get("path") and (img_path in image.get("path") or image.get("path") in img_path):
                            metadata = {
                                "type": "image",
                                "page": image.get("page", 0),
                                "element_idx": image.get("image_idx", 0),
                                "path": image.get("path", ""),
                                "description": image.get("description", "")
                            }

                            metadata_str = json.dumps(metadata, ensure_ascii=False, indent=4)
                            result.append(f"<!-- METADATA\n{metadata_str}\n-->")
                            result.append(line)
                            break
                    else:
                        result.append(line)
            else:
                result.append(line)
        
        enhanced_lines = result

    return '\n'.join(enhanced_lines) 
