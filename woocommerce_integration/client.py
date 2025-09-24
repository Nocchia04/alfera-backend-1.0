"""
Client WooCommerce per sincronizzazione prodotti
"""
import logging
from typing import Dict, List, Optional, Any
from woocommerce import API
from django.conf import settings
from .image_handler import image_handler
from django.core.cache import cache


logger = logging.getLogger('sync')


class WooCommerceClient:
    """Client per l'integrazione con WooCommerce"""
    
    def __init__(self):
        self.wcapi = API(
            url=settings.WOOCOMMERCE_URL,
            consumer_key=settings.WOOCOMMERCE_KEY,
            consumer_secret=settings.WOOCOMMERCE_SECRET,
            wp_api=True,
            version="wc/v3",
            timeout=30
        )
        self.logger = logger
    
    def test_connection(self) -> bool:
        """Testa la connessione con WooCommerce"""
        try:
            response = self.wcapi.get("products", params={"per_page": 1})
            return response.status_code == 200
        except Exception as e:
            self.logger.error(f"Test connessione WooCommerce fallito: {e}")
            return False
    
    def get_product_by_sku(self, sku: str) -> Optional[Dict[str, Any]]:
        """Recupera un prodotto WooCommerce per SKU"""
        try:
            response = self.wcapi.get("products", params={"sku": sku})
            
            if response.status_code == 200:
                products = response.json()
                return products[0] if products else None
            else:
                self.logger.error(f"Errore recupero prodotto WooCommerce {sku}: {response.status_code}")
                return None
                
        except Exception as e:
            self.logger.error(f"Errore recupero prodotto WooCommerce {sku}: {e}")
            return None
    
    def create_product_draft(self, product_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Crea un prodotto in bozza su WooCommerce"""
        try:
            # Prepara i dati per WooCommerce
            woo_data = self._prepare_product_data(product_data)
            woo_data['status'] = 'draft'  # Sempre in bozza
            
            response = self.wcapi.post("products", woo_data)
            
            if response.status_code == 201:
                created_product = response.json()
                self.logger.info(f"Prodotto creato in bozza: {created_product['name']} (ID: {created_product['id']})")
                return created_product
            else:
                self.logger.error(f"Errore creazione prodotto: {response.status_code} - {response.text}")
                return None
                
        except Exception as e:
            self.logger.error(f"Errore creazione prodotto WooCommerce: {e}")
            return None
    
    def update_product_draft(self, woo_id: int, product_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Aggiorna un prodotto in bozza su WooCommerce"""
        try:
            # Prepara i dati per WooCommerce
            woo_data = self._prepare_product_data(product_data)
            woo_data['status'] = 'draft'  # Mantieni in bozza
            
            response = self.wcapi.put(f"products/{woo_id}", woo_data)
            
            if response.status_code == 200:
                updated_product = response.json()
                self.logger.info(f"Prodotto aggiornato: {updated_product['name']} (ID: {woo_id})")
                return updated_product
            else:
                self.logger.error(f"Errore aggiornamento prodotto {woo_id}: {response.status_code} - {response.text}")
                return None
                
        except Exception as e:
            self.logger.error(f"Errore aggiornamento prodotto WooCommerce {woo_id}: {e}")
            return None
    
    def create_or_update_product(self, product_data: Dict[str, Any], existing_woo_id: Optional[int] = None) -> Optional[Dict[str, Any]]:
        """Crea o aggiorna un prodotto su WooCommerce"""
        if existing_woo_id:
            return self.update_product_draft(existing_woo_id, product_data)
        else:
            # Verifica se esiste già per SKU
            existing_product = self.get_product_by_sku(product_data.get('sku', ''))
            if existing_product:
                return self.update_product_draft(existing_product['id'], product_data)
            else:
                return self.create_product_draft(product_data)
    
    def create_category(self, category_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Crea una categoria su WooCommerce"""
        try:
            woo_category = {
                'name': category_data['name'],
                'slug': category_data.get('slug', ''),
                'parent': category_data.get('parent_id', 0)
            }
            
            response = self.wcapi.post("products/categories", woo_category)
            
            if response.status_code == 201:
                created_category = response.json()
                self.logger.info(f"Categoria creata: {created_category['name']} (ID: {created_category['id']})")
                return created_category
            else:
                self.logger.error(f"Errore creazione categoria: {response.status_code} - {response.text}")
                return None
                
        except Exception as e:
            self.logger.error(f"Errore creazione categoria WooCommerce: {e}")
            return None
    
    def get_categories(self) -> List[Dict[str, Any]]:
        """Recupera tutte le categorie WooCommerce"""
        try:
            all_categories = []
            page = 1
            per_page = 100
            
            while True:
                response = self.wcapi.get("products/categories", params={
                    "per_page": per_page,
                    "page": page
                })
                
                if response.status_code == 200:
                    categories = response.json()
                    if not categories:
                        break
                    
                    all_categories.extend(categories)
                    page += 1
                else:
                    self.logger.error(f"Errore recupero categorie: {response.status_code}")
                    break
            
            return all_categories
            
        except Exception as e:
            self.logger.error(f"Errore recupero categorie WooCommerce: {e}")
            return []
    
    def bulk_create_products(self, products_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Crea prodotti in blocco su WooCommerce"""
        try:
            # Prepara i dati per il batch
            batch_data = {
                'create': [self._prepare_product_data(product) for product in products_data]
            }
            
            # Imposta tutti come bozza
            for product in batch_data['create']:
                product['status'] = 'draft'
            
            response = self.wcapi.post("products/batch", batch_data)
            
            if response.status_code == 200:
                result = response.json()
                created_count = len(result.get('create', []))
                self.logger.info(f"Creati {created_count} prodotti in blocco")
                
                return {
                    'success': True,
                    'created': created_count,
                    'products': result.get('create', []),
                    'errors': result.get('create', [])  # WooCommerce include gli errori qui
                }
            else:
                self.logger.error(f"Errore creazione blocco: {response.status_code} - {response.text}")
                return {'success': False, 'error': response.text}
                
        except Exception as e:
            self.logger.error(f"Errore creazione blocco WooCommerce: {e}")
            return {'success': False, 'error': str(e)}
    
    def _prepare_product_data(self, product_data: Dict[str, Any]) -> Dict[str, Any]:
        """Prepara i dati del prodotto per WooCommerce"""
        
        # Converti datetime in stringa se necessario
        def safe_string(value):
            if hasattr(value, 'isoformat'):
                return value.isoformat()
            return str(value) if value else ''
        
        woo_product = {
            'name': str(product_data.get('name', '')),
            'type': 'simple',  # Default, può essere 'variable' se ha varianti
            'sku': str(product_data.get('sku', '')),
            'description': str(product_data.get('description', '')),
            'short_description': str(product_data.get('short_description', '')),
            'status': 'draft',
            'catalog_visibility': 'visible',
            'manage_stock': True,
            'stock_quantity': int(product_data.get('stock_quantity', 0)),
            'stock_status': 'instock' if product_data.get('stock_quantity', 0) > 0 else 'outofstock',
            'meta_data': [
                {
                    'key': '_supplier_name',
                    'value': safe_string(product_data.get('supplier_name', ''))
                },
                {
                    'key': '_supplier_ref',
                    'value': safe_string(product_data.get('supplier_ref', ''))
                },
                {
                    'key': '_last_sync',
                    'value': safe_string(product_data.get('last_sync', ''))
                }
            ]
        }
        
        # 🆕 PREZZO AUTOMATICO - Usa base_price del prodotto se disponibile
        price_to_use = None
        
        # Priorità 1: Prezzo dal product_data (legacy)
        if product_data.get('price'):
            try:
                price_to_use = float(product_data['price'])
            except (ValueError, TypeError):
                pass
        
        # Priorità 2: base_price dal modello Product
        if not price_to_use and hasattr(product_data, 'base_price') and product_data.base_price:
            try:
                price_to_use = float(product_data.base_price)
            except (ValueError, TypeError):
                pass
        
        # Priorità 3: Primo prezzo dalla lista prezzi
        if not price_to_use and product_data.get('prices') and len(product_data['prices']) > 0:
            try:
                price_to_use = float(product_data['prices'][0].get('price', 0))
            except (ValueError, TypeError, IndexError):
                pass
        
        if price_to_use and price_to_use > 0:
            woo_product['regular_price'] = str(price_to_use)
        
        # Immagini - Processa con image handler
        if product_data.get('images'):
            try:
                processed_images = image_handler.process_product_images(product_data)
                if processed_images:
                    woo_product['images'] = []
                    for i, img_data in enumerate(processed_images):
                        woo_product['images'].append({
                            'src': str(img_data['src']),
                            'alt': str(img_data.get('alt', product_data.get('name', ''))),
                            'name': str(img_data.get('name', f'image_{i}')),
                            'position': i
                        })
                else:
                    logger.warning(f"Nessuna immagine processabile per {product_data.get('sku', 'unknown')}")
            except Exception as e:
                logger.error(f"Errore processing immagini: {e}")
                # Fallback: usa URL originali
                woo_product['images'] = []
                for i, image_url in enumerate(product_data['images']):
                    if image_url:
                        woo_product['images'].append({
                            'src': str(image_url),
                            'alt': str(product_data.get('name', '')),
                            'position': i
                        })
        
        # 🆕 CATEGORIE AUTOMATICHE
        categories_to_use = []
        
        # Priorità 1: Category ID dal modello Product
        if hasattr(product_data, 'category') and product_data.category and hasattr(product_data.category, 'woocommerce_id'):
            if product_data.category.woocommerce_id:
                try:
                    categories_to_use.append({'id': int(product_data.category.woocommerce_id)})
                except (ValueError, TypeError):
                    pass
        
        # Priorità 2: Categories dal product_data (legacy)
        if not categories_to_use and product_data.get('categories'):
            for cat_id in product_data['categories']:
                try:
                    categories_to_use.append({'id': int(cat_id)})
                except (ValueError, TypeError):
                    pass
        
        # Priorità 3: Categoria di default se nessuna assegnata
        if not categories_to_use:
            # Usa categoria "Uncategorized" (ID 1 di default WooCommerce)
            categories_to_use.append({'id': 1})
        
        if categories_to_use:
            woo_product['categories'] = categories_to_use
        
        # Attributi (per varianti future)
        if product_data.get('attributes'):
            woo_product['attributes'] = []
            for attr_name, attr_values in product_data['attributes'].items():
                if attr_values:  # Solo se ha valori
                    values = attr_values if isinstance(attr_values, list) else [attr_values]
                    woo_product['attributes'].append({
                        'name': str(attr_name),
                        'options': [str(v) for v in values if v],
                        'visible': True,
                        'variation': True
                    })
        
        # Dimensioni e peso
        dimensions = {}
        for dim_key in ['length', 'width', 'height']:
            if product_data.get(dim_key):
                try:
                    dimensions[dim_key] = str(float(product_data[dim_key]))
                except (ValueError, TypeError):
                    pass
        
        if dimensions:
            woo_product['dimensions'] = dimensions
        
        if product_data.get('weight'):
            try:
                woo_product['weight'] = str(float(product_data['weight']))
            except (ValueError, TypeError):
                pass
        
        return woo_product
    
    def get_category_by_name(self, name, parent_id=0):
        """Cerca una categoria per nome"""
        try:
            params = {
                'search': name,
                'parent': parent_id,
                'per_page': 10
            }
            
            response = self.wcapi.get('products/categories', params=params)
            
            if response.status_code == 200:
                categories = response.json()
                for category in categories:
                    if category['name'].lower() == name.lower():
                        return category
            
            return None
            
        except Exception as e:
            logger.error(f"Errore ricerca categoria {name}: {e}")
            return None
    
    def create_category(self, category_data):
        """Crea una nuova categoria su WooCommerce"""
        try:
            response = self.wcapi.post('products/categories', category_data)
            
            if response.status_code == 201:
                category = response.json()
                logger.info(f"Categoria creata: {category['name']} (ID: {category['id']})")
                return category
            else:
                logger.error(f"Errore creazione categoria: {response.status_code} - {response.text}")
                return None
                
        except Exception as e:
            logger.error(f"Errore creazione categoria: {e}")
            return None
    
    def get_product_stats(self) -> Dict[str, int]:
        """Recupera statistiche sui prodotti WooCommerce"""
        try:
            # Conta prodotti per stato
            stats = {}
            
            for status in ['draft', 'pending', 'private', 'publish']:
                response = self.wcapi.get("products", params={
                    "status": status,
                    "per_page": 1
                })
                
                if response.status_code == 200:
                    # Il totale è nell'header X-WP-Total
                    total = int(response.headers.get('X-WP-Total', 0))
                    stats[status] = total
            
            return stats
            
        except Exception as e:
            self.logger.error(f"Errore recupero statistiche WooCommerce: {e}")
            return {}
    
    def clear_draft_products(self) -> int:
        """Elimina tutti i prodotti in bozza (ATTENZIONE: operazione pericolosa!)"""
        try:
            deleted_count = 0
            page = 1
            
            while True:
                response = self.wcapi.get("products", params={
                    "status": "draft",
                    "per_page": 100,
                    "page": page
                })
                
                if response.status_code == 200:
                    products = response.json()
                    if not products:
                        break
                    
                    # Elimina i prodotti
                    for product in products:
                        delete_response = self.wcapi.delete(f"products/{product['id']}", params={"force": True})
                        if delete_response.status_code == 200:
                            deleted_count += 1
                    
                    page += 1
                else:
                    break
            
            self.logger.info(f"Eliminati {deleted_count} prodotti in bozza")
            return deleted_count
            
        except Exception as e:
            self.logger.error(f"Errore eliminazione prodotti bozza: {e}")
            return 0
