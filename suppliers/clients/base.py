"""
Client base per tutti i fornitori
"""
import logging
import time
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any
from django.conf import settings


logger = logging.getLogger('suppliers')


class BaseSupplierClient(ABC):
    """Classe base per tutti i client fornitori"""
    
    def __init__(self, supplier):
        self.supplier = supplier
        self.logger = logger
        
    @abstractmethod
    def get_products(self, **kwargs) -> List[Dict[str, Any]]:
        """Recupera i prodotti dal fornitore"""
        pass
    
    @abstractmethod
    def get_stock(self, **kwargs) -> List[Dict[str, Any]]:
        """Recupera i dati di stock dal fornitore"""
        pass
    
    @abstractmethod
    def get_prices(self, **kwargs) -> List[Dict[str, Any]]:
        """Recupera i prezzi dal fornitore"""
        pass
    
    def get_print_data(self, **kwargs) -> List[Dict[str, Any]]:
        """Recupera i dati di stampa (opzionale)"""
        return []
    
    def get_print_prices(self, **kwargs) -> List[Dict[str, Any]]:
        """Recupera i prezzi di stampa (opzionale)"""
        return []
    
    def test_connection(self) -> bool:
        """Testa la connessione con il fornitore"""
        try:
            # Prova a recuperare un piccolo set di dati
            self.get_products(limit=1)
            return True
        except Exception as e:
            self.logger.error(f"Test connessione fallito per {self.supplier.name}: {e}")
            return False
    
    def _handle_rate_limit(self):
        """Gestisce il rate limiting"""
        if hasattr(self.supplier, 'rate_limit'):
            rate_limit = self.supplier.rate_limit
            if not rate_limit.can_make_request():
                self.logger.warning(f"Rate limit raggiunto per {self.supplier.name}")
                time.sleep(60)  # Aspetta 1 minuto
            else:
                rate_limit.increment_requests()
    
    def _log_api_call(self, endpoint: str, response_size: int = 0):
        """Log delle chiamate API"""
        self.logger.info(f"API call: {self.supplier.name} - {endpoint} - {response_size} items")


class APIError(Exception):
    """Errore generico API"""
    pass


class RateLimitError(APIError):
    """Errore rate limit"""
    pass


class AuthenticationError(APIError):
    """Errore autenticazione"""
    pass


class DataParsingError(APIError):
    """Errore parsing dati"""
    pass
