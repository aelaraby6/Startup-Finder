import os
import importlib
import inspect
from typing import List
from .base import BaseFetcher
from config import logger

def get_all_fetchers() -> List[BaseFetcher]:
    """
    Dynamically discovers and instantiates all fetchers inside the fetchers folder
    that subclass BaseFetcher (excluding base.py and __init__.py).
    
    Returns:
        List[BaseFetcher]: A list of instantiated fetcher classes.
    """
    fetchers: List[BaseFetcher] = []
    dir_path = os.path.dirname(__file__)
    
    logger.info("Initializing dynamic fetcher discovery...")
    
    for filename in os.listdir(dir_path):
        if filename.endswith(".py") and filename not in ("base.py", "__init__.py"):
            module_name = f"fetchers.{filename[:-3]}"
            try:
                module = importlib.import_module(module_name)
                found_in_module = False
                for name, obj in inspect.getmembers(module):
                    if inspect.isclass(obj) and issubclass(obj, BaseFetcher) and obj is not BaseFetcher:
                        fetchers.append(obj())
                        found_in_module = True
                        logger.info(f"Discovered and loaded fetcher: {obj.__name__} from {filename}")
                if not found_in_module:
                    logger.warning(f"No BaseFetcher subclass found in {filename}")
            except Exception as e:
                logger.error(f"Failed to load fetcher module {module_name}: {e}", exc_info=True)
                
    logger.info(f"Total fetchers loaded: {len(fetchers)}")
    return fetchers
