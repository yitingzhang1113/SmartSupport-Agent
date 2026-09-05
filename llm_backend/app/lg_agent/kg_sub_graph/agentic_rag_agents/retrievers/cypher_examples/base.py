from abc import ABC, abstractmethod
from typing import Any

from pydantic import BaseModel, ConfigDict


class BaseCypherExampleRetriever(BaseModel, ABC):
    """
    Abstract base class for Cypher example retrievers.

    Subclasses must implement the `get_examples` method.
    """

    model_config: ConfigDict = ConfigDict(arbitrary_types_allowed=True)

    @abstractmethod
    def get_examples(self, query: str, k: int = 5) -> str:
        """
        Retrieve relevant Cypher query examples based on a user query.

        Parameters
        ----------
        query : str
            User's natural language query.
        k : int, optional
            Maximum number of examples to return. Defaults to 5.

        Returns
        -------
        str
            A formatted string containing example question and Cypher query pairs.
        """
        pass