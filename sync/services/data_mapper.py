"""
Servizio per mappare e unificare i dati da diversi fornitori
"""
import logging
import re
from typing import Dict, List, Optional, Any
from django.utils.text import slugify
from suppliers.models import Supplier
from products.models import Category

logger = logging.getLogger('sync')


class DataMapper:
    """Mapper per unificare dati da fornitori diversi"""
    
    def __init__(self):
        self.logger = logger
        
        # Mapping categorie comuni
        self.category_mapping = {
            'MIDOCEAN': {
                'Office & Writing': 'Ufficio e Scrittura',
                'Notebooks': 'Quaderni',
                'Hard cover': 'Copertina Rigida',
                'Bags & Travel': 'Borse e Viaggi',
                'Technology': 'Tecnologia',
                'Drinkware': 'Bevande',
                'Outdoor & Sport': 'Sport e Tempo Libero'
            },
            'MAKITO': {
                'Attrezzi, Bricolage e Auto': 'Attrezzi e Bricolage',
                'Agricoltura': 'Agricoltura',
                'Casa e Giardino': 'Casa e Giardino'
            },
            'BIC': {
                'BIC': 'BIC',
                'Prodotti Promozionali': 'Prodotti Promozionali'
            }
        }
    
    def map_product_data(self, raw_data: Dict[str, Any], supplier: Supplier) -> Dict[str, Any]:
        """Mappa i dati del prodotto in formato unificato"""
        if supplier.supplier_type == 'MIDOCEAN':
            return self._map_midocean_product(raw_data, supplier)
        elif supplier.supplier_type == 'MAKITO':
            return self._map_makito_product(raw_data, supplier)
        elif supplier.supplier_type == 'BIC':
            return self._map_bic_product(raw_data, supplier)
        else:
            raise ValueError(f"Supplier type non supportato: {supplier.supplier_type}")
    
    def map_stock_data(self, raw_data: Dict[str, Any], supplier: Supplier) -> Dict[str, Any]:
        """Mappa i dati di stock in formato unificato"""
        if supplier.supplier_type == 'MIDOCEAN':
            return self._map_midocean_stock(raw_data, supplier)
        elif supplier.supplier_type == 'MAKITO':
            return self._map_makito_stock(raw_data, supplier)
        elif supplier.supplier_type == 'BIC':
            return self._map_bic_stock(raw_data, supplier)
        else:
            raise ValueError(f"Supplier type non supportato: {supplier.supplier_type}")
    
    def map_price_data(self, raw_data: Dict[str, Any], supplier: Supplier) -> List[Dict[str, Any]]:
        """Mappa i dati di prezzo in formato unificato"""
        if supplier.supplier_type == 'MIDOCEAN':
            return self._map_midocean_prices(raw_data, supplier)
        elif supplier.supplier_type == 'MAKITO':
            return self._map_makito_prices(raw_data, supplier)
        elif supplier.supplier_type == 'BIC':
            return self._map_bic_prices(raw_data, supplier)
        else:
            raise ValueError(f"Supplier type non supportato: {supplier.supplier_type}")
    
    def _map_midocean_product(self, raw_data: Dict[str, Any], supplier: Supplier) -> Dict[str, Any]:
        """Mappa prodotto Midocean"""
        try:
            # Dati base prodotto
            mapped_data = {
                'supplier': supplier,
                'supplier_ref': raw_data.get('master_code', ''),
                'name': raw_data.get('product_name', ''),
                'description': raw_data.get('long_description', ''),
                'short_description': raw_data.get('short_description', ''),
                'brand': raw_data.get('brand', ''),
                'material': raw_data.get('material', ''),
                'dimensions': raw_data.get('dimensions', ''),
                'is_printable': raw_data.get('printable') == 'yes',
                'main_image': '',
                'images': [],
                'variants': [],
                'categories': [],
                'print_areas': []
            }
            
            # Genera SKU unico
            mapped_data['sku'] = f"MID_{raw_data.get('master_code', '')}"
            
            # Categorie
            category_path = []
            if raw_data.get('category_level1'):
                category_path.append(raw_data['category_level1'])
            if raw_data.get('category_level2'):
                category_path.append(raw_data['category_level2'])
            if raw_data.get('category_level3'):
                category_path.append(raw_data['category_level3'])
            
            mapped_data['category_path'] = category_path
            
            # Varianti
            if 'variants' in raw_data:
                variants = raw_data['variants']
                if not isinstance(variants, list):
                    variants = [variants]
                
                for variant in variants:
                    mapped_variant = {
                        'supplier_variant_ref': variant.get('sku', ''),
                        'sku': variant.get('sku', ''),
                        'color': variant.get('color_description', ''),
                        'color_code': variant.get('color_code', ''),
                        'size': variant.get('size', ''),
                        'gtin': variant.get('gtin', ''),
                        'image': ''
                    }
                    
                    # Immagini variante
                    if 'digital_assets' in variant:
                        for asset in variant['digital_assets']:
                            if asset.get('type') == 'image':
                                mapped_variant['image'] = asset.get('url_highress') or asset.get('url', '')
                                break
                    
                    mapped_data['variants'].append(mapped_variant)
            
            # Immagini prodotto principale
            if 'digital_assets' in raw_data:
                for asset in raw_data['digital_assets']:
                    if asset.get('type') == 'image':
                        image_url = asset.get('url_highress') or asset.get('url', '')
                        if image_url:
                            if not mapped_data['main_image']:
                                mapped_data['main_image'] = image_url
                            mapped_data['images'].append(image_url)
            
            return mapped_data
            
        except Exception as e:
            self.logger.error(f"Errore mapping prodotto Midocean: {e}")
            raise
    
    def _map_makito_product(self, raw_data: Dict[str, Any], supplier: Supplier) -> Dict[str, Any]:
        """Mappa prodotto Makito"""
        try:
            mapped_data = {
                'supplier': supplier,
                'supplier_ref': raw_data.get('supplier_ref', ''),
                'name': raw_data.get('name', ''),
                'description': raw_data.get('description', ''),
                'short_description': raw_data.get('short_description', ''),
                'brand': raw_data.get('brand', ''),
                'material': raw_data.get('composition', ''),
                'dimensions': raw_data.get('dimensions', ''),
                'weight': self._parse_weight(raw_data.get('weight')),
                'is_printable': bool(raw_data.get('print_code')),
                'main_image': raw_data.get('main_image', ''),
                'images': raw_data.get('images', []),
                'variants': [],
                'categories': raw_data.get('categories', []),
                'print_areas': []
            }
            
            # Genera SKU unico
            mapped_data['sku'] = f"MAK_{raw_data.get('supplier_ref', '')}"
            
            # Mappa varianti Makito
            for variant in raw_data.get('variants', []):
                mapped_variant = {
                    'supplier_variant_ref': variant.get('refct', ''),
                    'sku': variant.get('refct', ''),
                    'color': variant.get('colour', ''),
                    'color_code': variant.get('colour', ''),
                    'size': variant.get('size', ''),
                    'gtin': variant.get('matnr', ''),
                    'image': variant.get('image', '')
                }
                mapped_data['variants'].append(mapped_variant)
            
            return mapped_data
            
        except Exception as e:
            self.logger.error(f"Errore mapping prodotto Makito: {e}")
            raise
    
    def _map_midocean_stock(self, raw_data: Dict[str, Any], supplier: Supplier) -> Dict[str, Any]:
        """Mappa stock Midocean"""
        return {
            'sku': raw_data.get('sku', ''),
            'stock_quantity': int(raw_data.get('qty', 0)),
            'availability_status': 'available' if int(raw_data.get('qty', 0)) > 0 else 'out_of_stock',
            'next_arrival_date': raw_data.get('first_arrival_date'),
            'next_arrival_quantity': int(raw_data.get('first_arrival_qty', 0)) if raw_data.get('first_arrival_qty') else None
        }
    
    def _map_makito_stock(self, raw_data: Dict[str, Any], supplier: Supplier) -> Dict[str, Any]:
        """Mappa stock Makito"""
        return {
            'sku': raw_data.get('sku', ''),
            'supplier_ref': raw_data.get('supplier_ref', ''),
            'color': raw_data.get('color', ''),
            'size': raw_data.get('size', ''),
            'stock_quantity': raw_data.get('stock_quantity', 0),
            'availability_status': raw_data.get('availability', 'unknown')
        }
    
    def _map_midocean_prices(self, raw_data: Dict[str, Any], supplier: Supplier) -> List[Dict[str, Any]]:
        """Mappa prezzi Midocean"""
        prices = []
        
        sku = raw_data.get('sku', '')
        base_price = float(raw_data.get('price', 0))
        
        # Prezzo base
        prices.append({
            'sku': sku,
            'price': base_price,
            'min_quantity': 1,
            'max_quantity': None,
            'currency': 'EUR',
            'valid_until': raw_data.get('valid_until')
        })
        
        # Prezzi a scaglioni
        if 'scale' in raw_data:
            for scale in raw_data['scale']:
                prices.append({
                    'sku': sku,
                    'price': float(scale.get('price', 0)),
                    'min_quantity': int(scale.get('minimum_quantity', 1)),
                    'max_quantity': None,
                    'currency': 'EUR',
                    'valid_until': raw_data.get('valid_until')
                })
        
        return prices
    
    def _map_makito_prices(self, raw_data: Dict[str, Any], supplier: Supplier) -> List[Dict[str, Any]]:
        """Mappa prezzi Makito"""
        prices = []
        supplier_ref = raw_data.get('supplier_ref', '')
        
        for price_range in raw_data.get('price_ranges', []):
            if price_range.get('price', 0) > 0:
                prices.append({
                    'supplier_ref': supplier_ref,
                    'price': price_range['price'],
                    'min_quantity': price_range['min_quantity'],
                    'max_quantity': None,
                    'currency': 'EUR'
                })
        
        return prices
    
    def create_or_get_category(self, category_path: List[str], supplier: Supplier) -> Optional[Category]:
        """Crea o recupera una categoria dalla gerarchia"""
        if not category_path:
            return None
        
        parent_category = None
        
        for category_name in category_path:
            # Mappa il nome categoria se necessario
            mapped_name = self._map_category_name(category_name, supplier.supplier_type)
            slug = slugify(mapped_name)
            
            # Cerca categoria esistente
            category, created = Category.objects.get_or_create(
                slug=slug,
                defaults={
                    'name': mapped_name,
                    'parent': parent_category
                }
            )
            
            if created:
                self.logger.info(f"Creata categoria: {mapped_name}")
            
            parent_category = category
        
        return parent_category
    
    def _map_category_name(self, category_name: str, supplier_type: str) -> str:
        """Mappa il nome categoria usando il mapping definito"""
        mapping = self.category_mapping.get(supplier_type, {})
        return mapping.get(category_name, category_name)
    
    def _parse_weight(self, weight_str: str) -> Optional[float]:
        """Parsa il peso da stringa"""
        if not weight_str:
            return None
        
        try:
            # Estrae numeri dalla stringa
            numbers = re.findall(r'\d+\.?\d*', str(weight_str))
            if numbers:
                return float(numbers[0])
        except (ValueError, TypeError):
            pass
        
        return None
    
    def _parse_dimensions(self, dimensions_str: str) -> Dict[str, Optional[float]]:
        """Parsa le dimensioni da stringa"""
        dimensions = {'length': None, 'width': None, 'height': None}
        
        if not dimensions_str:
            return dimensions
        
        try:
            # Cerca pattern tipo "21X14X1,6 CM" o "21x14x1.6"
            pattern = r'(\d+\.?\d*)[xX×](\d+\.?\d*)[xX×](\d+\.?\d*)'
            match = re.search(pattern, str(dimensions_str))
            
            if match:
                dimensions['length'] = float(match.group(1))
                dimensions['width'] = float(match.group(2))
                dimensions['height'] = float(match.group(3))
        except (ValueError, TypeError):
            pass
        
        return dimensions
    
    def prepare_woocommerce_data(self, product_data: Dict[str, Any]) -> Dict[str, Any]:
        """Prepara i dati per WooCommerce"""
        # Converti datetime in stringa se necessario
        last_sync = product_data.get('updated_at', '')
        if hasattr(last_sync, 'isoformat'):
            last_sync = last_sync.isoformat()
        elif last_sync:
            last_sync = str(last_sync)
        
        woo_data = {
            'name': product_data.get('name', ''),
            'sku': product_data.get('sku', ''),
            'description': product_data.get('description', ''),
            'short_description': product_data.get('short_description', ''),
            'images': product_data.get('images', []),
            'supplier_name': product_data.get('supplier', {}).get('name', '') if isinstance(product_data.get('supplier'), dict) else str(product_data.get('supplier', '')),
            'supplier_ref': product_data.get('supplier_ref', ''),
            'stock_quantity': 0,  # Sarà aggiornato dal sync stock
            'price': None,  # Sarà aggiornato dal sync prezzi
            'categories': [],  # Sarà popolato dopo creazione categorie
            'attributes': {},
            'last_sync': last_sync
        }
        
        # Attributi da varianti
        if product_data.get('variants'):
            colors = set()
            sizes = set()
            
            for variant in product_data['variants']:
                if variant.get('color'):
                    colors.add(variant['color'])
                if variant.get('size'):
                    sizes.add(variant['size'])
            
            if colors:
                woo_data['attributes']['Colore'] = list(colors)
            if sizes:
                woo_data['attributes']['Taglia'] = list(sizes)
        
        # Dimensioni e peso
        if product_data.get('weight'):
            woo_data['weight'] = product_data['weight']
        
        dimensions = self._parse_dimensions(product_data.get('dimensions', ''))
        if any(dimensions.values()):
            woo_data.update(dimensions)
        
        return woo_data
    
    def _map_bic_product(self, raw_data: Dict[str, Any], supplier: Supplier) -> Dict[str, Any]:
        """Mappa prodotto BIC"""
        try:
            # I dati BIC sono già standardizzati dal parser
            return {
                'name': raw_data.get('name', ''),
                'sku': raw_data.get('sku', ''),
                'supplier_ref': raw_data.get('supplier_ref', ''),
                'supplier': supplier,  # ✅ AGGIUNTO CAMPO SUPPLIER
                'description': raw_data.get('description', ''),
                'short_description': raw_data.get('short_description', ''),
                'brand': raw_data.get('brand', 'BIC'),
                'categories': raw_data.get('categories', []),
                'images': raw_data.get('images', []),
                'dimensions': raw_data.get('dimensions', {}),
                'weight': raw_data.get('weight'),
                'materials': raw_data.get('materials', ''),
                'country_of_origin': raw_data.get('country_of_origin', ''),
                'customs_code': raw_data.get('customs_code', ''),
                'variants': raw_data.get('variants', []),
                'prices': raw_data.get('prices', []),
                'packaging': raw_data.get('packaging', {}),
                'multilang_data': raw_data.get('multilang_data', {}),
                'active': raw_data.get('active', True)
            }
        except Exception as e:
            self.logger.error(f"Errore mapping prodotto BIC: {e}")
            return {}
    
    def _map_bic_stock(self, raw_data: Dict[str, Any], supplier: Supplier) -> Dict[str, Any]:
        """Mappa stock BIC"""
        # BIC non ha dati stock separati, usa default
        return {
            'supplier_ref': raw_data.get('supplier_ref', ''),
            'sku': raw_data.get('sku', ''),
            'supplier': supplier,  # ✅ AGGIUNTO CAMPO SUPPLIER
            'quantity': 0,  # BIC non fornisce stock nel CSV
            'location': '',
            'updated_at': None
        }
    
    def _map_bic_prices(self, raw_data: Dict[str, Any], supplier: Supplier) -> List[Dict[str, Any]]:
        """Mappa prezzi BIC"""
        try:
            prices = []
            bic_prices = raw_data.get('prices', [])
            
            for price_data in bic_prices:
                prices.append({
                    'supplier_ref': raw_data.get('supplier_ref', ''),
                    'sku': raw_data.get('sku', ''),
                    'supplier': supplier,  # ✅ AGGIUNTO CAMPO SUPPLIER
                    'min_quantity': price_data.get('min_quantity', 1),
                    'max_quantity': price_data.get('max_quantity', 999999),
                    'price': price_data.get('price', 0),
                    'currency': price_data.get('currency', 'EUR'),
                    'valid_from': None,
                    'valid_to': None
                })
            
            return prices
        except Exception as e:
            self.logger.error(f"Errore mapping prezzi BIC: {e}")
            return []
