"""
Parser CSV per fornitore BIC
"""
import csv
import logging
from typing import Dict, List, Any, Optional
from decimal import Decimal
from .base import BaseSupplierClient
import os

logger = logging.getLogger('sync')

class BICParser(BaseSupplierClient):
    """Parser per file CSV BIC"""
    
    def __init__(self, supplier):
        super().__init__(supplier)
        self.csv_path = supplier.csv_path
        self.preferred_language = 'it'  # Preferenza italiana per hotel
        
    def get_products(self, limit: Optional[int] = None, force_refresh: bool = False) -> List[Dict[str, Any]]:
        """Recupera prodotti dal CSV BIC"""
        logger.info(f"Parsing CSV BIC: {self.csv_path}")
        
        if not os.path.exists(self.csv_path):
            logger.error(f"File CSV non trovato: {self.csv_path}")
            return []
        
        products = []
        products_by_code = {}  # Raggruppa per productCode
        
        try:
            with open(self.csv_path, 'r', encoding='utf-8') as file:
                reader = csv.DictReader(file)
                row_count = 0
                
                for row in reader:
                    row_count += 1
                    
                    # Salta prodotti non attivi
                    if row.get('active') != '1':
                        continue
                    
                    product_code = row.get('productCode', '').strip()
                    language = row.get('language', '').strip()
                    
                    if not product_code:
                        continue
                    
                    # Raggruppa per productCode
                    if product_code not in products_by_code:
                        products_by_code[product_code] = {}
                    
                    products_by_code[product_code][language] = row
                    
                    if limit and len(products_by_code) >= limit:
                        break
                
                logger.info(f"Processate {row_count} righe CSV, trovati {len(products_by_code)} prodotti unici")
                
                # Converti in formato standardizzato
                for product_code, languages in products_by_code.items():
                    product_data = self._standardize_bic_product_data(product_code, languages)
                    if product_data:
                        products.append(product_data)
                
                logger.info(f"Standardizzati {len(products)} prodotti BIC")
                
        except Exception as e:
            logger.error(f"Errore parsing CSV BIC: {e}")
            return []
        
        return products
    
    def _standardize_bic_product_data(self, product_code: str, languages: Dict[str, Dict]) -> Optional[Dict[str, Any]]:
        """Standardizza i dati prodotto BIC"""
        try:
            # Usa lingua preferita, altrimenti inglese, altrimenti prima disponibile
            main_data = None
            if self.preferred_language in languages:
                main_data = languages[self.preferred_language]
            elif 'en' in languages:
                main_data = languages['en']
            else:
                main_data = next(iter(languages.values()))
            
            if not main_data:
                return None
            
            # Dati base prodotto
            product_data = {
                'supplier_ref': product_code,
                'sku': f"BIC_{product_code}",
                'name': main_data.get('name', '').strip(),
                'description': main_data.get('description', '').strip(),
                'short_description': main_data.get('benefits', '').strip()[:500],  # Limita lunghezza
                'brand': main_data.get('brand', 'BIC').strip(),
                'active': main_data.get('active') == '1',
                'images': self._extract_images(main_data),
                'categories': self._extract_categories(main_data),
                'dimensions': self._extract_dimensions(main_data),
                'weight': self._safe_float(main_data.get('weight', '').replace(' g', '')),
                'materials': main_data.get('materials', '').strip(),
                'country_of_origin': main_data.get('countryOfOrigin', '').strip(),
                'customs_code': main_data.get('customsCode', '').strip(),
                'variants': [self._create_main_variant(main_data)],
                'prices': self._extract_prices(main_data),
                'packaging': self._extract_packaging(main_data),
                'multilang_data': languages,  # Mantieni tutti i dati multilingua
                'raw_data': main_data
            }
            
            return product_data
            
        except Exception as e:
            logger.error(f"Errore standardizzazione prodotto BIC {product_code}: {e}")
            return None
    
    def _create_main_variant(self, data: Dict) -> Dict[str, Any]:
        """Crea variante principale del prodotto"""
        return {
            'supplier_variant_ref': data.get('productCode', ''),
            'sku': f"BIC_{data.get('productCode', '')}",
            'color': '',  # BIC non ha varianti colore standard
            'size': '',   # BIC non ha varianti taglia standard
            'gtin': '',   # Non presente nel CSV
            'image': data.get('listImage', '').strip(),
            'current_stock': 0,  # Da aggiornare separatamente
            'current_price': self._get_min_price(data)
        }
    
    def _extract_images(self, data: Dict) -> List[str]:
        """Estrae URL immagini"""
        images = []
        
        # Immagine principale
        list_image = data.get('listImage', '').strip()
        if list_image:
            images.append(list_image)
        
        # Template stampa (se disponibile)
        imprint_template = data.get('imprintTemplate', '').strip()
        if imprint_template and imprint_template != list_image:
            images.append(imprint_template)
        
        return images
    
    def _extract_categories(self, data: Dict) -> List[str]:
        """Estrae categorie (per BIC useremo il brand come categoria base)"""
        categories = []
        
        brand = data.get('brand', '').strip()
        if brand:
            categories.append(brand)
        
        # Aggiungi categoria generale per prodotti promozionali
        categories.append('Prodotti Promozionali')
        
        return categories
    
    def _extract_dimensions(self, data: Dict) -> Dict[str, float]:
        """Estrae dimensioni prodotto"""
        dimensions = {}
        
        width = self._safe_float(data.get('width', '').replace(' cm', ''))
        height = self._safe_float(data.get('height', '').replace(' cm', ''))
        depth = self._safe_float(data.get('depth', '').replace(' cm', ''))
        diameter = self._safe_float(data.get('diameter', '').replace(' cm', ''))
        
        if width: dimensions['width'] = width
        if height: dimensions['height'] = height
        if depth: dimensions['depth'] = depth
        if diameter: dimensions['diameter'] = diameter
        
        return dimensions
    
    def _extract_packaging(self, data: Dict) -> Dict[str, Any]:
        """Estrae informazioni packaging"""
        packaging = {}
        
        # Dimensioni packaging
        pkg_width = self._safe_float(data.get('packaging.width', '').replace(' cm', ''))
        pkg_height = self._safe_float(data.get('packaging.height', '').replace(' cm', ''))
        pkg_depth = self._safe_float(data.get('packaging.depth', '').replace(' cm', ''))
        pkg_weight = self._safe_float(data.get('packaging.weight', '').replace(' g', ''))
        pkg_capacity = data.get('packaging.capacity', '').strip()
        
        if pkg_width: packaging['width'] = pkg_width
        if pkg_height: packaging['height'] = pkg_height
        if pkg_depth: packaging['depth'] = pkg_depth
        if pkg_weight: packaging['weight'] = pkg_weight
        if pkg_capacity: packaging['capacity'] = pkg_capacity
        
        return packaging
    
    def _extract_prices(self, data: Dict) -> List[Dict[str, Any]]:
        """Estrae prezzi a scaglioni"""
        prices = []
        
        currency = data.get('price.currency', 'EUR').strip()
        
        for i in range(1, 11):  # price.1 to price.10
            min_qty_key = f'minQty.{i}'
            max_qty_key = f'maxQty.{i}'
            price_key = f'price.{i}'
            
            min_qty = self._safe_int(data.get(min_qty_key, ''))
            max_qty = self._safe_int(data.get(max_qty_key, ''))
            price = self._safe_float(data.get(price_key, ''))
            
            if price and min_qty:
                prices.append({
                    'min_quantity': min_qty,
                    'max_quantity': max_qty if max_qty else 999999,
                    'price': price,
                    'currency': currency
                })
        
        return prices
    
    def _get_min_price(self, data: Dict) -> Optional[float]:
        """Ottiene il prezzo minimo (primo scaglione)"""
        return self._safe_float(data.get('price.1', ''))
    
    def _safe_float(self, value: str) -> Optional[float]:
        """Conversione sicura a float"""
        if not value or not isinstance(value, str):
            return None
        
        try:
            # Rimuovi spazi e caratteri comuni
            cleaned = value.strip().replace(',', '.')
            return float(cleaned) if cleaned else None
        except (ValueError, TypeError):
            return None
    
    def _safe_int(self, value: str) -> Optional[int]:
        """Conversione sicura a int"""
        if not value or not isinstance(value, str):
            return None
        
        try:
            cleaned = value.strip()
            return int(float(cleaned)) if cleaned else None
        except (ValueError, TypeError):
            return None
    
    def get_stock(self, force_refresh: bool = False) -> List[Dict[str, Any]]:
        """BIC CSV non contiene stock separato - ritorna stock base"""
        logger.info("BIC: Stock non disponibile nel CSV, usando stock di default")
        return []
    
    def get_prices(self, force_refresh: bool = False) -> List[Dict[str, Any]]:
        """I prezzi sono già inclusi nei dati prodotto"""
        logger.info("BIC: Prezzi già inclusi nei dati prodotto")
        return []
    
    def get_print_data(self, force_refresh: bool = False) -> List[Dict[str, Any]]:
        """Estrae dati stampa da CSV"""
        products = self.get_products(force_refresh=force_refresh)
        print_data = []
        
        for product in products:
            raw_data = product.get('raw_data', {})
            
            if raw_data.get('imprintRequired') == '1':
                print_data.append({
                    'supplier_ref': product['supplier_ref'],
                    'imprint_required': True,
                    'imprint_template': raw_data.get('imprintTemplate', ''),
                    'print_areas': self._extract_print_areas(raw_data)
                })
        
        return print_data
    
    def _extract_print_areas(self, data: Dict) -> List[Dict[str, Any]]:
        """Estrae aree di stampa (da implementare in base ai dati BIC)"""
        # Per ora ritorna area generica
        return [{
            'area_name': 'Standard',
            'max_colors': 4,  # BIC supporta fino a 4 colori
            'print_methods': ['Tampografia', 'Serigrafia']
        }]
    
    def get_print_prices(self, force_refresh: bool = False) -> List[Dict[str, Any]]:
        """BIC: Prezzi stampa non separati nel CSV"""
        logger.info("BIC: Prezzi stampa non disponibili separatamente")
        return []
    
    def clear_cache(self):
        """BIC CSV non usa cache"""
        logger.info("BIC: Nessuna cache da pulire per parser CSV")
        pass
