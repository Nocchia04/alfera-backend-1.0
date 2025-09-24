"""
Parser ottimizzato specifico per MKTO Web Service
"""
import os
import xml.etree.ElementTree as ET
from typing import Dict, List, Optional, Any, Generator
from django.conf import settings
try:
    from django.core.cache import cache
    CACHE_AVAILABLE = True
except Exception:
    CACHE_AVAILABLE = False
    cache = None
from .base import BaseSupplierClient, APIError, DataParsingError
import logging


logger = logging.getLogger('suppliers')


class MKTOParser(BaseSupplierClient):
    """Parser ottimizzato per i file XML di MKTO"""
    
    def __init__(self, supplier):
        super().__init__(supplier)
        self.xml_path = supplier.xml_path or settings.MAKITO_XML_PATH
        
        # File XML di MKTO (nomi reali dai tuoi file)
        self.files = {
            'products': 'alldatafile_ita.xml',
            'stock': 'allstockgroupedfile.xml', 
            'prices': 'pricefile_€805301.xml',
            'print_data': 'allprintdatafile_ita.xml',
            'print_prices': 'PrintPrices_ita.xml'
        }
        
        self.logger = logger
    
    def _get_file_path(self, file_type: str) -> str:
        """Ottiene il percorso completo del file XML"""
        if file_type not in self.files:
            raise ValueError(f"Tipo file non valido: {file_type}")
        
        filename = self.files[file_type]
        file_path = os.path.join(self.xml_path, filename)
        
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File XML non trovato: {file_path}")
        
        return file_path
    
    def _parse_xml_iterative(self, file_path: str, target_tag: str) -> Generator[Dict[str, Any], None, None]:
        """Parsa XML in modo iterativo per file grandi"""
        try:
            # Parse iterativo per gestire file grandi senza caricare tutto in memoria
            context = ET.iterparse(file_path, events=('start', 'end'))
            context = iter(context)
            event, root = next(context)
            
            current_element = None
            
            for event, elem in context:
                if event == 'start' and elem.tag == target_tag:
                    current_element = elem
                elif event == 'end' and elem.tag == target_tag and current_element is not None:
                    # Converte elemento in dizionario
                    data = self._xml_element_to_dict(current_element)
                    yield data
                    
                    # Pulisce memoria
                    current_element.clear()
                    root.clear()
                    current_element = None
                    
        except ET.ParseError as e:
            raise DataParsingError(f"Errore parsing XML {file_path}: {e}")
        except Exception as e:
            raise APIError(f"Errore lettura file {file_path}: {e}")
    
    def _xml_element_to_dict(self, element: ET.Element) -> Dict[str, Any]:
        """Converte un elemento XML in dizionario ottimizzato"""
        result = {}
        
        # Testo dell'elemento
        if element.text and element.text.strip():
            if len(element) == 0:  # Elemento foglia
                return element.text.strip()
            else:
                result['_text'] = element.text.strip()
        
        # Elementi figli
        for child in element:
            child_data = self._xml_element_to_dict(child)
            
            if child.tag in result:
                # Se esiste già, crea una lista
                if not isinstance(result[child.tag], list):
                    result[child.tag] = [result[child.tag]]
                result[child.tag].append(child_data)
            else:
                result[child.tag] = child_data
        
        return result
    
    def get_products(self, limit: Optional[int] = None, **kwargs) -> List[Dict[str, Any]]:
        """
        Recupera i prodotti dal file alldatafile_ita.xml
        """
        cache_key = "mkto_products"
        
        if not kwargs.get('force_refresh') and CACHE_AVAILABLE:
            try:
                cached_data = cache.get(cache_key)
                if cached_data:
                    self.logger.info("Usando cache per prodotti MKTO")
                    return cached_data[:limit] if limit else cached_data
            except Exception as e:
                self.logger.warning(f"Cache non disponibile, parsing diretto: {e}")
        
        try:
            file_path = self._get_file_path('products')
            self.logger.info(f"Parsing prodotti MKTO da: {file_path}")
            
            products = []
            count = 0
            
            # Parse iterativo per gestire file grandi
            for product_data in self._parse_xml_iterative(file_path, 'product'):
                standardized_product = self._standardize_mkto_product(product_data)
                products.append(standardized_product)
                
                count += 1
                if count % 100 == 0:
                    self.logger.info(f"Processati {count} prodotti...")
                
                # Limita se specificato
                if limit and count >= limit:
                    break
            
            # Cache per 2 ore (file grandi)
            if CACHE_AVAILABLE:
                try:
                    cache.set(cache_key, products, 2 * 3600)
                except Exception as e:
                    self.logger.warning(f"Impossibile salvare in cache: {e}")
            
            self.logger.info(f"Recuperati {len(products)} prodotti da MKTO XML")
            return products
            
        except Exception as e:
            self.logger.error(f"Errore recupero prodotti MKTO: {e}")
            raise APIError(f"Errore recupero prodotti: {e}")
    
    def get_stock(self, limit: Optional[int] = None, **kwargs) -> List[Dict[str, Any]]:
        """
        Recupera i dati di stock dal file allstockgroupedfile.xml
        """
        cache_key = "mkto_stock"
        
        if not kwargs.get('force_refresh') and CACHE_AVAILABLE:
            try:
                cached_data = cache.get(cache_key)
                if cached_data:
                    self.logger.info("Usando cache per stock MKTO")
                    return cached_data[:limit] if limit else cached_data
            except Exception as e:
                self.logger.warning(f"Cache non disponibile per stock: {e}")
        
        try:
            file_path = self._get_file_path('stock')
            self.logger.info(f"Parsing stock MKTO da: {file_path}")
            
            stock_data = []
            count = 0
            
            for stock_info in self._parse_xml_iterative(file_path, 'product'):
                standardized_stock = self._standardize_mkto_stock(stock_info)
                stock_data.append(standardized_stock)
                
                count += 1
                if count % 500 == 0:
                    self.logger.info(f"Processati {count} record stock...")
                
                if limit and count >= limit:
                    break
            
            # Cache per 30 minuti (stock cambia più spesso)
            if CACHE_AVAILABLE:
                try:
                    cache.set(cache_key, stock_data, 30 * 60)
                except Exception:
                    pass
            
            self.logger.info(f"Recuperati {len(stock_data)} record stock da MKTO XML")
            return stock_data
            
        except Exception as e:
            self.logger.error(f"Errore recupero stock MKTO: {e}")
            raise APIError(f"Errore recupero stock: {e}")
    
    def get_prices(self, limit: Optional[int] = None, **kwargs) -> List[Dict[str, Any]]:
        """
        Recupera i prezzi dal file pricefile_€805301.xml
        """
        cache_key = "mkto_prices"
        
        if not kwargs.get('force_refresh') and CACHE_AVAILABLE:
            try:
                cached_data = cache.get(cache_key)
                if cached_data:
                    self.logger.info("Usando cache per prezzi MKTO")
                    return cached_data[:limit] if limit else cached_data
            except Exception:
                pass
        
        try:
            file_path = self._get_file_path('prices')
            self.logger.info(f"Parsing prezzi MKTO da: {file_path}")
            
            prices = []
            count = 0
            
            for price_data in self._parse_xml_iterative(file_path, 'product'):
                standardized_price = self._standardize_mkto_prices(price_data)
                prices.append(standardized_price)
                
                count += 1
                if count % 200 == 0:
                    self.logger.info(f"Processati {count} prezzi...")
                
                if limit and count >= limit:
                    break
            
            # Cache per 4 ore (prezzi cambiano meno spesso)
            if CACHE_AVAILABLE:
                try:
                    cache.set(cache_key, prices, 4 * 3600)
                except Exception:
                    pass
            
            self.logger.info(f"Recuperati {len(prices)} prezzi da MKTO XML")
            return prices
            
        except Exception as e:
            self.logger.error(f"Errore recupero prezzi MKTO: {e}")
            raise APIError(f"Errore recupero prezzi: {e}")
    
    def get_print_data(self, limit: Optional[int] = None, **kwargs) -> List[Dict[str, Any]]:
        """
        Recupera i dati di stampa dal file allprintdatafile_ita.xml
        """
        cache_key = "mkto_print_data"
        
        if not kwargs.get('force_refresh') and CACHE_AVAILABLE:
            try:
                cached_data = cache.get(cache_key)
                if cached_data:
                    self.logger.info("Usando cache per dati stampa MKTO")
                    return cached_data[:limit] if limit else cached_data
            except Exception:
                pass
        
        try:
            file_path = self._get_file_path('print_data')
            self.logger.info(f"Parsing dati stampa MKTO da: {file_path}")
            
            print_data = []
            count = 0
            
            for print_info in self._parse_xml_iterative(file_path, 'product'):
                standardized_print = self._standardize_mkto_print_data(print_info)
                if standardized_print.get('print_jobs'):  # Solo prodotti con stampa
                    print_data.append(standardized_print)
                
                count += 1
                if count % 200 == 0:
                    self.logger.info(f"Processati {count} record stampa...")
                
                if limit and count >= limit:
                    break
            
            # Cache per 6 ore (dati stampa cambiano raramente)
            if CACHE_AVAILABLE:
                try:
                    cache.set(cache_key, print_data, 6 * 3600)
                except Exception:
                    pass
            
            self.logger.info(f"Recuperati {len(print_data)} record dati stampa da MKTO XML")
            return print_data
            
        except Exception as e:
            self.logger.error(f"Errore recupero dati stampa MKTO: {e}")
            raise APIError(f"Errore recupero dati stampa: {e}")
    
    def get_print_prices(self, **kwargs) -> List[Dict[str, Any]]:
        """
        Recupera i prezzi di stampa dal file PrintPrices_ita.xml
        """
        cache_key = "mkto_print_prices"
        
        if not kwargs.get('force_refresh') and CACHE_AVAILABLE:
            try:
                cached_data = cache.get(cache_key)
                if cached_data:
                    self.logger.info("Usando cache per prezzi stampa MKTO")
                    return cached_data
            except Exception:
                pass
        
        try:
            file_path = self._get_file_path('print_prices')
            self.logger.info(f"Parsing prezzi stampa MKTO da: {file_path}")
            
            # Per i prezzi stampa usiamo il parsing tradizionale (file più piccolo)
            tree = ET.parse(file_path)
            root = tree.getroot()
            
            print_prices = []
            
            # Cerca il tag printjobs
            printjobs_elem = root.find('printjobs')
            if printjobs_elem is not None:
                for printjob_elem in printjobs_elem.findall('printjob'):
                    price_data = self._xml_element_to_dict(printjob_elem)
                    standardized_price = self._standardize_mkto_print_prices(price_data)
                    print_prices.append(standardized_price)
            
            # Cache per 12 ore
            if CACHE_AVAILABLE:
                try:
                    cache.set(cache_key, print_prices, 12 * 3600)
                except Exception:
                    pass
            
            self.logger.info(f"Recuperati {len(print_prices)} prezzi stampa da MKTO XML")
            return print_prices
            
        except Exception as e:
            self.logger.error(f"Errore recupero prezzi stampa MKTO: {e}")
            raise APIError(f"Errore recupero prezzi stampa: {e}")
    
    def _standardize_mkto_product(self, raw_data: Dict[str, Any]) -> Dict[str, Any]:
        """Standardizza i dati prodotto MKTO"""
        # Estrae immagini
        images = []
        if raw_data.get('imagemain'):
            images.append(raw_data['imagemain'])
        
        # Estrae immagini aggiuntive
        if 'images' in raw_data and isinstance(raw_data['images'], dict):
            image_list = raw_data['images'].get('image', [])
            if not isinstance(image_list, list):
                image_list = [image_list]
            
            for img in image_list:
                if isinstance(img, dict) and img.get('imagemax'):
                    if img['imagemax'] not in images:
                        images.append(img['imagemax'])
        
        # Estrae categorie
        categories = []
        if 'categories' in raw_data:
            cat_data = raw_data['categories']
            for i in range(1, 6):
                name_key = f'category_name_{i}'
                if cat_data.get(name_key):
                    categories.append(cat_data[name_key])
        
        # Estrae varianti
        variants = []
        if 'variants' in raw_data and isinstance(raw_data['variants'], dict):
            variant_list = raw_data['variants'].get('variant', [])
            if not isinstance(variant_list, list):
                variant_list = [variant_list]
            
            for variant in variant_list:
                if isinstance(variant, dict):
                    # Genera SKU unico per la variante
                    supplier_ref = raw_data.get('ref', '')
                    color = variant.get('colour', '')
                    size = variant.get('size', 'ST')  # Size/Taglia
                    refct = variant.get('refct', '')
                    
                    # Usa refct se disponibile, altrimenti genera SKU
                    if refct and refct.strip():
                        variant_sku = refct.strip()
                    else:
                        # Genera SKU basato su ref + colore + taglia
                        sku_parts = [f"MAK_{supplier_ref}"]
                        if color:
                            sku_parts.append(color.replace('/', '').replace(' ', ''))
                        if size and size != 'S/T':
                            sku_parts.append(size.replace('/', '').replace(' ', ''))
                        variant_sku = '_'.join(sku_parts)
                    
                    variants.append({
                        'supplier_variant_ref': refct or f"{supplier_ref}_{color}_{size}",
                        'sku': variant_sku,
                        'color': color,
                        'size': size,
                        'gtin': variant.get('matnr', ''),
                        'image': variant.get('image500px', '')
                    })
        
        return {
            'supplier_ref': raw_data.get('ref', ''),
            'name': raw_data.get('name', ''),
            'type': raw_data.get('type', ''),
            'description': raw_data.get('extendedinfo', ''),
            'short_description': raw_data.get('otherinfo', ''),
            'composition': raw_data.get('composition', ''),
            'brand': raw_data.get('brand', ''),
            'weight': self._safe_float(raw_data.get('item_weight')),
            'main_image': images[0] if images else '',
            'images': images,
            'categories': categories,
            'variants': variants,
            'is_printable': bool(raw_data.get('printcode')),
            'print_code': raw_data.get('printcode', ''),
            'keywords': raw_data.get('keywords', ''),
            'dimensions': self._format_dimensions(raw_data),
            'raw_data': raw_data
        }
    
    def _standardize_mkto_stock(self, raw_data: Dict[str, Any]) -> Dict[str, Any]:
        """Standardizza i dati stock MKTO"""
        # Estrae info stock
        stock_info = {}
        if 'infostocks' in raw_data:
            infostocks = raw_data['infostocks']
            if isinstance(infostocks, dict) and 'infostock' in infostocks:
                stock_data = infostocks['infostock']
                if isinstance(stock_data, list):
                    stock_info = stock_data[0] if stock_data else {}
                else:
                    stock_info = stock_data
        
        return {
            'supplier_ref': raw_data.get('ref', ''),
            'sku': raw_data.get('reftc', ''),
            'color': raw_data.get('colour', ''),
            'size': raw_data.get('size', ''),
            'stock_quantity': self._safe_int(stock_info.get('stock', 0)),
            'availability_status': stock_info.get('available', 'unknown'),
            'raw_data': raw_data
        }
    
    def _standardize_mkto_prices(self, raw_data: Dict[str, Any]) -> Dict[str, Any]:
        """Standardizza i dati prezzo MKTO"""
        price_ranges = []
        
        # Estrae i 4 scaglioni di prezzo
        for i in range(1, 5):
            section_key = f'section{i}'
            price_key = f'price{i}'
            
            if raw_data.get(price_key):
                min_qty = raw_data.get(section_key, 1)
                if isinstance(min_qty, str) and min_qty.startswith('-'):
                    min_qty = 1  # Primo scaglione
                
                price_ranges.append({
                    'min_quantity': self._safe_int(min_qty),
                    'price': self._safe_float(raw_data.get(price_key, 0))
                })
        
        return {
            'supplier_ref': raw_data.get('ref', ''),
            'name': raw_data.get('name', ''),
            'price_ranges': price_ranges,
            'raw_data': raw_data
        }
    
    def _standardize_mkto_print_data(self, raw_data: Dict[str, Any]) -> Dict[str, Any]:
        """Standardizza i dati stampa MKTO"""
        print_jobs = []
        
        if 'printjobs' in raw_data:
            printjobs = raw_data['printjobs']
            if isinstance(printjobs, dict) and 'printjob' in printjobs:
                jobs = printjobs['printjob']
                if not isinstance(jobs, list):
                    jobs = [jobs]
                
                for job in jobs:
                    if isinstance(job, dict):
                        areas = []
                        if 'areas' in job and isinstance(job['areas'], dict):
                            area_list = job['areas'].get('area', [])
                            if not isinstance(area_list, list):
                                area_list = [area_list]
                            
                            for area in area_list:
                                if isinstance(area, dict):
                                    areas.append({
                                        'code': area.get('areacode', ''),
                                        'name': area.get('areaname', ''),
                                        'width': self._safe_float(area.get('areawidth')),
                                        'height': self._safe_float(area.get('areahight')),  # Nota: typo nel XML
                                        'max_colors': self._safe_int(area.get('maxcolour', 1)),
                                        'image': area.get('areaimg', '')
                                    })
                        
                        print_jobs.append({
                            'technique_code': job.get('teccode', ''),
                            'technique_name': job.get('tecname', ''),
                            'color_layers': self._safe_int(job.get('colour_layers', 1)),
                            'max_colors': self._safe_int(job.get('colour_options', 1)),
                            'areas': areas
                        })
        
        return {
            'supplier_ref': raw_data.get('ref', ''),
            'name': raw_data.get('name', ''),
            'print_jobs': print_jobs,
            'raw_data': raw_data
        }
    
    def _standardize_mkto_print_prices(self, raw_data: Dict[str, Any]) -> Dict[str, Any]:
        """Standardizza i prezzi stampa MKTO"""
        price_ranges = []
        
        # Estrae i vari scaglioni di prezzo
        for i in range(1, 8):  # Fino a 7 scaglioni
            amount_key = f'amountunder{i}'
            price_key = f'price{i}'
            add_color_key = f'priceaditionalcol{i}'
            
            if raw_data.get(price_key):
                price_ranges.append({
                    'max_quantity': self._safe_int(raw_data.get(amount_key, 0)),
                    'price': self._safe_float(raw_data.get(price_key, 0)),
                    'additional_color_price': self._safe_float(raw_data.get(add_color_key, 0))
                })
        
        return {
            'technique_code': raw_data.get('teccode', ''),
            'code': raw_data.get('code', ''),
            'name': raw_data.get('name', ''),
            'setup_cost': self._safe_float(raw_data.get('cliche', 0)),
            'setup_repeat_cost': self._safe_float(raw_data.get('clicherep', 0)),
            'min_job_cost': self._safe_float(raw_data.get('minjob', 0)),
            'price_ranges': price_ranges,
            'terms': raw_data.get('terms', ''),
            'raw_data': raw_data
        }
    
    def _format_dimensions(self, raw_data: Dict[str, Any]) -> str:
        """Formatta le dimensioni del prodotto"""
        dims = []
        if raw_data.get('item_long'):
            dims.append(str(raw_data['item_long']))
        if raw_data.get('item_width'):
            dims.append(str(raw_data['item_width']))
        if raw_data.get('item_hight'):  # Nota: typo nel XML
            dims.append(str(raw_data['item_hight']))
        
        return ' x '.join(dims) + ' cm' if dims else ''
    
    def _safe_int(self, value) -> int:
        """Converte in int in modo sicuro"""
        try:
            return int(float(str(value))) if value else 0
        except (ValueError, TypeError):
            return 0
    
    def _safe_float(self, value) -> Optional[float]:
        """Converte in float in modo sicuro"""
        try:
            return float(str(value).replace(',', '.')) if value else None
        except (ValueError, TypeError):
            return None
    
    def get_file_info(self) -> Dict[str, Dict[str, Any]]:
        """Restituisce informazioni sui file XML"""
        file_info = {}
        
        for file_type, filename in self.files.items():
            file_path = os.path.join(self.xml_path, filename)
            
            info = {
                'filename': filename,
                'path': file_path,
                'exists': os.path.exists(file_path),
                'size': 0,
                'last_modified': None
            }
            
            if info['exists']:
                stat = os.stat(file_path)
                info['size'] = stat.st_size
                info['last_modified'] = stat.st_mtime
            
            file_info[file_type] = info
        
        return file_info
    
    def clear_cache(self):
        """Pulisce la cache di MKTO"""
        cache_keys = [
            'mkto_products',
            'mkto_stock', 
            'mkto_prices',
            'mkto_print_data',
            'mkto_print_prices'
        ]
        
        if CACHE_AVAILABLE:
            try:
                for key in cache_keys:
                    cache.delete(key)
            except Exception:
                pass
        
        self.logger.info("Cache MKTO pulita")
