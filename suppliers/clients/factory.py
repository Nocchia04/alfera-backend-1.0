"""
Factory per creare i client appropriati per ogni fornitore
"""
from typing import Optional
from suppliers.models import Supplier
from .base import BaseSupplierClient
from .midocean_client import MidoceanClient
from .makito_parser import MakitoParser
from .mkto_parser import MKTOParser
from .bic_parser import BICParser


class SupplierClientFactory:
    """Factory per creare client fornitori"""
    
    @staticmethod
    def create_client(supplier: Supplier) -> Optional[BaseSupplierClient]:
        """Crea il client appropriato per il fornitore"""
        
        if not supplier.is_active:
            raise ValueError(f"Fornitore {supplier.name} non è attivo")
        
        if supplier.supplier_type == 'MIDOCEAN':
            return MidoceanClient(supplier)
        elif supplier.supplier_type == 'MAKITO':
            # Usa il parser MKTO ottimizzato per il fornitore MKTO
            if supplier.code == 'MKTO':
                return MKTOParser(supplier)
            else:
                return MakitoParser(supplier)
        elif supplier.supplier_type == 'BIC':
            return BICParser(supplier)
        else:
            raise ValueError(f"Tipo fornitore non supportato: {supplier.supplier_type}")
    
    @staticmethod
    def get_available_suppliers() -> list:
        """Restituisce la lista dei fornitori disponibili"""
        return Supplier.objects.filter(is_active=True)
    
    @staticmethod
    def test_all_connections() -> dict:
        """Testa le connessioni di tutti i fornitori"""
        results = {}
        
        for supplier in Supplier.objects.filter(is_active=True):
            try:
                client = SupplierClientFactory.create_client(supplier)
                results[supplier.name] = {
                    'success': client.test_connection(),
                    'configured': supplier.is_api_configured,
                    'error': None
                }
            except Exception as e:
                results[supplier.name] = {
                    'success': False,
                    'configured': supplier.is_api_configured,
                    'error': str(e)
                }
        
        return results
