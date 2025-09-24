#!/usr/bin/env python
"""
Script completo per sincronizzazione MKTO → Database → WooCommerce
"""
import os
import sys
import django
from pathlib import Path
from datetime import datetime

# Setup Django
BASE_DIR = Path(__file__).resolve().parent.parent.parent
sys.path.append(str(BASE_DIR))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'hotel_sync.settings')

# Configura credenziali WooCommerce
os.environ['WOOCOMMERCE_KEY'] = 'ck_f91ae98c1959c3a86cc4c78eb0a567a377d13282'
os.environ['WOOCOMMERCE_SECRET'] = 'cs_c6f622a680be721da388bbcc3a049567797bffeb'

try:
    django.setup()
except Exception as e:
    print(f"❌ Errore setup Django: {e}")
    sys.exit(1)

from suppliers.models import Supplier
from products.models import Product, ProductVariant, Stock, Price
from sync.services.sync_service import SyncService
from woocommerce_integration.client import WooCommerceClient
from django.conf import settings

def main():
    print("🚀 SINCRONIZZAZIONE COMPLETA MKTO")
    print("=" * 60)
    print(f"⏰ Inizio: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Configurazione
    woo_url = input("\n📝 URL WooCommerce (es: https://miosito.com): ").strip()
    if not woo_url:
        print("❌ URL WooCommerce richiesto!")
        return
    
    # Aggiorna settings
    os.environ['WOOCOMMERCE_URL'] = woo_url
    settings.WOOCOMMERCE_URL = woo_url
    settings.WOOCOMMERCE_KEY = 'ck_f91ae98c1959c3a86cc4c78eb0a567a377d13282'
    settings.WOOCOMMERCE_SECRET = 'cs_c6f622a680be721da388bbcc3a049567797bffeb'
    
    # Opzioni
    print(f"\n🔧 Opzioni sincronizzazione:")
    sync_woo = input("Sincronizzare anche su WooCommerce? (s/N): ").lower() in ['s', 'si', 'y', 'yes']
    dry_run = input("Modalità dry-run (solo simulazione)? (s/N): ").lower() in ['s', 'si', 'y', 'yes']
    
    try:
        # 1. Verifica fornitore MKTO
        print(f"\n1️⃣ Verifica Fornitore MKTO...")
        mkto = Supplier.objects.get(code='MKTO')
        print(f"   ✅ Fornitore: {mkto.name}")
        print(f"   📁 Path XML: {mkto.xml_path}")
        
        # 2. Test connessioni
        print(f"\n2️⃣ Test Connessioni...")
        
        # Test WooCommerce se richiesto
        if sync_woo:
            woo_client = WooCommerceClient()
            if woo_client.test_connection():
                print(f"   ✅ WooCommerce connesso")
                stats = woo_client.get_product_stats()
                total_products = sum(stats.values())
                print(f"   📊 Prodotti WooCommerce attuali: {total_products}")
            else:
                print(f"   ❌ WooCommerce non raggiungibile")
                sync_woo = False
        
        if dry_run:
            print(f"\n⚠️ MODALITÀ DRY-RUN - Nessuna modifica sarà effettuata")
            return simulate_sync(mkto)
        
        # 3. Sincronizzazione database
        print(f"\n3️⃣ Sincronizzazione Database...")
        
        # Conta prodotti prima
        products_before = Product.objects.filter(supplier=mkto).count()
        print(f"   📦 Prodotti MKTO esistenti: {products_before}")
        
        # Esegui sincronizzazione
        sync_service = SyncService()
        result = sync_service.sync_supplier(mkto, sync_to_woocommerce=sync_woo)
        
        if result['success']:
            stats = result['stats']
            print(f"   ✅ Sincronizzazione completata!")
            print(f"   📊 Statistiche:")
            print(f"      • Prodotti processati: {stats['products_processed']}")
            print(f"      • Prodotti creati: {stats['products_created']}")
            print(f"      • Prodotti aggiornati: {stats['products_updated']}")
            print(f"      • Stock aggiornati: {stats['stock_updated']}")
            print(f"      • Prezzi aggiornati: {stats['prices_updated']}")
            
            if sync_woo:
                print(f"      • WooCommerce sincronizzati: {stats['woo_synced']}")
            
            if stats['products_errors'] > 0:
                print(f"      ⚠️ Errori: {stats['products_errors']}")
        else:
            print(f"   ❌ Sincronizzazione fallita: {result.get('error')}")
            return
        
        # 4. Verifica risultati
        print(f"\n4️⃣ Verifica Risultati...")
        
        products_after = Product.objects.filter(supplier=mkto).count()
        variants_count = ProductVariant.objects.filter(product__supplier=mkto).count()
        stock_count = Stock.objects.filter(variant__product__supplier=mkto).count()
        
        print(f"   📦 Prodotti totali MKTO: {products_after}")
        print(f"   🎨 Varianti totali: {variants_count}")
        print(f"   📊 Record stock: {stock_count}")
        
        # Mostra primi prodotti
        print(f"\n   📋 Primi 5 prodotti sincronizzati:")
        recent_products = Product.objects.filter(supplier=mkto).order_by('-created_at')[:5]
        for i, p in enumerate(recent_products, 1):
            print(f"      {i}. {p.name[:50]}... ({p.sku})")
            print(f"         Varianti: {p.variants.count()}, Stock totale: {p.total_stock}")
        
        # 5. Riepilogo finale
        print(f"\n" + "=" * 60)
        print(f"✅ SINCRONIZZAZIONE COMPLETATA!")
        print(f"⏰ Fine: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        if sync_woo:
            print(f"🛒 Prodotti disponibili in WooCommerce come BOZZE")
            print(f"💡 Accedi al tuo WordPress admin per pubblicarli")
        else:
            print(f"💡 Per sincronizzare su WooCommerce:")
            print(f"   python manage.py sync --supplier MKTO")
        
    except Supplier.DoesNotExist:
        print(f"❌ Fornitore MKTO non trovato!")
        print(f"   Esegui prima: python test_mkto_simple.py")
    except Exception as e:
        print(f"❌ Errore: {e}")
        import traceback
        traceback.print_exc()

def simulate_sync(mkto):
    """Simula la sincronizzazione"""
    print(f"\n🎭 SIMULAZIONE SINCRONIZZAZIONE...")
    
    from suppliers.clients.factory import SupplierClientFactory
    
    try:
        client = SupplierClientFactory.create_client(mkto)
        
        # Test parsing limitato
        products = client.get_products(limit=10, force_refresh=True)
        stock = client.get_stock(limit=10, force_refresh=True)
        prices = client.get_prices(limit=10, force_refresh=True)
        
        print(f"   📦 Prodotti da processare: {len(products)}")
        print(f"   📊 Record stock: {len(stock)}")
        print(f"   💰 Prezzi: {len(prices)}")
        
        # Mostra esempi
        if products:
            print(f"\n   📋 Esempi prodotti:")
            for i, p in enumerate(products[:3], 1):
                print(f"      {i}. {p['name'][:40]}... (Ref: {p['supplier_ref']})")
                print(f"         Varianti: {len(p.get('variants', []))}")
        
        print(f"\n✅ Simulazione completata - Nessun dato modificato")
        
    except Exception as e:
        print(f"❌ Errore simulazione: {e}")

if __name__ == '__main__':
    main()
