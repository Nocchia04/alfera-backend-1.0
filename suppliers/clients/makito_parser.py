"""
Parser XML per i file Makito
"""
import os
import xml.etree.ElementTree as ET
from typing import Dict, List, Optional, Any
from django.conf import settings
from django.core.cache import cache
from .base import BaseSupplierClient, APIError, DataParsingError


class MakitoParser(BaseSupplierClient):
    """Parser per i file XML di Makito"""
    
    def __init__(self, supplier):
        super().__init__(supplier)
        self.xml_path = supplier.xml_path or settings.MAKITO_XML_PATH
        
        # File XML di Makito
        self.files = {
            'products': 'alldatafile_ita.xml',
            'stock': 'allstockgroupedfile.xml', 
            'prices': 'pricefile_€805301.xml',
            'print_data': 'allprintdatafile_ita.xml',
            'print_prices': 'PrintPrices_ita.xml'
        }
    
    def _get_file_path(self, file_type: str) -> str:
        """Ottiene il percorso completo del file XML"""
        if file_type not in self.files:
            raise ValueError(f"Tipo file non valido: {file_type}")
        
        filename = self.files[file_type]
        return os.path.join(self.xml_path, filename)
    
    def _parse_xml_file(self, file_path: str) -> ET.Element:
        """Parsa un file XML e restituisce il root element"""
        try:
            if not os.path.exists(file_path):
                raise FileNotFoundError(f"File XML non trovato: {file_path}")
            
            # Verifica che il file non sia vuoto
            if os.path.getsize(file_path) == 0:
                raise DataParsingError(f"File XML vuoto: {file_path}")
            
            tree = ET.parse(file_path)
            return tree.getroot()
            
        except ET.ParseError as e:
            raise DataParsingError(f"Errore parsing XML {file_path}: {e}")
        except Exception as e:
            raise APIError(f"Errore lettura file {file_path}: {e}")
    
    def _xml_to_dict(self, element: ET.Element) -> Dict[str, Any]:
        """Converte un elemento XML in dizionario"""
        result = {}
        
        # Attributi dell'elemento
        if element.attrib:
            result.update(element.attrib)
        
        # Testo dell'elemento
        if element.text and element.text.strip():
            if len(element) == 0:  # Elemento foglia
                return element.text.strip()
            else:
                result['_text'] = element.text.strip()
        
        # Elementi figli
        for child in element:
            child_data = self._xml_to_dict(child)
            
            if child.tag in result:
                # Se esiste già, crea una lista
                if not isinstance(result[child.tag], list):
                    result[child.tag] = [result[child.tag]]
                result[child.tag].append(child_data)
            else:
                result[child.tag] = child_data
        
        return result
    
    def get_products(self, **kwargs) -> List[Dict[str, Any]]:
        """
        Recupera i prodotti dal file alldatafile_ita.xml
        """
        cache_key = "makito_products"
        cached_data = cache.get(cache_key)
        
        if cached_data and not kwargs.get('force_refresh'):
            self.logger.info("Usando cache per prodotti Makito")
            return cached_data
        
        try:
            file_path = self._get_file_path('products')
            root = self._parse_xml_file(file_path)
            
            products = []
            
            # Il root dovrebbe essere <catalog>
            if root.tag != 'catalog':
                raise DataParsingError(f"Root element atteso 'catalog', trovato '{root.tag}'")
            
            # Itera sui prodotti
            for product_elem in root.findall('product'):
                product_data = self._xml_to_dict(product_elem)
                
                # Standardizza i campi
                standardized_product = self._standardize_product_data(product_data)
                products.append(standardized_product)
            
            # Cache per 6 ore
            cache.set(cache_key, products, 6 * 3600)
            
            self.logger.info(f"Recuperati {len(products)} prodotti da Makito XML")
            return products
            
        except Exception as e:
            self.logger.error(f"Errore recupero prodotti Makito: {e}")
            raise APIError(f"Errore recupero prodotti: {e}")
    
    def get_stock(self, **kwargs) -> List[Dict[str, Any]]:
        """
        Recupera i dati di stock dal file allstockgroupedfile.xml
        """
        cache_key = "makito_stock"
        cached_data = cache.get(cache_key)
        
        if cached_data and not kwargs.get('force_refresh'):
            self.logger.info("Usando cache per stock Makito")
            return cached_data
        
        try:
            file_path = self._get_file_path('stock')
            root = self._parse_xml_file(file_path)
            
            stock_data = []
            
            for product_elem in root.findall('product'):
                stock_info = self._xml_to_dict(product_elem)
                
                # Standardizza i dati stock
                standardized_stock = self._standardize_stock_data(stock_info)
                stock_data.append(standardized_stock)
            
            # Cache per 1 ora
            cache.set(cache_key, stock_data, 3600)
            
            self.logger.info(f"Recuperati {len(stock_data)} record stock da Makito XML")
            return stock_data
            
        except Exception as e:
            self.logger.error(f"Errore recupero stock Makito: {e}")
            raise APIError(f"Errore recupero stock: {e}")
    
    def get_prices(self, **kwargs) -> List[Dict[str, Any]]:
        """
        Recupera i prezzi dal file pricefile_€805301.xml
        """
        cache_key = "makito_prices"
        cached_data = cache.get(cache_key)
        
        if cached_data and not kwargs.get('force_refresh'):
            self.logger.info("Usando cache per prezzi Makito")
            return cached_data
        
        try:
            file_path = self._get_file_path('prices')
            root = self._parse_xml_file(file_path)
            
            prices = []
            
            for product_elem in root.findall('product'):
                price_data = self._xml_to_dict(product_elem)
                
                # Standardizza i dati prezzo
                standardized_price = self._standardize_price_data(price_data)
                prices.append(standardized_price)
            
            # Cache per 12 ore
            cache.set(cache_key, prices, 12 * 3600)
            
            self.logger.info(f"Recuperati {len(prices)} prezzi da Makito XML")
            return prices
            
        except Exception as e:
            self.logger.error(f"Errore recupero prezzi Makito: {e}")
            raise APIError(f"Errore recupero prezzi: {e}")
    
    def get_print_data(self, **kwargs) -> List[Dict[str, Any]]:
        """
        Recupera i dati di stampa dal file allprintdatafile_ita.xml
        """
        cache_key = "makito_print_data"
        cached_data = cache.get(cache_key)
        
        if cached_data and not kwargs.get('force_refresh'):
            self.logger.info("Usando cache per dati stampa Makito")
            return cached_data
        
        try:
            file_path = self._get_file_path('print_data')
            root = self._parse_xml_file(file_path)
            
            print_data = []
            
            for product_elem in root.findall('product'):
                print_info = self._xml_to_dict(product_elem)
                
                # Standardizza i dati stampa
                standardized_print = self._standardize_print_data(print_info)
                print_data.append(standardized_print)
            
            # Cache per 24 ore
            cache.set(cache_key, print_data, 24 * 3600)
            
            self.logger.info(f"Recuperati {len(print_data)} record dati stampa da Makito XML")
            return print_data
            
        except Exception as e:
            self.logger.error(f"Errore recupero dati stampa Makito: {e}")
            raise APIError(f"Errore recupero dati stampa: {e}")
    
    def get_print_prices(self, **kwargs) -> List[Dict[str, Any]]:
        """
        Recupera i prezzi di stampa dal file PrintPrices_ita.xml
        """
        cache_key = "makito_print_prices"
        cached_data = cache.get(cache_key)
        
        if cached_data and not kwargs.get('force_refresh'):
            self.logger.info("Usando cache per prezzi stampa Makito")
            return cached_data
        
        try:
            file_path = self._get_file_path('print_prices')
            root = self._parse_xml_file(file_path)
            
            print_prices = []
            
            for printjob_elem in root.find('printjobs').findall('printjob'):
                price_data = self._xml_to_dict(printjob_elem)
                
                # Standardizza i prezzi stampa
                standardized_price = self._standardize_print_price_data(price_data)
                print_prices.append(standardized_price)
            
            # Cache per 24 ore
            cache.set(cache_key, print_prices, 24 * 3600)
            
            self.logger.info(f"Recuperati {len(print_prices)} prezzi stampa da Makito XML")
            return print_prices
            
        except Exception as e:
            self.logger.error(f"Errore recupero prezzi stampa Makito: {e}")
            raise APIError(f"Errore recupero prezzi stampa: {e}")
    
    def _standardize_product_data(self, raw_data: Dict[str, Any]) -> Dict[str, Any]:
        """Standardizza i dati prodotto Makito"""
        return {
            'supplier_ref': raw_data.get('ref', ''),
            'name': raw_data.get('name', ''),
            'type': raw_data.get('type', ''),
            'description': raw_data.get('extendedinfo', ''),
            'short_description': raw_data.get('otherinfo', ''),
            'composition': raw_data.get('composition', ''),
            'brand': raw_data.get('brand', ''),
            'dimensions': f"{raw_data.get('item_long', '')}x{raw_data.get('item_width', '')}x{raw_data.get('item_hight', '')}".strip('x'),
            'weight': raw_data.get('item_weight', ''),
            'main_image': raw_data.get('imagemain', ''),
            'images': self._extract_images(raw_data),
            'categories': self._extract_categories(raw_data),
            'variants': self._extract_variants(raw_data),
            'print_code': raw_data.get('printcode', ''),
            'keywords': raw_data.get('keywords', ''),
            'raw_data': raw_data  # Mantieni i dati originali per debug
        }
    
    def _standardize_stock_data(self, raw_data: Dict[str, Any]) -> Dict[str, Any]:
        """Standardizza i dati stock Makito"""
        infostocks = raw_data.get('infostocks', {})
        if isinstance(infostocks, dict) and 'infostock' in infostocks:
            stock_info = infostocks['infostock']
            if isinstance(stock_info, list):
                stock_info = stock_info[0] if stock_info else {}
        else:
            stock_info = {}
        
        return {
            'supplier_ref': raw_data.get('ref', ''),
            'sku': raw_data.get('reftc', ''),
            'color': raw_data.get('colour', ''),
            'size': raw_data.get('size', ''),
            'stock_quantity': int(stock_info.get('stock', 0)) if stock_info.get('stock') else 0,
            'availability': stock_info.get('available', ''),
            'raw_data': raw_data
        }
    
    def _standardize_price_data(self, raw_data: Dict[str, Any]) -> Dict[str, Any]:
        """Standardizza i dati prezzo Makito"""
        return {
            'supplier_ref': raw_data.get('ref', ''),
            'name': raw_data.get('name', ''),
            'price_ranges': [
                {
                    'min_quantity': int(raw_data.get('section1', '').replace('-', '0')) if raw_data.get('section1') else 0,
                    'price': float(raw_data.get('price1', 0)) if raw_data.get('price1') else 0
                },
                {
                    'min_quantity': int(raw_data.get('section2', 0)) if raw_data.get('section2') else 0,
                    'price': float(raw_data.get('price2', 0)) if raw_data.get('price2') else 0
                },
                {
                    'min_quantity': int(raw_data.get('section3', 0)) if raw_data.get('section3') else 0,
                    'price': float(raw_data.get('price3', 0)) if raw_data.get('price3') else 0
                },
                {
                    'min_quantity': int(raw_data.get('section4', 0)) if raw_data.get('section4') else 0,
                    'price': float(raw_data.get('price4', 0)) if raw_data.get('price4') else 0
                }
            ],
            'raw_data': raw_data
        }
    
    def _standardize_print_data(self, raw_data: Dict[str, Any]) -> Dict[str, Any]:
        """Standardizza i dati stampa Makito"""
        printjobs = raw_data.get('printjobs', {})
        if isinstance(printjobs, dict) and 'printjob' in printjobs:
            jobs = printjobs['printjob']
            if not isinstance(jobs, list):
                jobs = [jobs]
        else:
            jobs = []
        
        return {
            'supplier_ref': raw_data.get('ref', ''),
            'name': raw_data.get('name', ''),
            'print_jobs': jobs,
            'raw_data': raw_data
        }
    
    def _standardize_print_price_data(self, raw_data: Dict[str, Any]) -> Dict[str, Any]:
        """Standardizza i prezzi stampa Makito"""
        return {
            'technique_code': raw_data.get('teccode', ''),
            'code': raw_data.get('code', ''),
            'name': raw_data.get('name', ''),
            'setup_cost': float(raw_data.get('cliche', 0)) if raw_data.get('cliche') else 0,
            'setup_repeat_cost': float(raw_data.get('clicherep', 0)) if raw_data.get('clicherep') else 0,
            'min_job_cost': float(raw_data.get('minjob', 0)) if raw_data.get('minjob') else 0,
            'price_ranges': [
                {
                    'max_quantity': int(raw_data.get('amountunder1', 0)) if raw_data.get('amountunder1') else 0,
                    'price': float(raw_data.get('price1', 0)) if raw_data.get('price1') else 0,
                    'additional_color_price': float(raw_data.get('priceaditionalcol1', 0)) if raw_data.get('priceaditionalcol1') else 0
                },
                {
                    'max_quantity': int(raw_data.get('amountunder2', 0)) if raw_data.get('amountunder2') else 0,
                    'price': float(raw_data.get('price2', 0)) if raw_data.get('price2') else 0,
                    'additional_color_price': float(raw_data.get('priceaditionalcol2', 0)) if raw_data.get('priceaditionalcol2') else 0
                }
                # Aggiungi altri range se necessario
            ],
            'terms': raw_data.get('terms', ''),
            'raw_data': raw_data
        }
    
    def _extract_images(self, product_data: Dict[str, Any]) -> List[str]:
        """Estrae le immagini dal prodotto"""
        images = []
        
        # Immagine principale
        if product_data.get('imagemain'):
            images.append(product_data['imagemain'])
        
        # Altre immagini
        if 'images' in product_data and 'image' in product_data['images']:
            image_list = product_data['images']['image']
            if not isinstance(image_list, list):
                image_list = [image_list]
            
            for img in image_list:
                if isinstance(img, dict) and 'imagemax' in img:
                    if img['imagemax'] and img['imagemax'] not in images:
                        images.append(img['imagemax'])
        
        return images
    
    def _extract_categories(self, product_data: Dict[str, Any]) -> List[Dict[str, str]]:
        """Estrae le categorie dal prodotto"""
        categories = []
        
        if 'categories' in product_data:
            cat_data = product_data['categories']
            for i in range(1, 6):  # category_ref_1 to category_ref_5
                ref_key = f'category_ref_{i}'
                name_key = f'category_name_{i}'
                
                if cat_data.get(ref_key) and cat_data.get(name_key):
                    categories.append({
                        'ref': cat_data[ref_key],
                        'name': cat_data[name_key]
                    })
        
        return categories
    
    def _extract_variants(self, product_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Estrae le varianti dal prodotto"""
        variants = []
        
        if 'variants' in product_data and 'variant' in product_data['variants']:
            variant_list = product_data['variants']['variant']
            if not isinstance(variant_list, list):
                variant_list = [variant_list]
            
            for variant in variant_list:
                variants.append({
                    'matnr': variant.get('matnr', ''),
                    'refct': variant.get('refct', ''),
                    'colour': variant.get('colour', ''),
                    'colour_name': variant.get('colourname', ''),
                    'size': variant.get('size', ''),
                    'image': variant.get('image500px', '')
                })
        
        return variants
    
    def clear_cache(self):
        """Pulisce la cache di Makito"""
        cache_keys = [
            'makito_products',
            'makito_stock',
            'makito_prices',
            'makito_print_data',
            'makito_print_prices'
        ]
        
        for key in cache_keys:
            cache.delete(key)
        
        self.logger.info("Cache Makito pulita")
