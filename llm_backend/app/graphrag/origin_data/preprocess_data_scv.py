import pandas as pd
import os
from datetime import datetime
import re

# Get the absolute path of the directory where this script is located
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

# Directory for exported data
EXPORT_DIR = os.path.join(SCRIPT_DIR, 'exported_data')

# Directory for output data
OUTPUT_DIR = os.path.join(SCRIPT_DIR, 'output_data')


# Simple token counting function
def count_tokens(text):
    """
    Simple estimation of token count.

    Chinese: each Chinese character is counted as one token.
    English: each word separated by spaces is counted as one token.
    Punctuation: each punctuation mark is counted as one token.
    """
    if not text:
        return 0

    # Chinese characters
    chinese_chars = re.findall(r'[\u4e00-\u9fff]', text)

    # English words
    english_words = re.findall(r'[a-zA-Z]+', text)

    # Numbers
    numbers = re.findall(r'[0-9]+', text)

    # Punctuation marks
    punctuations = re.findall(r'[^\w\s\u4e00-\u9fff]', text)

    # Total tokens = Chinese characters + English words + numbers + punctuation marks
    return len(chinese_chars) + len(english_words) + len(numbers) + len(punctuations)


def preprocess_reviews(
    reviews_file=None,
    products_file=None,
    customers_file=None,
    categories_file=None,
    output_file=None
):
    """
    Preprocess review data by joining it with product, customer, and category data,
    and generate structured text.

    Parameters:
        reviews_file: Path to the reviews CSV file
        products_file: Path to the products CSV file
        customers_file: Path to the customers CSV file
        categories_file: Path to the categories CSV file
        output_file: Path to the output CSV file
    """
    # Set default file paths
    if reviews_file is None:
        reviews_file = os.path.join(EXPORT_DIR, 'reviews.csv')
    if products_file is None:
        products_file = os.path.join(EXPORT_DIR, 'products.csv')
    if customers_file is None:
        customers_file = os.path.join(EXPORT_DIR, 'customers.csv')
    if categories_file is None:
        categories_file = os.path.join(EXPORT_DIR, 'categories.csv')
    if output_file is None:
        output_file = os.path.join(OUTPUT_DIR, 'processed_reviews.csv')

    print(f"Start processing review data: {reviews_file}")
    print(f"Export directory: {EXPORT_DIR}")

    # Check whether the export directory exists
    if not os.path.exists(EXPORT_DIR):
        print(f"Error: Export directory {EXPORT_DIR} does not exist")
        return

    # Check whether input files exist
    for file_path, file_name in [
        (reviews_file, "reviews"),
        (products_file, "products"),
        (customers_file, "customers"),
        (categories_file, "categories")
    ]:
        if not os.path.exists(file_path):
            print(f"Error: {file_name} file {file_path} does not exist")
            return

    # Read CSV files
    try:
        reviews_df = pd.read_csv(reviews_file)
        products_df = pd.read_csv(products_file)
        customers_df = pd.read_csv(customers_file)
        categories_df = pd.read_csv(categories_file)

        print(f"Successfully loaded {len(reviews_df)} review records")
    except Exception as e:
        print(f"Error while reading CSV files: {e}")
        return

    # Merge data
    # 1. Merge reviews with product data
    if 'ProductID' in reviews_df.columns and 'ProductID' in products_df.columns:
        merged_df = pd.merge(
            reviews_df,
            products_df,
            on='ProductID',
            how='left',
            suffixes=('', '_product')
        )
    else:
        print("Error: ProductID column is missing in reviews or products data")
        return

    # 2. Merge the result with customer data
    if 'CustomerID' in reviews_df.columns and 'CustomerID' in customers_df.columns:
        merged_df = pd.merge(
            merged_df,
            customers_df,
            on='CustomerID',
            how='left',
            suffixes=('', '_customer')
        )
    else:
        print("Error: CustomerID column is missing in reviews or customers data")
        return

    # 3. Merge the result with category data
    if 'CategoryID' in merged_df.columns and 'CategoryID' in categories_df.columns:
        merged_df = pd.merge(
            merged_df,
            categories_df,
            on='CategoryID',
            how='left',
            suffixes=('', '_category')
        )
    else:
        print("Warning: Unable to merge with category data. CategoryID may be missing.")

    # Create structured text descriptions
    merged_df['text'] = merged_df.apply(
        lambda row: format_review_text(row),
        axis=1
    )

    # Calculate token count for each review
    merged_df['token_count'] = merged_df['text'].apply(count_tokens)
    print(f"Average token count per review: {merged_df['token_count'].mean():.2f}")
    print(f"Maximum token count: {merged_df['token_count'].max()}")
    print(f"Minimum token count: {merged_df['token_count'].min()}")

    # Save processed data
    try:
        # Ensure the output directory exists
        output_dir = os.path.dirname(output_file)
        if output_dir and not os.path.exists(output_dir):
            os.makedirs(output_dir)

        # Select columns to export
        output_columns = [
            'ReviewID',
            'ProductID',
            'CustomerID',
            'Rating',
            'ReviewDate',
            'text',
            'token_count'
        ]

        if 'CategoryName' in merged_df.columns:
            output_columns.append('CategoryName')
        if 'ProductName' in merged_df.columns:
            output_columns.append('ProductName')
        if 'CompanyName' in merged_df.columns:
            output_columns.append('CompanyName')

        # Save to CSV
        merged_df[output_columns].to_csv(output_file, index=False, encoding='utf-8')
        print(f"Processed data has been saved to: {output_file}")
        return output_file

    except Exception as e:
        print(f"Error while saving processed data: {e}")
        return None


def format_review_text(row):
    """
    Format review data into a structured English text description.
    """
    product_name = row.get('ProductName', 'Unknown Product')
    unit_price = row.get('UnitPrice', 'Unknown Price')
    units_in_stock = row.get('UnitsInStock', 'Unknown Stock')

    supplier_name = row.get('SupplierName', '')

    customer_id = row.get('CustomerID', 'Unknown Customer ID')
    customer_company = row.get('CompanyName', 'Unknown Customer Company')
    customer_location = f"{row.get('City', '')}, {row.get('Country', '')}"
    customer_location = customer_location.strip(', ')

    category_name = row.get('CategoryName', 'Unknown Category')

    rating = row.get('Rating', 0)
    review_text = row.get('ReviewText', '')

    review_date = row.get('ReviewDate', '')
    try:
        if review_date:
            date_obj = pd.to_datetime(review_date)
            review_date = date_obj.strftime('%Y-%m-%d')
    except Exception:
        pass

    parts = []
    parts.append(f"Customer ID: {customer_id}")
    parts.append(f"Customer Company: {customer_company}")

    if customer_location:
        parts.append(f"Customer Location: {customer_location}")

    parts.append(f"Product Info: {product_name} (Category: {category_name})")

    if supplier_name:
        parts.append(f"Manufacturer: {supplier_name}")

    if unit_price != 'Unknown Price':
        parts.append(f"Product Price: {unit_price}")

    parts.append(f"Rating: {rating} stars")
    parts.append(f"Review Date: {review_date}")
    parts.append(f"Review Content: \"{review_text}\"")

    formatted_text = "\n".join(parts)
    return formatted_text


def merge_csv_rows(
    input_file=None,
    output_file=None,
    group_size=5,
    separator="<ROW_SEP>\n\n",
    max_tokens=1000
):
    """
    Merge rows in a CSV file by fixed-size groups, preserve all fields,
    and ensure the merged text does not exceed the token threshold.

    Parameters:
        input_file: Path to the input CSV file
        output_file: Path to the output CSV file
        group_size: Maximum number of rows per group. Default is 5.
        separator: Separator between rows. Default is "<ROW_SEP>\\n\\n".
        max_tokens: Maximum token count for the merged text. Default is 1000.
    """
    # Set default file paths
    if input_file is None:
        input_file = os.path.join(OUTPUT_DIR, 'processed_reviews.csv')
    if output_file is None:
        output_file = os.path.join(OUTPUT_DIR, 'merged_reviews.csv')

    print(f"Merging review data with separator: '{separator}'")
    print(f"Maximum token count: {max_tokens}, maximum rows per group: {group_size}")

    # Check whether the input file exists
    if not os.path.exists(input_file):
        print(f"Error: Input file {input_file} does not exist")
        return None

    # Read CSV file
    df = pd.read_csv(input_file)

    # Ensure the text column exists
    if 'text' not in df.columns:
        print(f"Error: Input file {input_file} does not contain a text column")
        return None

    # Get all column names
    all_columns = df.columns.tolist()
    text_column_idx = all_columns.index('text')
    other_columns = [col for col in all_columns if col != 'text']

    # Store merged rows
    merged_rows = []

    # Calculate token count for all reviews
    if 'token_count' not in df.columns:
        df['token_count'] = df['text'].apply(count_tokens)

    # Check whether the token threshold is reasonable
    max_single_token = df['token_count'].max()
    if max_tokens < max_single_token:
        print(
            f"Warning: max_tokens ({max_tokens}) is smaller than the maximum "
            f"single-review token count ({max_single_token})"
        )
        print(f"max_tokens will be automatically adjusted to {max(max_single_token, 500)}")
        max_tokens = max(max_single_token, 500)

    # Group by category if CategoryName exists
    if 'CategoryName' in df.columns:
        grouped = df.groupby('CategoryName')

        for category, group in grouped:
            print(f"Processing category: {category}, total reviews: {len(group)}")

            # Current batch texts and token count
            current_texts = []
            current_token_count = 0

            # Record the first row in the batch to preserve metadata
            first_row_in_batch = None

            # Iterate through each row in the group
            for _, row in group.iterrows():
                # Record the first row in the current batch
                if not current_texts:
                    first_row_in_batch = row

                # Get current row text and token count
                text = row['text']
                token_count = row.get('token_count', count_tokens(text))

                # If a single review exceeds the maximum token limit, process it separately
                if token_count > max_tokens:
                    print(
                        f"Warning: A single review token count ({token_count}) "
                        f"exceeds the maximum limit ({max_tokens})"
                    )

                    # If the current batch has content, save it first
                    if current_texts:
                        merged_text = separator.join(current_texts)
                        merged_row = {'text': merged_text}

                        # Add values from other columns
                        for col in other_columns:
                            merged_row[col] = first_row_in_batch[col]

                        # Add token count
                        merged_row['token_count'] = current_token_count

                        # Add to result
                        merged_rows.append(merged_row)

                        # Reset current batch
                        current_texts = []
                        current_token_count = 0

                    # Try to truncate the text
                    truncated_text = truncate_text(text, max_tokens)
                    truncated_token_count = count_tokens(truncated_text)

                    # Create a separate row
                    merged_row = {'text': truncated_text}

                    # Add values from other columns
                    for col in other_columns:
                        merged_row[col] = row[col]

                    # Add token count
                    merged_row['token_count'] = truncated_token_count

                    # Add to result
                    merged_rows.append(merged_row)

                    # Continue to the next review
                    continue

                # Calculate separator token count
                separator_tokens = count_tokens(separator) if current_texts else 0

                # Check whether adding this review would exceed the token limit
                if current_token_count + token_count + separator_tokens > max_tokens:
                    # If it would exceed the limit, save the current batch first
                    if current_texts:
                        merged_text = separator.join(current_texts)
                        merged_row = {'text': merged_text}

                        # Add values from other columns
                        for col in other_columns:
                            merged_row[col] = first_row_in_batch[col]

                        # Add token count
                        merged_row['token_count'] = current_token_count

                        # Add to result
                        merged_rows.append(merged_row)

                        # Reset current batch
                        current_texts = [text]
                        current_token_count = token_count
                        first_row_in_batch = row
                    else:
                        # This should not happen because single-review token count was already handled
                        print("Warning: Unexpected case: empty batch but token count check failed")
                else:
                    # If it would not exceed the limit, add it to the current batch
                    current_texts.append(text)
                    current_token_count += token_count + separator_tokens

            # Process the last batch
            if current_texts:
                merged_text = separator.join(current_texts)
                merged_row = {'text': merged_text}

                # Add values from other columns
                for col in other_columns:
                    merged_row[col] = first_row_in_batch[col]

                # Add token count
                merged_row['token_count'] = current_token_count

                # Add to result
                merged_rows.append(merged_row)

    else:
        # If CategoryName does not exist, process rows directly
        print("CategoryName column not found. Rows will be processed directly.")

        # Current batch texts and token count
        current_texts = []
        current_token_count = 0

        # Record the first row in the batch to preserve metadata
        first_row_in_batch = None

        # Iterate through each row
        for _, row in df.iterrows():
            # Record the first row in the current batch
            if not current_texts:
                first_row_in_batch = row

            # Get current row text and token count
            text = row['text']
            token_count = row.get('token_count', count_tokens(text))

            # If a single review exceeds the maximum token limit, process it separately
            if token_count > max_tokens:
                print(
                    f"Warning: A single review token count ({token_count}) "
                    f"exceeds the maximum limit ({max_tokens})"
                )

                # If the current batch has content, save it first
                if current_texts:
                    merged_text = separator.join(current_texts)
                    merged_row = {'text': merged_text}

                    # Add values from other columns
                    for col in other_columns:
                        merged_row[col] = first_row_in_batch[col]

                    # Add token count
                    merged_row['token_count'] = current_token_count

                    # Add to result
                    merged_rows.append(merged_row)

                    # Reset current batch
                    current_texts = []
                    current_token_count = 0

                # Try to truncate the text
                truncated_text = truncate_text(text, max_tokens)
                truncated_token_count = count_tokens(truncated_text)

                # Create a separate row
                merged_row = {'text': truncated_text}

                # Add values from other columns
                for col in other_columns:
                    merged_row[col] = row[col]

                # Add token count
                merged_row['token_count'] = truncated_token_count

                # Add to result
                merged_rows.append(merged_row)

                # Continue to the next review
                continue

            # Calculate separator token count
            separator_tokens = count_tokens(separator) if current_texts else 0

            # Check whether adding this review would exceed the token limit
            if current_token_count + token_count + separator_tokens > max_tokens:
                # If it would exceed the limit, save the current batch first
                if current_texts:
                    merged_text = separator.join(current_texts)
                    merged_row = {'text': merged_text}

                    # Add values from other columns
                    for col in other_columns:
                        merged_row[col] = first_row_in_batch[col]

                    # Add token count
                    merged_row['token_count'] = current_token_count

                    # Add to result
                    merged_rows.append(merged_row)

                    # Reset current batch
                    current_texts = [text]
                    current_token_count = token_count
                    first_row_in_batch = row
                else:
                    # This should not happen because single-review token count was already handled
                    print("Warning: Unexpected case: empty batch but token count check failed")
            else:
                # If it would not exceed the limit, add it to the current batch
                current_texts.append(text)
                current_token_count += token_count + separator_tokens

                # If group_size is reached, save the current batch
                if len(current_texts) >= group_size:
                    merged_text = separator.join(current_texts)
                    merged_row = {'text': merged_text}

                    # Add values from other columns
                    for col in other_columns:
                        merged_row[col] = first_row_in_batch[col]

                    # Add token count
                    merged_row['token_count'] = current_token_count

                    # Add to result
                    merged_rows.append(merged_row)

                    # Reset current batch
                    current_texts = []
                    current_token_count = 0
                    first_row_in_batch = None

        # Process the last batch
        if current_texts:
            merged_text = separator.join(current_texts)
            merged_row = {'text': merged_text}

            # Add values from other columns
            for col in other_columns:
                merged_row[col] = first_row_in_batch[col]

            # Add token count
            merged_row['token_count'] = current_token_count

            # Add to result
            merged_rows.append(merged_row)

    # Create a new DataFrame
    merged_df = pd.DataFrame(merged_rows)

    # Ensure the output directory exists
    output_dir = os.path.dirname(output_file)
    if output_dir and not os.path.exists(output_dir):
        os.makedirs(output_dir)

    # Save the processed CSV file
    # merged_df.to_csv(output_file, index=False)
    # print(f"Processing completed. Saved to {output_file}")
    # print(f"Original row count: {len(df)}, merged row count: {len(merged_df)}")
    # print(f"Merged columns: {merged_df.columns.tolist()}")

    # Add chunk_id for each merged text block
    merged_df.insert(0, 'chunk_id', range(1, len(merged_df) + 1))

    # Only keep fields that correctly describe the merged text block
    final_columns = ['chunk_id', 'text', 'token_count']

    if 'CategoryName' in merged_df.columns:
        final_columns.append('CategoryName')

    # Save the final merged CSV file
    merged_df[final_columns].to_csv(output_file, index=False, encoding='utf-8')

    print(f"Processing completed. Saved to {output_file}")
    print(f"Original row count: {len(df)}, merged row count: {len(merged_df)}")
    print(f"Final columns kept: {final_columns}")

    # Print token statistics
    if 'token_count' in merged_df.columns:
        print(f"Average token count after merging: {merged_df['token_count'].mean():.2f}")
        print(f"Maximum token count after merging: {merged_df['token_count'].max()}")
        print(f"Minimum token count after merging: {merged_df['token_count'].min()}")

    # Show an example of how to split by <ROW_SEP>
    if not merged_df.empty:
        first_text = merged_df.iloc[0]['text']
        rows = first_text.split('<ROW_SEP>')
        print(f"\nExample: The first merged record contains {len(rows)} original reviews")
        print("You can use text.split('<ROW_SEP>') to split it back into individual reviews")

    return output_file


def truncate_text(text, max_tokens):
    """
    Truncate text so that its token count does not exceed max_tokens.

    Parameters:
        text: Text to be truncated
        max_tokens: Maximum token count

    Returns:
        Truncated text
    """
    # Return directly if text is empty
    if not text:
        return text

    # Return directly if token count is already within the limit
    if count_tokens(text) <= max_tokens:
        return text

    # Split text by line
    lines = text.split('\n')

    # Keep essential review metadata and the beginning of review content
    essential_info = lines[:5]

    # Find the line containing review content
    review_content_line = None
    for i, line in enumerate(lines):
        if line.startswith("Review Content:"):
            review_content_line = i
            break

    # If the review content line is found
    if review_content_line is not None:
        review_content = lines[review_content_line]

        # Extract the content inside quotation marks
        content_match = re.search(r'"(.*)"', review_content)
        if content_match:
            content = content_match.group(1)

            # Calculate token count of existing essential information
            info_tokens = count_tokens('\n'.join(essential_info))

            # Calculate available token count for review content
            available_tokens = max_tokens - info_tokens - 20

            # If available token count is less than or equal to 0,
            # keep only the essential information
            if available_tokens <= 0:
                truncated_content = "..."
            else:
                # Truncate review content
                truncated_content = truncate_content(content, available_tokens)

            # Replace the original review content
            lines[review_content_line] = f'Review Content: "{truncated_content}..."'

            # Keep only essential lines
            return '\n'.join(essential_info + [lines[review_content_line]])

    # If review content is not found or processing fails, perform simple truncation
    result = '\n'.join(essential_info)
    if count_tokens(result) > max_tokens:
        # If even essential information exceeds max_tokens, simplify further
        result = '\n'.join(lines[:3]) + "\n...(content truncated)..."

    return result


def truncate_content(content, max_tokens):
    """
    Truncate review content so that its token count does not exceed max_tokens.

    Parameters:
        content: Review content
        max_tokens: Maximum token count

    Returns:
        Truncated content
    """
    # Return directly if content is empty
    if not content:
        return content

    # Return directly if token count is already within the limit
    if count_tokens(content) <= max_tokens:
        return content

    # For Chinese text, truncate by character
    if re.search(r'[\u4e00-\u9fff]', content):
        # Binary search for the appropriate truncation position
        left, right = 0, len(content)
        while left < right:
            mid = (left + right) // 2
            if count_tokens(content[:mid]) <= max_tokens:
                left = mid + 1
            else:
                right = mid

        # Find the last complete sentence boundary
        last_sentence_end = max(
            content[:left - 1].rfind('。'),
            content[:left - 1].rfind('！'),
            content[:left - 1].rfind('？'),
            content[:left - 1].rfind('；'),
            content[:left - 1].rfind(','),
            content[:left - 1].rfind('，')
        )

        if last_sentence_end > 0:
            return content[:last_sentence_end + 1]
        else:
            return content[:left - 1]

    # For English text, truncate by words
    words = content.split()
    result = []
    current_tokens = 0

    for word in words:
        word_tokens = count_tokens(word)
        if current_tokens + word_tokens <= max_tokens:
            result.append(word)
            current_tokens += word_tokens
        else:
            break

    return ' '.join(result)


def list_files_in_export_dir():
    """
    List all files in the export directory.
    """
    if not os.path.exists(EXPORT_DIR):
        print(f"Export directory {EXPORT_DIR} does not exist")
        return

    print(f"Files in export directory {EXPORT_DIR}:")
    for file in os.listdir(EXPORT_DIR):
        file_path = os.path.join(EXPORT_DIR, file)
        if os.path.isfile(file_path):
            print(f"  - {file} ({os.path.getsize(file_path)} bytes)")


if __name__ == "__main__":
    # List all files in the export directory
    list_files_in_export_dir()

    # If this script is run directly, process files using default paths
    processed_file = preprocess_reviews()

    # If processing succeeds, merge the processed review records
    if processed_file:
        merge_csv_rows(
            input_file=processed_file,
            max_tokens=1000
        )
