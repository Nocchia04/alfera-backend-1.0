#!/usr/bin/env python
"""
🗑️ ELIMINA TUTTI I PRODOTTI WOOCOMMERCE - VERSIONE CORRETTA
Conta i prodotti direttamente tramite API, non tramite stats
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

def count_products_directly(wc_client):
    """Conta prodotti direttamente tramite API"""
    try:
        # Prima chiamata per vedere quanti ce ne sono
        response = wc_client.wcapi.get('products', params={
            'per_page': 1,
            'page': 1,
            'status': 'any'
        })
        
        if response.status_code == 200:
            # Controlla headers per total count
            total_products = response.headers.get('X-WP-Total', 0)
            total_pages = response.headers.get('X-WP-TotalPages', 0)
            
            print(f"📊 CONTEGGIO DIRETTO API:")
            print(f"   📦 Prodotti totali (header): {total_products}")
            print(f"   📄 Pagine totali: {total_pages}")
            
            return int(total_products) if total_products else 0
        else:
            print(f"❌ Errore conteggio: {response.status_code}")
            return 0
            
    except Exception as e:
        print(f"❌ Errore conteggio diretto: {e}")
        return 0

def delete_all_products_fixed():
    """Versione corretta eliminazione bulk"""
    
    print("🗑️ ELIMINAZIONE BULK PRODOTTI WOOCOMMERCE - FIXED")
    print("=" * 55)
    
    try:
        wc_client = WooCommerceClient()
        
        # Conta prodotti con metodo diretto
        total_products = count_products_directly(wc_client)
        
        if total_products == 0:
            print("✅ Nessun prodotto trovato!")
            return
        
        print(f"\n⚠️  TROVATI {total_products} PRODOTTI DA ELIMINARE!")
        print("⚠️  L'operazione NON è reversibile!")
        
        # Conferma
        confirm = input(f"\n❓ Elimino tutti i {total_products} prodotti? (scrivi 'SI'): ")
        if confirm != "SI":
            print("❌ Operazione annullata")
            return
        
        print(f"\n🗑️ INIZIO ELIMINAZIONE...")
        deleted_count = 0
        batch_size = 100
        max_iterations = 50  # Safety limit
        iteration = 0
        
        while deleted_count < total_products and iteration < max_iterations:
            iteration += 1
            print(f"\n🔄 Iterazione {iteration} - Recupero prodotti...")
            
            # Recupera sempre la prima pagina (perché eliminando si spostano)
            response = wc_client.wcapi.get('products', params={
                'per_page': batch_size,
                'page': 1,
                'status': 'any'
            })
            
            if response.status_code != 200:
                print(f"❌ Errore recupero: {response.status_code}")
                break
            
            products = response.json()
            
            if not products:
                print("✅ Nessun prodotto rimanente")
                break
            
            print(f"   📦 Trovati {len(products)} prodotti")
            
            # Elimina ogni prodotto singolarmente (più affidabile)
            for product in products:
                product_id = product['id']
                product_name = product.get('name', 'Senza nome')[:30]
                
                try:
                    delete_response = wc_client.wcapi.delete(
                        f'products/{product_id}', 
                        params={'force': True}
                    )
                    
                    if delete_response.status_code == 200:
                        deleted_count += 1
                        print(f"   ✅ [{deleted_count:4d}] Eliminato: {product_name}")
                        
                        # Progress ogni 10 eliminazioni
                        if deleted_count % 10 == 0:
                            progress = (deleted_count / total_products) * 100
                            print(f"   📊 Progresso: {deleted_count}/{total_products} ({progress:.1f}%)")
                    else:
                        print(f"   ❌ Errore eliminazione ID {product_id}: {delete_response.status_code}")
                        
                except Exception as e:
                    print(f"   ❌ Errore prodotto {product_id}: {e}")
            
            # Pausa tra batch
            time.sleep(2)
        
        print(f"\n📊 ELIMINAZIONE COMPLETATA!")
        print(f"🗑️ Prodotti eliminati: {deleted_count}")
        
        # Verifica finale
        print(f"\n🔍 Verifica finale...")
        remaining = count_products_directly(wc_client)
        print(f"   📦 Prodotti rimanenti: {remaining}")
        
        if remaining == 0:
            print("🎉 TUTTI I PRODOTTI ELIMINATI!")
        else:
            print(f"⚠️ Rimangono {remaining} prodotti")
            
            # Opzione per continuare
            if remaining > 0 and remaining < total_products:
                continue_delete = input(f"\n❓ Continuo con i {remaining} rimanenti? (s/N): ")
                if continue_delete.lower() == 's':
                    delete_remaining_products(wc_client, remaining)
        
    except Exception as e:
        print(f"❌ Errore critico: {e}")
        import traceback
        traceback.print_exc()

def delete_remaining_products(wc_client, count):
    """Elimina prodotti rimanenti uno per uno"""
    print(f"\n🔄 ELIMINAZIONE PRODOTTI RIMANENTI...")
    
    for i in range(count):
        try:
            # Prendi sempre il primo prodotto
            response = wc_client.wcapi.get('products', params={
                'per_page': 1,
                'page': 1,
                'status': 'any'
            })
            
            if response.status_code == 200:
                products = response.json()
                if products:
                    product_id = products[0]['id']
                    delete_response = wc_client.wcapi.delete(f'products/{product_id}', params={'force': True})
                    
                    if delete_response.status_code == 200:
                        print(f"   ✅ [{i+1}] Eliminato prodotto ID {product_id}")
                    else:
                        print(f"   ❌ Errore eliminazione ID {product_id}")
                else:
                    print("✅ Nessun prodotto rimanente")
                    break
            
            time.sleep(1)
            
        except Exception as e:
            print(f"   ❌ Errore: {e}")

def show_real_stats():
    """Mostra statistiche reali"""
    print("📊 STATISTICHE REALI WOOCOMMERCE")
    print("=" * 40)
    
    try:
        wc_client = WooCommerceClient()
        
        # Conta direttamente
        total = count_products_directly(wc_client)
        
        # Conta per stato
        states = ['publish', 'draft', 'private', 'trash']
        state_counts = {}
        
        for state in states:
            response = wc_client.wcapi.get('products', params={
                'per_page': 1,
                'status': state
            })
            if response.status_code == 200:
                count = response.headers.get('X-WP-Total', 0)
                state_counts[state] = int(count) if count else 0
        
        print(f"📦 Prodotti totali: {total}")
        for state, count in state_counts.items():
            if count > 0:
                print(f"   {state}: {count}")
                
    except Exception as e:
        print(f"❌ Errore: {e}")

if __name__ == '__main__':
    print("🗑️ GESTIONE PRODOTTI WOOCOMMERCE - FIXED")
    print("=" * 45)
    print("1. Mostra statistiche reali")
    print("2. Elimina TUTTI i prodotti")
    print("3. Esci")
    
    choice = input("\nScegli (1-3): ").strip()
    
    if choice == '1':
        show_real_stats()
    elif choice == '2':
        delete_all_products_fixed()
    elif choice == '3':
        print("👋 Arrivederci!")
    else:
        print("❌ Scelta non valida")
