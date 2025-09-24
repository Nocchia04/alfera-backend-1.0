#!/usr/bin/env python
"""
Script per configurare WooCommerce e testare la connessione
"""
import os
import sys
import django
from pathlib import Path

# Setup Django
BASE_DIR = Path(__file__).resolve().parent.parent.parent
sys.path.append(str(BASE_DIR))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'hotel_sync.settings')

# Configura variabili WooCommerce
os.environ['WOOCOMMERCE_KEY'] = 'ck_f91ae98c1959c3a86cc4c78eb0a567a377d13282'
os.environ['WOOCOMMERCE_SECRET'] = 'cs_c6f622a680be721da388bbcc3a049567797bffeb'

try:
    django.setup()
except Exception as e:
    print(f"❌ Errore setup Django: {e}")
    sys.exit(1)

from woocommerce_integration.client import WooCommerceClient
from django.conf import settings

def main():
    print("🛒 SETUP WOOCOMMERCE")
    print("=" * 50)
    
    # Chiedi URL WooCommerce
    print("\n📝 Configurazione WooCommerce:")
    woo_url = input("Inserisci l'URL del tuo sito WooCommerce (es: https://miosito.com): ").strip()
    
    if not woo_url:
        print("❌ URL richiesto!")
        return
    
    # Aggiorna variabile ambiente
    os.environ['WOOCOMMERCE_URL'] = woo_url
    
    print(f"\n🔑 Credenziali configurate:")
    print(f"   URL: {woo_url}")
    print(f"   Consumer Key: ck_f91ae98c...d13282")
    print(f"   Consumer Secret: cs_c6f622a6...97bffeb")
    
    # Test connessione
    print(f"\n🔗 Test connessione WooCommerce...")
    
    try:
        # Aggiorna settings Django
        settings.WOOCOMMERCE_URL = woo_url
        settings.WOOCOMMERCE_KEY = 'ck_f91ae98c1959c3a86cc4c78eb0a567a377d13282'
        settings.WOOCOMMERCE_SECRET = 'cs_c6f622a680be721da388bbcc3a049567797bffeb'
        
        woo_client = WooCommerceClient()
        
        if woo_client.test_connection():
            print("   ✅ Connessione WooCommerce riuscita!")
            
            # Mostra statistiche
            try:
                stats = woo_client.get_product_stats()
                print(f"\n📊 Statistiche WooCommerce:")
                for status, count in stats.items():
                    print(f"   {status}: {count} prodotti")
            except Exception as e:
                print(f"   ⚠️ Impossibile recuperare statistiche: {e}")
            
            print(f"\n✅ WooCommerce configurato correttamente!")
            print(f"💡 Ora puoi eseguire:")
            print(f"   python manage.py sync --supplier MKTO --test-connections")
            print(f"   python manage.py sync --supplier MKTO --dry-run")
            print(f"   python manage.py sync --supplier MKTO")
            
        else:
            print("   ❌ Connessione WooCommerce fallita!")
            print("   Verifica:")
            print("   • URL corretto")
            print("   • Credenziali API valide")
            print("   • WooCommerce REST API abilitata")
            
    except Exception as e:
        print(f"   ❌ Errore test WooCommerce: {e}")
        print(f"   Verifica le credenziali e l'URL")

if __name__ == '__main__':
    main()
