"""
Vector-based query matcher for mapping user questions to predefined Cypher queries.
"""

import json
import re
from typing import Any, Dict, List, Optional

import numpy as np
import requests
from langchain_core.prompts import ChatPromptTemplate
from sklearn.metrics.pairwise import cosine_similarity

from app.core.config import settings


class VectorQueryMatcher:
    """Vector-based matcher for mapping user questions to predefined Cypher queries."""

    def __init__(
        self,
        predefined_cypher_dict: Dict[str, str],
        query_descriptions: Dict[str, str],
        similarity_threshold: float = 0.5,
    ):
        """
        Initialize the query matcher.

        Parameters
        ----------
        predefined_cypher_dict : Dict[str, str]
            Dictionary of predefined Cypher queries.
        query_descriptions : Dict[str, str]
            Dictionary containing descriptions for each predefined query.
        similarity_threshold : float
            Similarity threshold. Matches below this threshold are ignored.
        """
        self.predefined_cypher_dict = predefined_cypher_dict
        self.query_descriptions = query_descriptions
        self.similarity_threshold = similarity_threshold

        # Load the Ollama base URL and embedding model from the application settings
        self.ollama_base_url = settings.OLLAMA_BASE_URL.rstrip("/")
        self.ollama_embedding_model = settings.OLLAMA_EMBEDDING_MODEL
        self.ollama_api_url = f"{self.ollama_base_url}/api/embed"

        print(f"Using Ollama embedding model: {self.ollama_embedding_model}, Base URL: {self.ollama_base_url}")

        # Precompute embeddings for predefined queries
        self.query_vectors = self._compute_query_vectors()

    def _embed_texts(self, texts: List[str]) -> List[List[float]]:
        """Convert texts into vectors using the Ollama embedding API."""
        payload = {
            "model": self.ollama_embedding_model,
            "input": texts,
        }

        try:
            response = requests.post(self.ollama_api_url, json=payload, timeout=60)
            response.raise_for_status()
            result = response.json()
            return result["embeddings"]
        except Exception as e:
            print(f"Failed to generate embeddings: {e}")

            # Return zero vectors as a fallback
            return [[0.0] * 1024 for _ in texts]

    def _compute_query_vectors(self) -> Dict[str, np.ndarray]:
        """Precompute vector representations for all predefined queries."""
        query_texts = []
        query_keys = []

        for query_name in self.predefined_cypher_dict:
            # Combine the query name and description to improve semantic representation
            description = self.query_descriptions.get(query_name, "")
            query_text = f"{query_name} {description}"
            query_texts.append(query_text)
            query_keys.append(query_name)

        # Generate vector representations
        vectors = self._embed_texts(query_texts)

        # Map each query name to its vector
        return {key: np.array(vector) for key, vector in zip(query_keys, vectors)}

    def match_query(self, user_question: str, top_k: int = 3) -> List[Dict[str, Any]]:
        """
        Match a user question to the most similar predefined queries.

        Parameters
        ----------
        user_question : str
            User question.
        top_k : int
            Maximum number of matches to return.

        Returns
        -------
        List[Dict[str, Any]]
            Matched queries sorted by similarity in descending order.
        """
        # Generate a vector for the user question
        question_vector = np.array(self._embed_texts([user_question])[0])

        # Calculate similarity between the user question and each predefined query
        similarities = []

        for query_name, query_vector in self.query_vectors.items():
            similarity = cosine_similarity([question_vector], [query_vector])[0][0]
            similarities.append((query_name, similarity))

        # Sort matches by similarity in descending order
        similarities.sort(key=lambda item: item[1], reverse=True)

        # Return the top matches that meet the similarity threshold
        results = []

        for query_name, similarity in similarities[:top_k]:
            if similarity >= self.similarity_threshold:
                results.append({
                    "query_name": query_name,
                    "similarity": float(similarity),
                    "cypher": self.predefined_cypher_dict[query_name],
                })

        return results

    def extract_parameters(self, user_question: str, query_name: str, llm: Any = None) -> Dict[str, str]:
        """
        Extract parameters from a user question.

        Parameters
        ----------
        user_question : str
            User question.
        query_name : str
            Name of the matched predefined query.
        llm : Any, optional
            Language model used for complex parameter extraction.

        Returns
        -------
        Dict[str, str]
            Dictionary containing extracted parameter names and values.
        """
        # Verify that the matched query exists
        if query_name not in self.predefined_cypher_dict:
            return {}

        # Retrieve the Cypher query template
        cypher_template = self.predefined_cypher_dict[query_name]

        # Extract parameter names from the Cypher query
        param_names = list(dict.fromkeys(re.findall(r"\$(\w+)", cypher_template)))

        # No parameters are required by the query
        if not param_names:
            return {}

        # Use the language model when one is provided
        if llm is not None:
            return self._extract_parameters_with_llm(user_question, param_names, query_name, llm)

        # Otherwise, use rule-based parameter extraction
        return self._extract_parameters_with_rules(user_question, param_names)

    def _extract_parameters_with_rules(self, user_question: str, param_names: List[str]) -> Dict[str, str]:
        """Extract parameters from a user question using predefined rules."""
        params = {}

        for param_name in param_names:
            if param_name == "product_name":
                # Extract a product name from an English question
                product_patterns = [
                    r"(?:product|item)(?:\s+named|\s+called|\s+name)?\s*[:#]?\s*[\"']?([A-Za-z0-9][A-Za-z0-9\s\-]+?)[\"']?(?:\?|$|price|inventory|stock|information|details)",
                ]

                for pattern in product_patterns:
                    product_match = re.search(pattern, user_question, re.IGNORECASE)

                    if product_match:
                        params[param_name] = product_match.group(1).strip()
                        break

            elif param_name == "category_name":
                # Extract a category name from an English question
                category_patterns = [
                    r"(?:category|type|classification)(?:\s+named|\s+called|\s+of)?\s*[:#]?\s*[\"']?([A-Za-z0-9][A-Za-z0-9\s\-]+?)[\"']?(?:\?|$|products|items|information|details)",
                ]

                for pattern in category_patterns:
                    category_match = re.search(pattern, user_question, re.IGNORECASE)

                    if category_match:
                        params[param_name] = category_match.group(1).strip()
                        break

            elif param_name == "supplier_name":
                # Extract a supplier name from an English question
                supplier_patterns = [
                    r"(?:supplier|vendor)(?:\s+named|\s+called)?\s*[:#]?\s*[\"']?([A-Za-z0-9][A-Za-z0-9\s\-]+?)[\"']?(?:\?|$|products|items|information|details)",
                ]

                for pattern in supplier_patterns:
                    supplier_match = re.search(pattern, user_question, re.IGNORECASE)

                    if supplier_match:
                        params[param_name] = supplier_match.group(1).strip()
                        break

            elif param_name == "customer_name":
                # Extract a customer name from an English question
                customer_patterns = [
                    r"(?:customer|client)(?:\s+named|\s+called)?\s*[:#]?\s*[\"']?([A-Za-z][A-Za-z\s\-]+?)[\"']?(?:\?|$|orders|information|details|purchases)",
                ]

                for pattern in customer_patterns:
                    customer_match = re.search(pattern, user_question, re.IGNORECASE)

                    if customer_match:
                        params[param_name] = customer_match.group(1).strip()
                        break

            elif param_name == "employee_name":
                # Extract an employee name from an English question
                employee_patterns = [
                    r"(?:employee|staff member)(?:\s+named|\s+called)?\s*[:#]?\s*[\"']?([A-Za-z][A-Za-z\s\-]+?)[\"']?(?:\?|$|orders|information|details)",
                ]

                for pattern in employee_patterns:
                    employee_match = re.search(pattern, user_question, re.IGNORECASE)

                    if employee_match:
                        params[param_name] = employee_match.group(1).strip()
                        break

            elif param_name == "country":
                # Extract a country name from an English question
                country_patterns = [
                    r"(?:from|in|located in)\s+([A-Za-z][A-Za-z\s\-]+?)(?:\?|$|supplier|suppliers|vendor|vendors|company|companies)",
                ]

                for pattern in country_patterns:
                    country_match = re.search(pattern, user_question, re.IGNORECASE)

                    if country_match:
                        params[param_name] = country_match.group(1).strip()
                        break

            elif param_name == "order_id":
                # Extract a numeric order ID
                order_match = re.search(r"(?:order(?:\s+id)?)\s*[:#]?\s*([0-9]+)", user_question, re.IGNORECASE)

                if order_match:
                    params[param_name] = order_match.group(1)

        return params

    def _extract_parameters_with_llm(
        self,
        user_question: str,
        param_names: List[str],
        query_name: str,
        llm: Any,
    ) -> Dict[str, str]:
        """Extract parameters from a user question using a language model."""
        prompt = ChatPromptTemplate.from_messages([
            (
                "system",
                """You are an expert parameter extraction assistant.
    Extract the specified parameters from the user's question.
    Return only a valid JSON object without Markdown, code fences, comments, or explanations.
    Use the exact parameter names provided in the request.
    If a parameter cannot be extracted, use an empty string as its value.""",
            ),
            (
                "human",
                """User question:
    {user_question}

    Query type:
    {query_name}

    Parameters to extract:
    {param_names}

    Return the extracted parameters using the following JSON structure:
    {{"parameter_name": "parameter_value"}}""",),
        ])

        messages = prompt.format_messages(
            user_question=user_question,
            query_name=query_name,
            param_names=", ".join(param_names),
        )

        response = llm.invoke(messages)
        response_content = response.content if hasattr(response, "content") else str(response)

        try:
            json_match = re.search(r"\{.*\}", response_content, re.DOTALL)

            if not json_match:
                return {}

            extracted_params = json.loads(json_match.group(0))

            if not isinstance(extracted_params, dict):
                return {}

            return {param_name: str(extracted_params.get(param_name, "")).strip() for param_name in param_names}
        except (json.JSONDecodeError, TypeError, ValueError) as e:
            print(f"Failed to parse the LLM response as JSON: {e}")
            return {}


def create_vector_query_matcher(
    predefined_cypher_dict: Dict[str, str],
    query_descriptions: Optional[Dict[str, str]] = None,
) -> VectorQueryMatcher:
    """
    Create and return a VectorQueryMatcher instance.

    Parameters
    ----------
    predefined_cypher_dict : Dict[str, str]
        Dictionary of predefined Cypher queries.
    query_descriptions : Optional[Dict[str, str]]
        Optional dictionary containing query descriptions.

    Returns
    -------
    VectorQueryMatcher
        Initialized VectorQueryMatcher instance.
    """
    # Generate default descriptions when no descriptions are provided
    if query_descriptions is None:
        query_descriptions = {}

        for query_name in predefined_cypher_dict:
            query_descriptions[query_name] = query_name.replace("_", " ")

    return VectorQueryMatcher(predefined_cypher_dict, query_descriptions)