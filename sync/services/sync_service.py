"""
Servizio principale per la sincronizzazione dei dati
"""
import logging
from typing import Dict, List, Optional, Any
from django.db import transaction
from django.utils import timezone
from django.core.cache import cache

from suppliers.models import Supplier, SyncLog
from suppliers.clients.factory import SupplierClientFactory
from products.models import Product, ProductVariant, Category, Stock, Price
from woocommerce_integration.client import WooCommerceClient
from sync.models import SyncTask, SyncError
from .data_mapper import DataMapper

logger = logging.getLogger('sync')


class SyncService:
    """Servizio principale per sincronizzazione"""
    
    def __init__(self):
        self.logger = logger
        self.data_mapper = DataMapper()
        self.woo_client = WooCommerceClient()
        
        # Statistiche sincronizzazione
        self.stats = {
            'products_processed': 0,
            'products_created': 0,
            'products_updated': 0,
            'products_errors': 0,
            'variants_processed': 0,
            'stock_updated': 0,
            'prices_updated': 0,
            'woo_synced': 0
        }
    
    def sync_all_suppliers(self, sync_to_woocommerce: bool = True) -> Dict[str, Any]:
        """Sincronizza tutti i fornitori attivi"""
        self.logger.info("Iniziando sincronizzazione completa di tutti i fornitori")
        
        results = {}
        total_stats = {key: 0 for key in self.stats.keys()}
        
        for supplier in Supplier.objects.filter(is_active=True):
            try:
                result = self.sync_supplier(supplier, sync_to_woocommerce=sync_to_woocommerce)
                results[supplier.name] = result
                
                # Accumula statistiche
                for key, value in result.get('stats', {}).items():
                    total_stats[key] = total_stats.get(key, 0) + value
                    
            except Exception as e:
                self.logger.error(f"Errore sincronizzazione fornitore {supplier.name}: {e}")
                results[supplier.name] = {'success': False, 'error': str(e)}
        
        self.logger.info(f"Sincronizzazione completa terminata. Statistiche: {total_stats}")
        
        return {
            'success': True,
            'suppliers': results,
            'total_stats': total_stats
        }
    
    def sync_supplier(self, supplier: Supplier, sync_to_woocommerce: bool = True) -> Dict[str, Any]:
        """Sincronizza un singolo fornitore"""
        self.logger.info(f"Iniziando sincronizzazione fornitore: {supplier.name}")
        
        # Reset statistiche
        self.stats = {key: 0 for key in self.stats.keys()}
        
        # Crea log sincronizzazione
        sync_log = SyncLog.objects.create(
            supplier=supplier,
            sync_type='FULL',
            status='RUNNING'
        )
        
        try:
            # Crea client fornitore
            client = SupplierClientFactory.create_client(supplier)
            
            # Sincronizza prodotti
            products_result = self._sync_products(client, supplier, sync_log)
            
            # Sincronizza stock
            stock_result = self._sync_stock(client, supplier, sync_log)
            
            # Sincronizza prezzi
            prices_result = self._sync_prices(client, supplier, sync_log)
            
            # Sincronizza con WooCommerce se richiesto
            if sync_to_woocommerce:
                woo_result = self._sync_to_woocommerce(supplier, sync_log)
            else:
                woo_result = {'synced': 0}
            
            # Aggiorna statistiche sync_log
            sync_log.products_processed = self.stats['products_processed']
            sync_log.products_created = self.stats['products_created']
            sync_log.products_updated = self.stats['products_updated']
            sync_log.products_errors = self.stats['products_errors']
            
            # Completa sincronizzazione
            sync_log.mark_completed('SUCCESS')
            
            result = {
                'success': True,
                'stats': self.stats.copy(),
                'products': products_result,
                'stock': stock_result,
                'prices': prices_result,
                'woocommerce': woo_result
            }
            
            self.logger.info(f"Sincronizzazione {supplier.name} completata con successo")
            return result
            
        except Exception as e:
            error_msg = f"Errore sincronizzazione {supplier.name}: {e}"
            self.logger.error(error_msg)
            
            # Registra errore
            SyncError.objects.create(
                sync_task=None,
                supplier=supplier,
                error_type='SYSTEM_ERROR',
                severity='HIGH',
                error_message=str(e),
                context_data={'stats': self.stats}
            )
            
            sync_log.mark_completed('ERROR', error_msg)
            
            return {
                'success': False,
                'error': error_msg,
                'stats': self.stats.copy()
            }
    
    def _sync_products(self, client, supplier: Supplier, sync_log: SyncLog) -> Dict[str, Any]:
        """Sincronizza i prodotti dal fornitore"""
        self.logger.info(f"Sincronizzando prodotti da {supplier.name}")
        
        try:
            # Recupera prodotti dal fornitore
            raw_products = client.get_products()
            
            created_count = 0
            updated_count = 0
            error_count = 0
            
            for raw_product in raw_products:
                try:
                    with transaction.atomic():
                        # Mappa i dati
                        mapped_data = self.data_mapper.map_product_data(raw_product, supplier)
                        
                        # Crea o aggiorna prodotto
                        product, created = self._create_or_update_product(mapped_data)
                        
                        if created:
                            created_count += 1
                            self.stats['products_created'] += 1
                        else:
                            updated_count += 1
                            self.stats['products_updated'] += 1
                        
                        # Gestisci varianti
                        self._sync_product_variants(product, mapped_data.get('variants', []))
                        
                        # 🆕 GESTIONE AUTOMATICA CATEGORIE E PREZZI
                        self._process_product_enhancements(product, mapped_data, supplier)
                        
                        self.stats['products_processed'] += 1
                        
                except Exception as e:
                    error_count += 1
                    self.stats['products_errors'] += 1
                    
                    # Log errore specifico
                    SyncError.objects.create(
                        supplier=supplier,
                        error_type='PARSING_ERROR',
                        severity='MEDIUM',
                        error_message=str(e),
                        object_type='product',
                        object_id=raw_product.get('supplier_ref', ''),
                        context_data=raw_product
                    )
                    
                    self.logger.error(f"Errore sincronizzazione prodotto {raw_product.get('supplier_ref', '')}: {e}")
            
            result = {
                'total': len(raw_products),
                'created': created_count,
                'updated': updated_count,
                'errors': error_count
            }
            
            self.logger.info(f"Prodotti sincronizzati: {result}")
            return result
            
        except Exception as e:
            self.logger.error(f"Errore sincronizzazione prodotti {supplier.name}: {e}")
            raise
    
    def _sync_stock(self, client, supplier: Supplier, sync_log: SyncLog) -> Dict[str, Any]:
        """Sincronizza i dati di stock"""
        self.logger.info(f"Sincronizzando stock da {supplier.name}")
        
        try:
            raw_stock = client.get_stock()
            updated_count = 0
            
            for stock_data in raw_stock:
                try:
                    mapped_stock = self.data_mapper.map_stock_data(stock_data, supplier)
                    
                    # Trova la variante corrispondente
                    variant = self._find_variant_by_sku(mapped_stock.get('sku'), supplier)
                    
                    if variant:
                        stock, created = Stock.objects.update_or_create(
                            variant=variant,
                            defaults={
                                'stock_quantity': mapped_stock.get('stock_quantity', 0),
                                'availability_status': mapped_stock.get('availability_status', 'unknown'),
                                'next_arrival_date': mapped_stock.get('next_arrival_date'),
                                'next_arrival_quantity': mapped_stock.get('next_arrival_quantity'),
                                'supplier_updated_at': timezone.now()
                            }
                        )
                        updated_count += 1
                        self.stats['stock_updated'] += 1
                    
                except Exception as e:
                    self.logger.error(f"Errore aggiornamento stock {stock_data}: {e}")
            
            result = {
                'total': len(raw_stock),
                'updated': updated_count
            }
            
            self.logger.info(f"Stock sincronizzato: {result}")
            return result
            
        except Exception as e:
            self.logger.error(f"Errore sincronizzazione stock {supplier.name}: {e}")
            return {'total': 0, 'updated': 0, 'error': str(e)}
    
    def _sync_prices(self, client, supplier: Supplier, sync_log: SyncLog) -> Dict[str, Any]:
        """Sincronizza i prezzi"""
        self.logger.info(f"Sincronizzando prezzi da {supplier.name}")
        
        try:
            raw_prices = client.get_prices()
            updated_count = 0
            
            for price_data in raw_prices:
                try:
                    mapped_prices = self.data_mapper.map_price_data(price_data, supplier)
                    
                    for mapped_price in mapped_prices:
                        # Trova la variante corrispondente
                        variant = self._find_variant_by_sku(mapped_price.get('sku'), supplier)
                        
                        if variant:
                            # Disattiva prezzi vecchi
                            Price.objects.filter(variant=variant).update(is_active=False)
                            
                            # Crea nuovo prezzo
                            Price.objects.create(
                                variant=variant,
                                price=mapped_price.get('price', 0),
                                currency=mapped_price.get('currency', 'EUR'),
                                min_quantity=mapped_price.get('min_quantity', 1),
                                max_quantity=mapped_price.get('max_quantity'),
                                valid_until=mapped_price.get('valid_until'),
                                is_active=True
                            )
                            updated_count += 1
                            self.stats['prices_updated'] += 1
                    
                except Exception as e:
                    self.logger.error(f"Errore aggiornamento prezzo {price_data}: {e}")
            
            result = {
                'total': len(raw_prices),
                'updated': updated_count
            }
            
            self.logger.info(f"Prezzi sincronizzati: {result}")
            return result
            
        except Exception as e:
            self.logger.error(f"Errore sincronizzazione prezzi {supplier.name}: {e}")
            return {'total': 0, 'updated': 0, 'error': str(e)}
    
    def _sync_to_woocommerce(self, supplier: Supplier, sync_log: SyncLog) -> Dict[str, Any]:
        """Sincronizza prodotti su WooCommerce"""
        self.logger.info(f"Sincronizzando prodotti {supplier.name} su WooCommerce")
        
        try:
            # Recupera prodotti da sincronizzare
            products = Product.objects.filter(
                supplier=supplier,
                is_active=True
            ).select_related('category').prefetch_related('variants', 'variants__stock', 'variants__prices')
            
            synced_count = 0
            batch_size = 50  # Sincronizza in batch per performance
            
            for i in range(0, products.count(), batch_size):
                batch_products = products[i:i+batch_size]
                woo_products_data = []
                
                for product in batch_products:
                    try:
                        # Prepara dati per WooCommerce
                        woo_data = self._prepare_woocommerce_product(product)
                        woo_products_data.append(woo_data)
                        
                    except Exception as e:
                        self.logger.error(f"Errore preparazione prodotto WooCommerce {product.sku}: {e}")
                
                # Sincronizzazione batch
                if woo_products_data:
                    try:
                        if len(woo_products_data) == 1:
                            # Singolo prodotto
                            result = self.woo_client.create_or_update_product(
                                woo_products_data[0], 
                                product.woocommerce_id
                            )
                            if result:
                                product.woocommerce_id = result['id']
                                product.woocommerce_status = 'draft'
                                product.last_woo_sync = timezone.now()
                                product.save()
                                synced_count += 1
                        else:
                            # Batch
                            result = self.woo_client.bulk_create_products(woo_products_data)
                            if result.get('success'):
                                synced_count += result.get('created', 0)
                                
                                # Aggiorna ID WooCommerce sui prodotti
                                for i, woo_product in enumerate(result.get('products', [])):
                                    if i < len(batch_products):
                                        batch_products[i].woocommerce_id = woo_product['id']
                                        batch_products[i].woocommerce_status = 'draft'
                                        batch_products[i].last_woo_sync = timezone.now()
                                        batch_products[i].save()
                        
                    except Exception as e:
                        self.logger.error(f"Errore sincronizzazione batch WooCommerce: {e}")
            
            self.stats['woo_synced'] = synced_count
            
            result = {
                'total': products.count(),
                'synced': synced_count
            }
            
            self.logger.info(f"WooCommerce sincronizzato: {result}")
            return result
            
        except Exception as e:
            self.logger.error(f"Errore sincronizzazione WooCommerce {supplier.name}: {e}")
            return {'total': 0, 'synced': 0, 'error': str(e)}
    
    def _create_or_update_product(self, mapped_data: Dict[str, Any]) -> tuple:
        """Crea o aggiorna un prodotto"""
        supplier = mapped_data['supplier']
        supplier_ref = mapped_data['supplier_ref']
        
        # Cerca prodotto esistente
        product, created = Product.objects.update_or_create(
            supplier=supplier,
            supplier_ref=supplier_ref,
            defaults={
                'sku': mapped_data.get('sku', ''),
                'name': mapped_data.get('name', ''),
                'description': mapped_data.get('description', ''),
                'short_description': mapped_data.get('short_description', ''),
                'brand': mapped_data.get('brand', ''),
                'material': mapped_data.get('material', ''),
                'dimensions': mapped_data.get('dimensions', ''),
                'weight': mapped_data.get('weight'),
                'main_image': mapped_data.get('main_image', ''),
                'images': mapped_data.get('images', []),
                'is_printable': mapped_data.get('is_printable', False),
                'print_areas': mapped_data.get('print_areas', []),
                'supplier_updated_at': timezone.now()
            }
        )
        
        return product, created
    
    def _sync_product_variants(self, product: Product, variants_data: List[Dict[str, Any]]):
        """Sincronizza le varianti del prodotto"""
        for variant_data in variants_data:
            try:
                # Verifica che SKU non sia vuoto
                sku = variant_data.get('sku', '').strip()
                supplier_variant_ref = variant_data.get('supplier_variant_ref', '').strip()
                
                if not sku:
                    # Genera SKU se mancante
                    sku = f"MAK_{product.supplier_ref}_{variant_data.get('color', 'NOCOLOR')}_{variant_data.get('size', 'NOSIZE')}"
                    sku = sku.replace('/', '').replace(' ', '_').replace('__', '_')
                
                if not supplier_variant_ref:
                    supplier_variant_ref = f"{product.supplier_ref}_{variant_data.get('color', '')}_{variant_data.get('size', '')}"
                
                # Verifica se SKU già esiste per altro prodotto
                existing_variant = ProductVariant.objects.filter(sku=sku).exclude(product=product).first()
                if existing_variant:
                    # Aggiungi suffisso per rendere unico
                    sku = f"{sku}_{product.id}"
                
                variant, created = ProductVariant.objects.update_or_create(
                    product=product,
                    supplier_variant_ref=supplier_variant_ref,
                    defaults={
                        'sku': sku,
                        'color': variant_data.get('color', ''),
                        'color_code': variant_data.get('color_code', ''),
                        'size': variant_data.get('size', ''),
                        'gtin': variant_data.get('gtin', ''),
                        'image': variant_data.get('image', '')
                    }
                )
                
                if created:
                    self.stats['variants_processed'] += 1
                    
            except Exception as e:
                self.logger.error(f"Errore creazione variante {variant_data}: {e}")
                # Registra errore dettagliato
                SyncError.objects.create(
                    supplier=product.supplier,
                    error_type='VALIDATION_ERROR',
                    severity='MEDIUM',
                    error_message=f"Errore variante: {str(e)}",
                    object_type='variant',
                    object_id=variant_data.get('sku', 'unknown'),
                    context_data=variant_data
                )
    
    def _find_variant_by_sku(self, sku: str, supplier: Supplier) -> Optional[ProductVariant]:
        """Trova una variante per SKU"""
        try:
            return ProductVariant.objects.select_related('product').get(
                sku=sku,
                product__supplier=supplier
            )
        except ProductVariant.DoesNotExist:
            return None
    
    def _prepare_woocommerce_product(self, product: Product) -> Dict[str, Any]:
        """Prepara i dati del prodotto per WooCommerce"""
        # Calcola stock totale
        total_stock = sum(variant.current_stock for variant in product.variants.all())
        
        # Prendi il prezzo più basso
        min_price = None
        for variant in product.variants.all():
            price = variant.current_price
            if price and (min_price is None or price < min_price):
                min_price = price
        
        # 🆕 USA PREZZO BASE SE DISPONIBILE
        price_to_use = min_price
        if not price_to_use and product.base_price:
            price_to_use = float(product.base_price)
        
        # Prepara dati base
        woo_data = self.data_mapper.prepare_woocommerce_data({
            'name': product.name,
            'sku': product.sku,
            'description': product.description,
            'short_description': product.short_description,
            'images': product.images,
            'supplier': product.supplier,
            'supplier_ref': product.supplier_ref,
            'stock_quantity': total_stock,
            'price': price_to_use,
            'base_price': product.base_price,  # 🆕 Passa base_price
            'currency': product.currency,     # 🆕 Passa currency
            'category': product.category,     # 🆕 Passa categoria
            'variants': [
                {
                    'color': v.color,
                    'size': v.size
                } for v in product.variants.all()
            ],
            'weight': product.weight,
            'dimensions': product.dimensions,
            'updated_at': product.updated_at.isoformat() if product.updated_at else ''
        })
        
        # Aggiungi categoria WooCommerce
        if product.category and product.category.woocommerce_id:
            woo_data['categories'] = [product.category.woocommerce_id]
        
        return woo_data
    
    def clear_supplier_cache(self, supplier: Supplier):
        """Pulisce la cache del fornitore"""
        try:
            client = SupplierClientFactory.create_client(supplier)
            client.clear_cache()
            self.logger.info(f"Cache pulita per {supplier.name}")
        except Exception as e:
            self.logger.error(f"Errore pulizia cache {supplier.name}: {e}")
    
    def get_sync_stats(self) -> Dict[str, Any]:
        """Restituisce statistiche delle sincronizzazioni"""
        return {
            'total_products': Product.objects.count(),
            'products_by_supplier': {
                supplier.name: supplier.products.count()
                for supplier in Supplier.objects.filter(is_active=True)
            },
            'recent_syncs': list(
                SyncLog.objects.select_related('supplier')
                .order_by('-started_at')[:10]
                .values(
                    'supplier__name', 'sync_type', 'status',
                    'started_at', 'completed_at',
                    'products_processed', 'products_created', 'products_updated'
                )
            ),
            'sync_errors': SyncError.objects.filter(is_resolved=False).count()
        }

    def _process_product_enhancements(self, product: Product, mapped_data: Dict[str, Any], supplier: Supplier):
        """🆕 Gestisce automaticamente categorie, prezzi e miglioramenti prodotto"""
        try:
            # 1. ASSEGNAZIONE CATEGORIA AUTOMATICA
            self._assign_product_category(product, mapped_data, supplier)
            
            # 2. ASSEGNAZIONE PREZZO PRINCIPALE
            self._assign_main_price(product, mapped_data.get('prices', []))
            
            # 3. SINCRONIZZAZIONE STOCK
            stock_data = mapped_data.get('stock', {})
            if stock_data:
                self._sync_product_stock(product, stock_data)
            
            # 4. SINCRONIZZAZIONE PREZZI DETTAGLIATI
            prices_data = mapped_data.get('prices', [])
            if prices_data:
                self._sync_product_prices(product, prices_data)
                
        except Exception as e:
            self.logger.error(f"Errore process enhancements prodotto {product.sku}: {e}")
    
    def _assign_product_category(self, product: Product, mapped_data: Dict[str, Any], supplier: Supplier):
        """🆕 Assegna categoria automaticamente al prodotto"""
        try:
            # Strategia 1: Usa category_path se disponibile
            if mapped_data.get('category_path'):
                category = self.data_mapper.create_or_get_category(
                    mapped_data['category_path'], supplier
                )
                if category:
                    product.category = category
                    product.save()
                    return
            
            # Strategia 2: Usa categories list (per BIC/MKTO)
            if mapped_data.get('categories') and len(mapped_data['categories']) > 0:
                category_name = mapped_data['categories'][0]  # Prima categoria
                category = self._get_or_create_simple_category(category_name, supplier)
                if category:
                    product.category = category
                    product.save()
                    return
            
            # Strategia 3: Categoria di default per fornitore
            default_category = self._get_default_category(supplier)
            if default_category:
                product.category = default_category
                product.save()
                
        except Exception as e:
            self.logger.error(f"Errore assegnazione categoria prodotto {product.sku}: {e}")
    
    def _assign_main_price(self, product: Product, prices_data: List[Dict[str, Any]]):
        """🆕 Assegna prezzo principale al prodotto"""
        try:
            if not prices_data:
                return
            
            # Prendi il primo prezzo (solitamente per quantità minima)
            main_price_data = prices_data[0]
            main_price = main_price_data.get('price', 0)
            
            if main_price > 0:
                # Aggiorna il prezzo principale del prodotto
                product.base_price = float(main_price)
                product.currency = main_price_data.get('currency', 'EUR')
                product.save()
                
                self.logger.info(f"Prezzo assegnato a {product.sku}: {main_price} {product.currency}")
                
        except Exception as e:
            self.logger.error(f"Errore assegnazione prezzo prodotto {product.sku}: {e}")
    
    def _get_or_create_simple_category(self, category_name: str, supplier: Supplier):
        """🆕 Crea o recupera categoria semplice"""
        try:
            from products.models import Category
            from django.utils.text import slugify
            
            # Pulisci nome categoria
            clean_name = str(category_name).strip()
            if not clean_name:
                return None
            
            # Genera slug
            slug = slugify(clean_name)[:50]
            
            # Cerca categoria esistente
            category = Category.objects.filter(name=clean_name).first()
            if category:
                return category
            
            # Crea nuova categoria
            category = Category.objects.create(
                name=clean_name,
                slug=slug,
                parent=None,
                mkto_mapping=clean_name if supplier.supplier_type == 'MAKITO' else ''
            )
            
            self.logger.info(f"Categoria creata: {clean_name}")
            return category
            
        except Exception as e:
            self.logger.error(f"Errore creazione categoria {category_name}: {e}")
            return None
    
    def _get_default_category(self, supplier: Supplier):
        """🆕 Recupera categoria di default per fornitore"""
        try:
            from products.models import Category
            from django.utils.text import slugify
            
            # Categorie default per fornitore
            default_names = {
                'MKTO': 'Prodotti MKTO',
                'BIC': 'Prodotti BIC',
                'MIDOCEAN': 'Prodotti Midocean'
            }
            
            default_name = default_names.get(supplier.supplier_type, f'Prodotti {supplier.name}')
            
            # Cerca o crea categoria default
            category, created = Category.objects.get_or_create(
                name=default_name,
                defaults={
                    'slug': slugify(default_name)[:50],
                    'parent': None
                }
            )
            
            if created:
                self.logger.info(f"Categoria default creata: {default_name}")
            
            return category
            
        except Exception as e:
            self.logger.error(f"Errore categoria default per {supplier.name}: {e}")
            return None
