import abc
from typing import List
from models import Company

class BaseFetcher(abc.ABC):
    """
    Abstract Base Class for all startup data fetchers.
    All subclasses must implement the fetch method.
    """
    
    @property
    def name(self) -> str:
        """Returns a user-friendly name of the fetcher source (derived from class name)."""
        return self.__class__.__name__.replace("Fetcher", "")

    @abc.abstractmethod
    async def fetch(self, country: str, category: str, max_results: int) -> List[Company]:
        """
        Fetches startups for a given country and category asynchronously.
        
        Args:
            country (str): The target country name.
            category (str): The target startup industry/category (e.g., AI, SaaS).
            max_results (int): The maximum number of results to return from this fetcher.
            
        Returns:
            List[Company]: A list of Company objects matching the search criteria.
        """
        pass
