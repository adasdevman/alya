import logging
import time
from typing import Callable, Any, Optional
from functools import wraps

logger = logging.getLogger(__name__)

class RetryHandler:
    """
    Gestionnaire de retries pour les appels API.
    
    Cette classe permet de réessayer une fonction en cas d'échec,
    avec un délai exponentiel entre les tentatives.
    """
    
    def __init__(self, max_retries: int = 3, initial_delay: float = 1.0, backoff_factor: float = 2.0):
        """
        Initialise le gestionnaire de retries.
        
        Args:
            max_retries (int): Nombre maximal de tentatives
            initial_delay (float): Délai initial avant la première tentative (en secondes)
            backoff_factor (float): Facteur multiplicatif pour augmenter le délai entre les tentatives
        """
        self.max_retries = max_retries
        self.initial_delay = initial_delay
        self.backoff_factor = backoff_factor
    
    def retry(self, func: Callable, *args, **kwargs) -> Any:
        """
        Exécute une fonction avec retry en cas d'échec.
        
        Args:
            func (Callable): La fonction à exécuter
            *args: Arguments positionnels pour la fonction
            **kwargs: Arguments nommés pour la fonction
            
        Returns:
            Any: Le résultat de la fonction
            
        Raises:
            Exception: La dernière exception levée par la fonction
        """
        retry_count = 0
        delay = self.initial_delay
        last_exception = None
        
        while retry_count <= self.max_retries:
            try:
                return func(*args, **kwargs)
            except Exception as e:
                last_exception = e
                retry_count += 1
                
                if retry_count > self.max_retries:
                    logger.error(f"Échec après {self.max_retries} tentatives: {str(e)}")
                    raise last_exception
                
                logger.warning(f"Tentative {retry_count}/{self.max_retries} échouée: {str(e)}. Nouvel essai dans {delay:.2f}s")
                time.sleep(delay)
                delay *= self.backoff_factor
        
        # Ce code ne devrait jamais être atteint, mais par précaution
        raise last_exception if last_exception else Exception("Échec inattendu dans le système de retry")

def with_retry(max_retries: int = 3, initial_delay: float = 1.0, backoff_factor: float = 2.0) -> Callable:
    """
    Décorateur pour exécuter une fonction avec retry.
    
    Args:
        max_retries (int): Nombre maximal de tentatives
        initial_delay (float): Délai initial avant la première tentative (en secondes)
        backoff_factor (float): Facteur multiplicatif pour augmenter le délai entre les tentatives
        
    Returns:
        Callable: Décorateur de fonction
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            retry_handler = RetryHandler(max_retries, initial_delay, backoff_factor)
            return retry_handler.retry(func, *args, **kwargs)
        return wrapper
    return decorator 