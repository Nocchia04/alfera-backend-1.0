#!/usr/bin/env python
"""
🗑️ ELIMINA TUTTI I PRODOTTI WOOCOMMERCE IN BULK
Script per pulire completamente il catalogo WooCommerce
"""
import os
import sys
import django
from pathlib import Path
import time

# Setup Django
BASE_DIR = Path(__file__).resolve().parent.parent.parent
sys.path.append(str(BASE_DIR))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'hotel_sync.settings')

try:
    django.setup()
except Exception as e:
    print(f"❌ Errore setup Django: {e}")
    sys.exit(1)

from woocommerce_integration.client import WooCommerceClient

def delete_all_products():
    """Elimina tutti i prodotti WooCommerce in bulk"""
    
    print("🗑️ ELIMINAZIONE BULK PRODOTTI WOOCOMMERCE")
    print("=" * 50)
    print("⚠️  ATTENZIONE: Questa operazione eliminerà TUTTI i prodotti!")
    print("⚠️  L'operazione NON è reversibile!")
    print("=" * 50)
    
    # Conferma utente
    confirm = input("\n❓ Sei sicuro di voler eliminare TUTTI i prodotti? (scrivi 'ELIMINA TUTTO'): ")
    if confirm != "ELIMINA TUTTO":
        print("❌ Operazione annullata.")
        return
    
    # Seconda conferma
    confirm2 = input("\n❓ ULTIMA CONFERMA - Elimino veramente tutto? (scrivi 'SI'): ")
    if confirm2 != "SI":
        print("❌ Operazione annullata.")
        return
    
    try:
        print(f"\n🔌 Connessione a WooCommerce...")
        wc_client = WooCommerceClient()
        
        # Statistiche iniziali
        print(f"\n📊 Recupero statistiche attuali...")
        initial_stats = wc_client.get_product_stats()
        if initial_stats:
            total_products = initial_stats.get('total_products', 0)
            print(f"   📦 Prodotti totali: {total_products}")
            print(f"   📋 Prodotti bozza: {initial_stats.get('draft_products', 0)}")
            print(f"   ✅ Prodotti pubblicati: {initial_stats.get('publish_products', 0)}")
        else:
            print("   ⚠️ Impossibile recuperare statistiche")
            total_products = 0
        
        if total_products == 0:
            print("✅ Nessun prodotto da eliminare!")
            return
        
        print(f"\n🔄 INIZIO ELIMINAZIONE...")
        print(f"⏰ Inizio: {time.strftime('%H:%M:%S')}")
        
        deleted_count = 0
        batch_size = 100  # WooCommerce API limit
        page = 1
        
        while True:
            print(f"\n📄 Recupero pagina {page} (batch {batch_size})...")
            
            # Recupera prodotti in batch
            try:
                response = wc_client.wcapi.get('products', params={
                    'per_page': batch_size,
                    'page': page,
                    'status': 'any'  # Tutti gli stati
                })
                
                if response.status_code != 200:
                    print(f"❌ Errore recupero prodotti: {response.status_code}")
                    break
                
                products = response.json()
                
                if not products:
                    print("✅ Nessun prodotto rimanente")
                    break
                
                print(f"   📦 Trovati {len(products)} prodotti in questa pagina")
                
                # Elimina prodotti in batch
                if len(products) == 1:
                    # Eliminazione singola
                    product_id = products[0]['id']
                    delete_response = wc_client.wcapi.delete(f'products/{product_id}', params={'force': True})
                    
                    if delete_response.status_code == 200:
                        deleted_count += 1
                        print(f"   ✅ Eliminato prodotto ID {product_id}")
                    else:
                        print(f"   ❌ Errore eliminazione ID {product_id}: {delete_response.status_code}")
                else:
                    # Eliminazione batch
                    batch_data = {
                        'delete': [product['id'] for product in products]
                    }
                    
                    delete_response = wc_client.wcapi.post('products/batch', batch_data)
                    
                    if delete_response.status_code == 200:
                        result = delete_response.json()
                        deleted_in_batch = len(result.get('delete', []))
                        deleted_count += deleted_in_batch
                        print(f"   ✅ Eliminati {deleted_in_batch} prodotti in batch")
                        
                        # Mostra progress
                        if total_products > 0:
                            progress = (deleted_count / total_products) * 100
                            print(f"   📊 Progresso: {deleted_count}/{total_products} ({progress:.1f}%)")
                    else:
                        print(f"   ❌ Errore batch delete: {delete_response.status_code}")
                        print(f"      {delete_response.text[:200]}")
                        
                        # Fallback: eliminazione singola
                        print(f"   🔄 Fallback eliminazione singola...")
                        for product in products:
                            delete_response = wc_client.wcapi.delete(f'products/{product["id"]}', params={'force': True})
                            if delete_response.status_code == 200:
                                deleted_count += 1
                                print(f"      ✅ Eliminato ID {product['id']}")
                            else:
                                print(f"      ❌ Errore ID {product['id']}")
                
                # Pausa per non sovraccaricare API
                time.sleep(1)
                page += 1
                
                # Safety check - max 1000 pagine
                if page > 1000:
                    print("⚠️ Raggiunto limite pagine (1000) - interruzione per sicurezza")
                    break
                    
            except Exception as e:
                print(f"❌ Errore durante eliminazione: {e}")
                break
        
        print(f"\n📊 ELIMINAZIONE COMPLETATA!")
        print(f"⏰ Fine: {time.strftime('%H:%M:%S')}")
        print(f"🗑️ Prodotti eliminati: {deleted_count}")
        
        # Verifica finale
        print(f"\n🔍 Verifica finale...")
        final_stats = wc_client.get_product_stats()
        if final_stats:
            remaining = final_stats.get('total_products', 0)
            print(f"   📦 Prodotti rimanenti: {remaining}")
            
            if remaining == 0:
                print("✅ TUTTI I PRODOTTI ELIMINATI CON SUCCESSO!")
            else:
                print(f"⚠️ Rimangono {remaining} prodotti - potrebbero essere protetti o in cestino")
        
        # Pulizia database locale (opzionale)
        cleanup_local = input(f"\n❓ Vuoi pulire anche il database locale? (s/N): ")
        if cleanup_local.lower() == 's':
            cleanup_local_database()
        
        print(f"\n🎉 OPERAZIONE COMPLETATA!")
        
    except Exception as e:
        print(f"❌ Errore critico: {e}")
        import traceback
        traceback.print_exc()

def cleanup_local_database():
    """Pulisce anche il database locale"""
    print(f"\n🧹 PULIZIA DATABASE LOCALE...")
    
    try:
        from products.models import Product, ProductVariant, Stock, Price
        from sync.models import SyncLog, SyncError
        
        # Conta record
        products_count = Product.objects.count()
        variants_count = ProductVariant.objects.count()
        stock_count = Stock.objects.count()
        prices_count = Price.objects.count()
        
        print(f"   📦 Prodotti: {products_count}")
        print(f"   🎨 Varianti: {variants_count}")
        print(f"   📊 Stock: {stock_count}")
        print(f"   💰 Prezzi: {prices_count}")
        
        if products_count == 0:
            print("✅ Database locale già pulito!")
            return
        
        confirm_db = input(f"\n❓ Confermi eliminazione database locale? (scrivi 'PULISCI DB'): ")
        if confirm_db != "PULISCI DB":
            print("❌ Pulizia database annullata")
            return
        
        # Elimina in ordine (foreign keys)
        print(f"   🗑️ Eliminazione varianti...")
        ProductVariant.objects.all().delete()
        
        print(f"   🗑️ Eliminazione stock...")
        Stock.objects.all().delete()
        
        print(f"   🗑️ Eliminazione prezzi...")
        Price.objects.all().delete()
        
        print(f"   🗑️ Eliminazione prodotti...")
        Product.objects.all().delete()
        
        print(f"   🗑️ Eliminazione log sync...")
        SyncError.objects.all().delete()
        SyncLog.objects.all().delete()
        
        print(f"✅ Database locale pulito!")
        
    except Exception as e:
        print(f"❌ Errore pulizia database: {e}")

def show_current_stats():
    """Mostra statistiche attuali senza eliminare"""
    print("📊 STATISTICHE ATTUALI WOOCOMMERCE")
    print("=" * 40)
    
    try:
        wc_client = WooCommerceClient()
        stats = wc_client.get_product_stats()
        
        if stats:
            print(f"📦 Prodotti totali: {stats.get('total_products', 0)}")
            print(f"📋 Prodotti bozza: {stats.get('draft_products', 0)}")
            print(f"✅ Prodotti pubblicati: {stats.get('publish_products', 0)}")
            print(f"🗑️ Prodotti cestino: {stats.get('trash_products', 0)}")
        else:
            print("❌ Impossibile recuperare statistiche")
            
    except Exception as e:
        print(f"❌ Errore: {e}")

def main():
    """Menu principale"""
    print("🗑️ GESTIONE PRODOTTI WOOCOMMERCE")
    print("=" * 40)
    print("1. Mostra statistiche attuali")
    print("2. Elimina TUTTI i prodotti")
    print("3. Esci")
    
    choice = input("\nScegli (1-3): ").strip()
    
    if choice == '1':
        show_current_stats()
    elif choice == '2':
        delete_all_products()
    elif choice == '3':
        print("👋 Arrivederci!")
    else:
        print("❌ Scelta non valida")

if __name__ == '__main__':
    main()
