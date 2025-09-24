"""
Client API per Midocean
"""
import requests
import time
from typing import Dict, List, Optional, Any
from django.conf import settings
from django.core.cache import cache
from .base import BaseSupplierClient, APIError, AuthenticationError, RateLimitError


class MidoceanClient(BaseSupplierClient):
    """Client per le API Midocean"""
    
    def __init__(self, supplier):
        super().__init__(supplier)
        self.base_url = supplier.api_base_url or settings.MIDOCEAN_BASE_URL
        self.api_key = supplier.api_key or settings.MIDOCEAN_API_KEY
        self.session = requests.Session()
        
        # Headers per tutte le richieste
        self.session.headers.update({
            'x-Gateway-APIKey': self.api_key,
            'User-Agent': 'HotelSync/1.0',
        })
    
    def _make_request(self, endpoint: str, format_type: str = 'json', **params) -> Dict[str, Any]:
        """Effettua una richiesta all'API Midocean"""
        self._handle_rate_limit()
        
        url = f"{self.base_url.rstrip('/')}/{endpoint.lstrip('/')}"
        
        # Headers per formato richiesto
        headers = {}
        if format_type == 'xml':
            headers['Accept'] = 'text/xml'
        elif format_type == 'csv':
            headers['Accept'] = 'text/csv'
        else:
            headers['Accept'] = 'text/json'
        
        try:
            response = self.session.get(url, params=params, headers=headers, timeout=30)
            response.raise_for_status()
            
            # Log della chiamata
            content_size = len(response.content) if response.content else 0
            self._log_api_call(endpoint, content_size)
            
            if format_type == 'json':
                return response.json()
            else:
                return {'content': response.text, 'content_type': response.headers.get('content-type')}
                
        except requests.exceptions.HTTPError as e:
            if response.status_code == 401:
                raise AuthenticationError(f"Autenticazione fallita: {e}")
            elif response.status_code == 429:
                raise RateLimitError(f"Rate limit superato: {e}")
            else:
                raise APIError(f"Errore HTTP {response.status_code}: {e}")
        except requests.exceptions.RequestException as e:
            raise APIError(f"Errore richiesta: {e}")
    
    def get_products(self, language: str = 'it', **kwargs) -> List[Dict[str, Any]]:
        """
        Recupera i prodotti da Midocean
        https://api.midocean.com/gateway/products/2.0?language=it
        """
        cache_key = f"midocean_products_{language}"
        cached_data = cache.get(cache_key)
        
        if cached_data and not kwargs.get('force_refresh'):
            self.logger.info(f"Usando cache per prodotti Midocean ({language})")
            return cached_data
        
        try:
            endpoint = f"gateway/products/2.0"
            data = self._make_request(endpoint, language=language)
            
            products = []
            if 'products' in data:
                products = data['products']
            elif isinstance(data, list):
                products = data
            
            # Cache per 6 ore (prodotti si aggiornano giornalmente)
            cache.set(cache_key, products, 6 * 3600)
            
            self.logger.info(f"Recuperati {len(products)} prodotti da Midocean")
            return products
            
        except Exception as e:
            self.logger.error(f"Errore recupero prodotti Midocean: {e}")
            raise APIError(f"Errore recupero prodotti: {e}")
    
    def get_stock(self, **kwargs) -> List[Dict[str, Any]]:
        """
        Recupera i dati di stock da Midocean
        https://api.midocean.com/gateway/stock/2.0
        """
        cache_key = "midocean_stock"
        cached_data = cache.get(cache_key)
        
        if cached_data and not kwargs.get('force_refresh'):
            self.logger.info("Usando cache per stock Midocean")
            return cached_data
        
        try:
            endpoint = "gateway/stock/2.0"
            data = self._make_request(endpoint)
            
            stock_data = []
            if 'stock' in data:
                stock_data = data['stock']
            elif isinstance(data, list):
                stock_data = data
            
            # Cache per 1 ora (stock si aggiorna ogni ora)
            cache.set(cache_key, stock_data, 3600)
            
            self.logger.info(f"Recuperati {len(stock_data)} record stock da Midocean")
            return stock_data
            
        except Exception as e:
            self.logger.error(f"Errore recupero stock Midocean: {e}")
            raise APIError(f"Errore recupero stock: {e}")
    
    def get_prices(self, **kwargs) -> List[Dict[str, Any]]:
        """
        Recupera i prezzi da Midocean
        https://api.midocean.com/gateway/pricelist/2.0/
        """
        cache_key = "midocean_prices"
        cached_data = cache.get(cache_key)
        
        if cached_data and not kwargs.get('force_refresh'):
            self.logger.info("Usando cache per prezzi Midocean")
            return cached_data
        
        try:
            endpoint = "gateway/pricelist/2.0"
            data = self._make_request(endpoint)
            
            prices = []
            if 'price' in data:
                prices = data['price']
            elif isinstance(data, list):
                prices = data
            
            # Cache per 12 ore (prezzi si aggiornano giornalmente)
            cache.set(cache_key, prices, 12 * 3600)
            
            self.logger.info(f"Recuperati {len(prices)} prezzi da Midocean")
            return prices
            
        except Exception as e:
            self.logger.error(f"Errore recupero prezzi Midocean: {e}")
            raise APIError(f"Errore recupero prezzi: {e}")
    
    def get_print_data(self, **kwargs) -> List[Dict[str, Any]]:
        """
        Recupera i dati di stampa da Midocean
        https://api.midocean.com/gateway/printdata/1.0
        """
        cache_key = "midocean_print_data"
        cached_data = cache.get(cache_key)
        
        if cached_data and not kwargs.get('force_refresh'):
            self.logger.info("Usando cache per dati stampa Midocean")
            return cached_data
        
        try:
            endpoint = "gateway/printdata/1.0"
            data = self._make_request(endpoint)
            
            print_data = []
            if 'products' in data:
                print_data = data['products']
            elif isinstance(data, list):
                print_data = data
            
            # Cache per 24 ore (dati stampa si aggiornano giornalmente)
            cache.set(cache_key, print_data, 24 * 3600)
            
            self.logger.info(f"Recuperati {len(print_data)} record dati stampa da Midocean")
            return print_data
            
        except Exception as e:
            self.logger.error(f"Errore recupero dati stampa Midocean: {e}")
            raise APIError(f"Errore recupero dati stampa: {e}")
    
    def get_print_prices(self, **kwargs) -> List[Dict[str, Any]]:
        """
        Recupera i prezzi di stampa da Midocean
        https://api.midocean.com/gateway/printpricelist/2.0/
        """
        cache_key = "midocean_print_prices"
        cached_data = cache.get(cache_key)
        
        if cached_data and not kwargs.get('force_refresh'):
            self.logger.info("Usando cache per prezzi stampa Midocean")
            return cached_data
        
        try:
            endpoint = "gateway/printpricelist/2.0"
            data = self._make_request(endpoint)
            
            print_prices = []
            if 'print_techniques' in data:
                print_prices = data['print_techniques']
            elif isinstance(data, list):
                print_prices = data
            
            # Cache per 24 ore
            cache.set(cache_key, print_prices, 24 * 3600)
            
            self.logger.info(f"Recuperati {len(print_prices)} prezzi stampa da Midocean")
            return print_prices
            
        except Exception as e:
            self.logger.error(f"Errore recupero prezzi stampa Midocean: {e}")
            raise APIError(f"Errore recupero prezzi stampa: {e}")
    
    def get_product_by_sku(self, sku: str, language: str = 'it') -> Optional[Dict[str, Any]]:
        """Recupera un singolo prodotto per SKU"""
        try:
            products = self.get_products(language=language)
            
            for product in products:
                # Cerca nel prodotto principale
                if product.get('master_code') == sku:
                    return product
                
                # Cerca nelle varianti
                if 'variants' in product:
                    for variant in product['variants']:
                        if variant.get('sku') == sku:
                            # Combina dati prodotto + variante
                            product_data = product.copy()
                            product_data.update(variant)
                            return product_data
            
            return None
            
        except Exception as e:
            self.logger.error(f"Errore recupero prodotto {sku}: {e}")
            return None
    
    def get_stock_by_sku(self, sku: str) -> Optional[Dict[str, Any]]:
        """Recupera stock per un singolo SKU"""
        try:
            stock_data = self.get_stock()
            
            for stock in stock_data:
                if stock.get('sku') == sku:
                    return stock
            
            return None
            
        except Exception as e:
            self.logger.error(f"Errore recupero stock {sku}: {e}")
            return None
    
    def clear_cache(self):
        """Pulisce la cache di Midocean"""
        cache_keys = [
            'midocean_products_it',
            'midocean_products_en', 
            'midocean_stock',
            'midocean_prices',
            'midocean_print_data',
            'midocean_print_prices'
        ]
        
        for key in cache_keys:
            cache.delete(key)
        
        self.logger.info("Cache Midocean pulita")
