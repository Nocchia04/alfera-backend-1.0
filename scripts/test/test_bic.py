#!/usr/bin/env python
"""
Script per testare il parser BIC
"""
import os
import sys
import django
from pathlib import Path
import json

# Setup Django
BASE_DIR = Path(__file__).resolve().parent.parent.parent
sys.path.append(str(BASE_DIR))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'hotel_sync.settings')

try:
    django.setup()
except Exception as e:
    print(f"❌ Errore setup Django: {e}")
    sys.exit(1)

from suppliers.models import Supplier
from suppliers.clients.factory import SupplierClientFactory

def test_bic_system():
    """Test completo sistema BIC"""
    results = {
        'timestamp': str(django.utils.timezone.now()),
        'tests': {}
    }
    
    print("🧪 TEST SISTEMA BIC")
    print("=" * 50)
    
    # Test 1: Verifica file CSV
    print("\n1️⃣ Test File CSV...")
    csv_path = "data/BGE_Masterfile_Distributor_EUR.csv"
    if os.path.exists(csv_path):
        file_size = os.path.getsize(csv_path)
        print(f"   ✅ File trovato: {csv_path}")
        print(f"   📊 Dimensione: {file_size:,} bytes")
        results['tests']['csv_file'] = {'success': True, 'size': file_size}
    else:
        print(f"   ❌ File non trovato: {csv_path}")
        results['tests']['csv_file'] = {'success': False, 'error': 'File non trovato'}
        return results
    
    # Test 2: Creazione fornitore BIC
    print("\n2️⃣ Test Fornitore BIC...")
    try:
        bic_supplier, created = Supplier.objects.get_or_create(
            code='BIC',
            defaults={
                'name': 'BIC Europe',
                'supplier_type': 'BIC',
                'csv_path': os.path.abspath(csv_path),
                'is_active': True
            }
        )
        
        action = "Creato" if created else "Trovato"
        print(f"   ✅ {action} fornitore: {bic_supplier.name}")
        print(f"   📁 CSV Path: {bic_supplier.csv_path}")
        print(f"   🔧 Configurato: {bic_supplier.is_api_configured}")
        results['tests']['supplier_creation'] = {'success': True, 'created': created}
        
    except Exception as e:
        print(f"   ❌ Errore creazione fornitore: {e}")
        results['tests']['supplier_creation'] = {'success': False, 'error': str(e)}
        return results
    
    # Test 3: Factory client
    print("\n3️⃣ Test Factory Client...")
    try:
        client = SupplierClientFactory.create_client(bic_supplier)
        print(f"   ✅ Client creato: {type(client).__name__}")
        results['tests']['client_factory'] = {'success': True, 'client_type': type(client).__name__}
        
    except Exception as e:
        print(f"   ❌ Errore factory: {e}")
        results['tests']['client_factory'] = {'success': False, 'error': str(e)}
        return results
    
    # Test 4: Parsing prodotti (sample)
    print("\n4️⃣ Test Parsing Prodotti (primi 5)...")
    try:
        products = client.get_products(limit=5)
        print(f"   ✅ Prodotti parsati: {len(products)}")
        
        if products:
            sample_product = products[0]
            print(f"   📦 Esempio prodotto:")
            print(f"      • SKU: {sample_product.get('sku', 'N/A')}")
            print(f"      • Nome: {sample_product.get('name', 'N/A')[:50]}...")
            print(f"      • Brand: {sample_product.get('brand', 'N/A')}")
            print(f"      • Categorie: {sample_product.get('categories', [])}")
            print(f"      • Immagini: {len(sample_product.get('images', []))}")
            print(f"      • Varianti: {len(sample_product.get('variants', []))}")
            print(f"      • Prezzi: {len(sample_product.get('prices', []))}")
            
            results['tests']['product_parsing'] = {
                'success': True,
                'count': len(products),
                'sample_product': {
                    'sku': sample_product.get('sku'),
                    'name': sample_product.get('name'),
                    'brand': sample_product.get('brand'),
                    'categories': sample_product.get('categories'),
                    'image_count': len(sample_product.get('images', [])),
                    'variant_count': len(sample_product.get('variants', [])),
                    'price_count': len(sample_product.get('prices', []))
                }
            }
        else:
            results['tests']['product_parsing'] = {'success': False, 'error': 'Nessun prodotto trovato'}
            
    except Exception as e:
        print(f"   ❌ Errore parsing: {e}")
        results['tests']['product_parsing'] = {'success': False, 'error': str(e)}
    
    # Test 5: Dati stampa
    print("\n5️⃣ Test Dati Stampa...")
    try:
        print_data = client.get_print_data()
        print(f"   ✅ Dati stampa: {len(print_data)} prodotti")
        results['tests']['print_data'] = {'success': True, 'count': len(print_data)}
        
    except Exception as e:
        print(f"   ❌ Errore dati stampa: {e}")
        results['tests']['print_data'] = {'success': False, 'error': str(e)}
    
    # Test 6: Analisi lingue
    print("\n6️⃣ Test Analisi Lingue...")
    try:
        all_products = client.get_products(limit=10)
        languages = set()
        
        for product in all_products:
            multilang_data = product.get('multilang_data', {})
            languages.update(multilang_data.keys())
        
        print(f"   ✅ Lingue trovate: {sorted(list(languages))}")
        results['tests']['language_analysis'] = {'success': True, 'languages': sorted(list(languages))}
        
    except Exception as e:
        print(f"   ❌ Errore analisi lingue: {e}")
        results['tests']['language_analysis'] = {'success': False, 'error': str(e)}
    
    # Test 7: Controllo performance
    print("\n7️⃣ Test Performance...")
    try:
        import time
        start_time = time.time()
        
        # Parse 50 prodotti
        test_products = client.get_products(limit=50)
        
        end_time = time.time()
        duration = end_time - start_time
        
        print(f"   ✅ Parsing 50 prodotti in {duration:.2f} secondi")
        print(f"   📈 Velocità: {len(test_products)/duration:.1f} prodotti/secondo")
        
        results['tests']['performance'] = {
            'success': True,
            'products_count': len(test_products),
            'duration_seconds': round(duration, 2),
            'products_per_second': round(len(test_products)/duration, 1)
        }
        
    except Exception as e:
        print(f"   ❌ Errore test performance: {e}")
        results['tests']['performance'] = {'success': False, 'error': str(e)}
    
    return results

def main():
    results = test_bic_system()
    
    # Salva risultati
    with open('test_bic_results.json', 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    
    print(f"\n📁 Risultati salvati in: test_bic_results.json")
    
    # Riepilogo
    print(f"\n📊 RIEPILOGO TEST:")
    total_tests = len(results['tests'])
    passed_tests = sum(1 for test in results['tests'].values() if test['success'])
    
    print(f"   ✅ Test superati: {passed_tests}/{total_tests}")
    print(f"   ❌ Test falliti: {total_tests - passed_tests}/{total_tests}")
    
    if passed_tests == total_tests:
        print(f"\n🎉 TUTTI I TEST SUPERATI! Sistema BIC pronto!")
    else:
        print(f"\n⚠️ Alcuni test sono falliti. Controlla i dettagli nel file JSON.")
    
    print(f"\n🚀 Prossimi passi:")
    print(f"   1. Crea migrazione: python manage.py makemigrations suppliers")
    print(f"   2. Applica migrazione: python manage.py migrate")
    print(f"   3. Carica fixture: python manage.py loaddata suppliers/fixtures/bic_supplier.json")
    print(f"   4. Test sincronizzazione completa")

if __name__ == '__main__':
    main()
