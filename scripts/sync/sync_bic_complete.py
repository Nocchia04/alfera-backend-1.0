#!/usr/bin/env python
"""
Script per sincronizzazione completa fornitore BIC
"""
import os
import sys
import django
from pathlib import Path
import argparse

# Setup Django
BASE_DIR = Path(__file__).resolve().parent
sys.path.append(str(BASE_DIR))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'hotel_sync.settings')

try:
    django.setup()
except Exception as e:
    print(f"❌ Errore setup Django: {e}")
    sys.exit(1)

from suppliers.models import Supplier, SyncLog
from sync.services.sync_service import SyncService
from woocommerce_integration.client import WooCommerceClient
import logging

logger = logging.getLogger('sync')

def run_bic_sync():
    parser = argparse.ArgumentParser(description="Esegue la sincronizzazione completa per il fornitore BIC.")
    parser.add_argument('--no-woocommerce', action='store_true', help="Sincronizza solo nel DB locale, salta WooCommerce.")
    parser.add_argument('--limit', type=int, help="Limita il numero di prodotti da processare per test (solo per analisi).")
    parser.add_argument('--language', default='it', help="Lingua preferita per i prodotti (default: it).")
    
    args = parser.parse_args()

    print("\n🚀 AVVIO SINCRONIZZAZIONE COMPLETA BIC")
    print("=" * 50)
    print(f"Sincronizza su WooCommerce: {not args.no_woocommerce}")
    print(f"Limite per analisi: {args.limit if args.limit else 'Nessuno'}")
    print(f"Lingua preferita: {args.language}")

    try:
        # Trova o crea fornitore BIC
        bic_supplier, created = Supplier.objects.get_or_create(
            code='BIC',
            defaults={
                'name': 'BIC Europe',
                'supplier_type': 'BIC',
                'csv_path': os.path.abspath('BGE_Masterfile_Distributor_EUR.csv'),
                'is_active': True
            }
        )
        
        if created:
            print(f"✅ Fornitore BIC creato: {bic_supplier.name}")
        else:
            print(f"✅ Fornitore BIC trovato: {bic_supplier.name}")
        
        print(f"📁 CSV Path: {bic_supplier.csv_path}")
        print(f"🔧 Configurato: {bic_supplier.is_api_configured}")

        if not bic_supplier.is_api_configured:
            print("❌ Fornitore BIC non configurato correttamente!")
            print("   Verifica che il percorso CSV sia corretto.")
            return

        # Inizializza servizio sincronizzazione
        sync_service = SyncService()
        
        # Configura lingua preferita per BIC parser
        from suppliers.clients.factory import SupplierClientFactory
        client = SupplierClientFactory.create_client(bic_supplier)
        if hasattr(client, 'preferred_language'):
            client.preferred_language = args.language
            print(f"🌐 Lingua preferita impostata: {args.language}")

        print("\n📊 ANALISI PRELIMINARE BIC")
        print("-" * 30)
        
        # Test rapido per statistiche
        analysis_limit = args.limit if args.limit else 10
        sample_products = client.get_products(limit=analysis_limit)
        if sample_products:
            print(f"✅ Parser funzionante - Sample: {len(sample_products)} prodotti")
            
            # Analizza lingue disponibili
            languages = set()
            for product in sample_products:
                multilang_data = product.get('multilang_data', {})
                languages.update(multilang_data.keys())
            
            print(f"🌐 Lingue disponibili: {sorted(list(languages))}")
            
            # Analizza categorie
            categories = set()
            for product in sample_products:
                categories.update(product.get('categories', []))
            
            print(f"🏷️ Categorie trovate: {sorted(list(categories))}")
            
        else:
            print("❌ Nessun prodotto trovato nel CSV!")
            return

        print("\n🔄 AVVIO SINCRONIZZAZIONE PRODOTTI")
        print("-" * 40)
        
        # Esegui sincronizzazione
        sync_result = sync_service.sync_supplier(
            supplier=bic_supplier,
            sync_to_woocommerce=not args.no_woocommerce
        )
        
        # Estrai sync_log dal risultato
        sync_log = sync_result.get('sync_log')
        
        print("\n📈 RIEPILOGO SINCRONIZZAZIONE BIC")
        print("=" * 50)
        
        if sync_log:
            print(f"📦 Prodotti processati: {sync_log.products_processed}")
            print(f"✅ Prodotti creati: {sync_log.products_created}")
            print(f"🔄 Prodotti aggiornati: {sync_log.products_updated}")
            print(f"🎨 Varianti processate: {sync_log.variants_processed}")
            print(f"📊 Stock aggiornato: {sync_log.stock_updated}")
            print(f"💰 Prezzi aggiornati: {sync_log.prices_updated}")
            print(f"❌ Errori: {sync_log.errors_count}")
            print(f"⏱️ Durata: {sync_log.duration:.2f} secondi")
            
            if sync_log.products_processed > 0:
                print(f"📈 Velocità: {sync_log.products_processed/sync_log.duration:.1f} prodotti/secondo")
        else:
            print("⚠️ Nessun sync_log disponibile")
            print(f"Risultato sincronizzazione: {sync_result}")

        # Statistiche WooCommerce
        if not args.no_woocommerce:
            print("\n🛒 STATO PRODOTTI WOOCOMMERCE")
            print("-" * 30)
            try:
                wc_client = WooCommerceClient()
                wc_stats = wc_client.get_product_stats()
                if wc_stats:
                    print(f"📦 Prodotti totali: {wc_stats.get('total_products', 0)}")
                    print(f"📋 Prodotti in bozza: {wc_stats.get('draft_products', 0)}")
                    print(f"✅ Prodotti pubblicati: {wc_stats.get('publish_products', 0)}")
                else:
                    print("⚠️ Impossibile recuperare statistiche da WooCommerce")
            except Exception as e:
                print(f"❌ Errore statistiche WooCommerce: {e}")

        # Analisi errori
        if sync_log and sync_log.errors_count > 0:
            print(f"\n⚠️ ERRORI RILEVATI ({sync_log.errors_count})")
            print("-" * 20)
            from sync.models import SyncError
            recent_errors = SyncError.objects.filter(
                sync_log=sync_log
            ).order_by('-created_at')[:5]
            
            for error in recent_errors:
                print(f"❌ {error.error_type}: {error.error_message[:100]}...")

        print(f"\n🎉 SINCRONIZZAZIONE BIC COMPLETATA!")
        print("💾 Dati salvati nel database")
        if not args.no_woocommerce:
            print("🛒 Prodotti sincronizzati su WooCommerce (in bozza)")

    except Supplier.DoesNotExist:
        print("❌ Errore: Fornitore BIC non trovato.")
        print("   Esegui: python manage.py loaddata suppliers/fixtures/bic_supplier.json")
    except Exception as e:
        logger.exception("Errore critico durante la sincronizzazione BIC")
        print(f"❌ Errore critico: {e}")

if __name__ == "__main__":
    run_bic_sync()
