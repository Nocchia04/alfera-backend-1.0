"""
Comando Django per sincronizzazione fornitori
"""
import time
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from suppliers.models import Supplier
from sync.services.sync_service import SyncService
from woocommerce_integration.client import WooCommerceClient


class Command(BaseCommand):
    help = 'Sincronizza prodotti dai fornitori a WooCommerce'
    
    def add_arguments(self, parser):
        # Argomenti posizionali
        parser.add_argument(
            '--supplier',
            type=str,
            help='Nome o codice del fornitore specifico da sincronizzare'
        )
        
        parser.add_argument(
            '--type',
            choices=['products', 'stock', 'prices', 'all'],
            default='all',
            help='Tipo di sincronizzazione (default: all)'
        )
        
        parser.add_argument(
            '--no-woocommerce',
            action='store_true',
            help='Non sincronizzare con WooCommerce'
        )
        
        parser.add_argument(
            '--test-connections',
            action='store_true',
            help='Testa solo le connessioni senza sincronizzare'
        )
        
        parser.add_argument(
            '--clear-cache',
            action='store_true',
            help='Pulisce la cache prima della sincronizzazione'
        )
        
        parser.add_argument(
            '--stats',
            action='store_true',
            help='Mostra solo le statistiche'
        )
        
        parser.add_argument(
            '--batch-size',
            type=int,
            default=100,
            help='Dimensione batch per sincronizzazione (default: 100)'
        )
        
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Simula la sincronizzazione senza modificare i dati'
        )
        
        parser.add_argument(
            '--force',
            action='store_true',
            help='Forza la sincronizzazione ignorando la cache'
        )
    
    def handle(self, *args, **options):
        """Gestisce l'esecuzione del comando"""
        self.sync_service = SyncService()
        
        # Stile output
        self.style.SUCCESS = self.style.SUCCESS
        self.style.WARNING = self.style.WARNING
        self.style.ERROR = self.style.ERROR
        
        try:
            if options['test_connections']:
                self.test_connections()
            elif options['stats']:
                self.show_stats()
            elif options['clear_cache']:
                self.clear_cache(options['supplier'])
            else:
                self.run_sync(options)
                
        except KeyboardInterrupt:
            self.stdout.write(self.style.WARNING('\nSincronizzazione interrotta dall\'utente'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Errore: {e}'))
            raise CommandError(f'Sincronizzazione fallita: {e}')
    
    def run_sync(self, options):
        """Esegue la sincronizzazione"""
        start_time = time.time()
        
        self.stdout.write(self.style.SUCCESS('=== SINCRONIZZAZIONE FORNITORI ==='))
        self.stdout.write(f'Inizio: {timezone.now().strftime("%Y-%m-%d %H:%M:%S")}')
        
        if options['dry_run']:
            self.stdout.write(self.style.WARNING('MODALITÀ DRY-RUN - Nessuna modifica sarà effettuata'))
        
        # Determina fornitori da sincronizzare
        if options['supplier']:
            suppliers = self.get_suppliers_by_name_or_code(options['supplier'])
        else:
            suppliers = Supplier.objects.filter(is_active=True)
        
        if not suppliers:
            raise CommandError('Nessun fornitore trovato o attivo')
        
        self.stdout.write(f'Fornitori da sincronizzare: {", ".join(s.name for s in suppliers)}')
        
        # Opzioni sincronizzazione
        sync_to_woocommerce = not options['no_woocommerce']
        if not sync_to_woocommerce:
            self.stdout.write(self.style.WARNING('Sincronizzazione WooCommerce disabilitata'))
        
        # Pulisci cache se richiesto
        if options['clear_cache']:
            self.stdout.write('Pulizia cache...')
            for supplier in suppliers:
                self.sync_service.clear_supplier_cache(supplier)
        
        # Esegui sincronizzazione
        total_stats = {
            'products_processed': 0,
            'products_created': 0,
            'products_updated': 0,
            'products_errors': 0,
            'woo_synced': 0
        }
        
        for i, supplier in enumerate(suppliers, 1):
            self.stdout.write(f'\n[{i}/{len(suppliers)}] Sincronizzando {supplier.name}...')
            
            if options['dry_run']:
                self.stdout.write(self.style.WARNING(f'  DRY-RUN: Simulazione sincronizzazione {supplier.name}'))
                continue
            
            try:
                result = self.sync_service.sync_supplier(
                    supplier, 
                    sync_to_woocommerce=sync_to_woocommerce
                )
                
                if result['success']:
                    stats = result['stats']
                    self.stdout.write(self.style.SUCCESS(f'  ✓ Completato'))
                    self.stdout.write(f'    Prodotti: {stats["products_processed"]} processati, '
                                    f'{stats["products_created"]} creati, '
                                    f'{stats["products_updated"]} aggiornati')
                    
                    if sync_to_woocommerce:
                        self.stdout.write(f'    WooCommerce: {stats["woo_synced"]} sincronizzati')
                    
                    if stats['products_errors'] > 0:
                        self.stdout.write(self.style.WARNING(f'    ⚠ Errori: {stats["products_errors"]}'))
                    
                    # Accumula statistiche
                    for key, value in stats.items():
                        total_stats[key] = total_stats.get(key, 0) + value
                else:
                    self.stdout.write(self.style.ERROR(f'  ✗ Errore: {result.get("error", "Sconosciuto")}'))
                    
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'  ✗ Errore: {e}'))
        
        # Statistiche finali
        duration = time.time() - start_time
        self.stdout.write(f'\n=== SINCRONIZZAZIONE COMPLETATA ===')
        self.stdout.write(f'Durata: {duration:.2f} secondi')
        self.stdout.write(f'Prodotti processati: {total_stats["products_processed"]}')
        self.stdout.write(f'Prodotti creati: {total_stats["products_created"]}')
        self.stdout.write(f'Prodotti aggiornati: {total_stats["products_updated"]}')
        
        if total_stats['products_errors'] > 0:
            self.stdout.write(self.style.WARNING(f'Errori: {total_stats["products_errors"]}'))
        
        if sync_to_woocommerce:
            self.stdout.write(f'WooCommerce sincronizzati: {total_stats["woo_synced"]}')
        
        self.stdout.write(self.style.SUCCESS('Sincronizzazione completata con successo!'))
    
    def test_connections(self):
        """Testa le connessioni con tutti i fornitori"""
        self.stdout.write(self.style.SUCCESS('=== TEST CONNESSIONI ==='))
        
        from suppliers.clients.factory import SupplierClientFactory
        
        suppliers = Supplier.objects.filter(is_active=True)
        
        if not suppliers:
            self.stdout.write(self.style.WARNING('Nessun fornitore attivo trovato'))
            return
        
        all_ok = True
        
        for supplier in suppliers:
            self.stdout.write(f'\nTestando {supplier.name} ({supplier.supplier_type})...')
            
            try:
                client = SupplierClientFactory.create_client(supplier)
                
                # Test configurazione
                if supplier.is_api_configured:
                    self.stdout.write('  ✓ Configurazione OK')
                else:
                    self.stdout.write(self.style.WARNING('  ⚠ Configurazione incompleta'))
                    all_ok = False
                
                # Test connessione
                if client.test_connection():
                    self.stdout.write('  ✓ Connessione OK')
                else:
                    self.stdout.write(self.style.ERROR('  ✗ Connessione fallita'))
                    all_ok = False
                    
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'  ✗ Errore: {e}'))
                all_ok = False
        
        # Test WooCommerce
        self.stdout.write(f'\nTestando WooCommerce...')
        try:
            woo_client = WooCommerceClient()
            if woo_client.test_connection():
                self.stdout.write('  ✓ WooCommerce OK')
            else:
                self.stdout.write(self.style.ERROR('  ✗ WooCommerce fallito'))
                all_ok = False
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'  ✗ WooCommerce errore: {e}'))
            all_ok = False
        
        if all_ok:
            self.stdout.write(self.style.SUCCESS('\n✓ Tutte le connessioni funzionano correttamente'))
        else:
            self.stdout.write(self.style.ERROR('\n✗ Alcune connessioni hanno problemi'))
    
    def show_stats(self):
        """Mostra statistiche sincronizzazioni"""
        self.stdout.write(self.style.SUCCESS('=== STATISTICHE SINCRONIZZAZIONI ==='))
        
        stats = self.sync_service.get_sync_stats()
        
        self.stdout.write(f'\nProdotti totali: {stats["total_products"]}')
        
        self.stdout.write('\nProdotti per fornitore:')
        for supplier_name, count in stats['products_by_supplier'].items():
            self.stdout.write(f'  {supplier_name}: {count}')
        
        self.stdout.write('\nUltime sincronizzazioni:')
        for sync in stats['recent_syncs']:
            status_style = self.style.SUCCESS if sync['status'] == 'SUCCESS' else self.style.ERROR
            duration = ''
            if sync['completed_at'] and sync['started_at']:
                duration = f" ({(sync['completed_at'] - sync['started_at']).total_seconds():.1f}s)"
            
            self.stdout.write(f'  {sync["started_at"].strftime("%Y-%m-%d %H:%M")} - '
                            f'{sync["supplier__name"]} - '
                            f'{status_style(sync["status"])}'
                            f'{duration} - '
                            f'{sync["products_processed"]} prodotti')
        
        if stats['sync_errors'] > 0:
            self.stdout.write(self.style.WARNING(f'\nErrori non risolti: {stats["sync_errors"]}'))
        else:
            self.stdout.write(self.style.SUCCESS('\nNessun errore non risolto'))
    
    def clear_cache(self, supplier_name=None):
        """Pulisce la cache"""
        self.stdout.write(self.style.SUCCESS('=== PULIZIA CACHE ==='))
        
        if supplier_name:
            suppliers = self.get_suppliers_by_name_or_code(supplier_name)
        else:
            suppliers = Supplier.objects.filter(is_active=True)
        
        for supplier in suppliers:
            self.stdout.write(f'Pulizia cache {supplier.name}...')
            self.sync_service.clear_supplier_cache(supplier)
            self.stdout.write('  ✓ Cache pulita')
        
        self.stdout.write(self.style.SUCCESS('Pulizia cache completata'))
    
    def get_suppliers_by_name_or_code(self, identifier):
        """Trova fornitori per nome o codice"""
        suppliers = Supplier.objects.filter(is_active=True)
        
        # Cerca per codice esatto
        exact_match = suppliers.filter(code__iexact=identifier)
        if exact_match.exists():
            return exact_match
        
        # Cerca per nome (case insensitive, contiene)
        name_match = suppliers.filter(name__icontains=identifier)
        if name_match.exists():
            return name_match
        
        # Nessuna corrispondenza
        raise CommandError(f'Fornitore "{identifier}" non trovato')
    
    def confirm_action(self, message):
        """Chiede conferma all'utente"""
        response = input(f'{message} (s/N): ')
        return response.lower() in ['s', 'si', 'y', 'yes']
