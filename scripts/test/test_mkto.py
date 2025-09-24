#!/usr/bin/env python
"""
Script di test per il parser MKTO
Esegui con: python test_mkto.py
"""
import os
import sys
import django
from pathlib import Path

# Setup Django
BASE_DIR = Path(__file__).resolve().parent.parent.parent
sys.path.append(str(BASE_DIR))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'hotel_sync.settings')

try:
    django.setup()
except Exception as e:
    print(f"❌ Errore setup Django: {e}")
    sys.exit(1)

# Imports Django
from suppliers.models import Supplier
from suppliers.clients.factory import SupplierClientFactory
from django.core.management import call_command
import json
from datetime import datetime


class MKTOTester:
    """Tester per MKTO parser"""
    
    def __init__(self):
        self.results = {
            'database_setup': False,
            'supplier_created': False,
            'client_created': False,
            'files_found': {},
            'parsing_tests': {},
            'errors': []
        }
    
    def run_all_tests(self):
        """Esegue tutti i test"""
        print("🚀 AVVIO TEST MKTO PARSER")
        print("=" * 50)
        
        try:
            self.test_database_setup()
            self.test_supplier_creation()
            self.test_client_creation()
            self.test_file_detection()
            self.test_parsing()
            self.print_summary()
            
        except KeyboardInterrupt:
            print("\n⚠️ Test interrotti dall'utente")
        except Exception as e:
            print(f"\n❌ Errore generale: {e}")
            self.results['errors'].append(str(e))
    
    def test_database_setup(self):
        """Test setup database"""
        print("\n📊 Test 1: Setup Database")
        
        try:
            # Verifica migrazioni
            from django.db import connection
            with connection.cursor() as cursor:
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
                tables = [row[0] for row in cursor.fetchall()]
            
            required_tables = ['suppliers_supplier', 'products_product', 'sync_synclog']
            missing_tables = [t for t in required_tables if t not in tables]
            
            if missing_tables:
                print(f"⚠️ Tabelle mancanti: {missing_tables}")
                print("   Eseguendo migrazioni...")
                call_command('migrate', verbosity=0)
                print("   ✅ Migrazioni completate")
            else:
                print("   ✅ Database già configurato")
            
            self.results['database_setup'] = True
            
        except Exception as e:
            print(f"   ❌ Errore database: {e}")
            self.results['errors'].append(f"Database: {e}")
    
    def test_supplier_creation(self):
        """Test creazione fornitore MKTO"""
        print("\n🏭 Test 2: Creazione Fornitore MKTO")
        
        try:
            # Verifica se esiste già
            mkto_supplier = Supplier.objects.filter(code='MKTO').first()
            
            if mkto_supplier:
                print(f"   ✅ Fornitore MKTO già esistente: {mkto_supplier.name}")
            else:
                # Crea fornitore
                mkto_supplier = Supplier.objects.create(
                    name="MKTO Web Service",
                    code="MKTO",
                    supplier_type="MAKITO",
                    is_active=True,
                    xml_path=str(BASE_DIR),  # Directory corrente
                )
                print(f"   ✅ Fornitore MKTO creato: {mkto_supplier.name}")
            
            print(f"   📁 Path XML: {mkto_supplier.xml_path}")
            print(f"   🔧 Configurato: {mkto_supplier.is_api_configured}")
            
            self.mkto_supplier = mkto_supplier
            self.results['supplier_created'] = True
            
        except Exception as e:
            print(f"   ❌ Errore creazione fornitore: {e}")
            self.results['errors'].append(f"Supplier: {e}")
    
    def test_client_creation(self):
        """Test creazione client"""
        print("\n🔌 Test 3: Creazione Client MKTO")
        
        try:
            if not hasattr(self, 'mkto_supplier'):
                raise Exception("Fornitore MKTO non disponibile")
            
            client = SupplierClientFactory.create_client(self.mkto_supplier)
            print(f"   ✅ Client creato: {type(client).__name__}")
            
            # Test connessione
            connection_ok = client.test_connection()
            print(f"   🔗 Test connessione: {'✅ OK' if connection_ok else '❌ FAIL'}")
            
            self.client = client
            self.results['client_created'] = True
            
        except Exception as e:
            print(f"   ❌ Errore creazione client: {e}")
            self.results['errors'].append(f"Client: {e}")
    
    def test_file_detection(self):
        """Test rilevamento file XML"""
        print("\n📁 Test 4: Rilevamento File XML")
        
        try:
            if not hasattr(self, 'client'):
                raise Exception("Client non disponibile")
            
            file_info = self.client.get_file_info()
            
            for file_type, info in file_info.items():
                status = "✅" if info['exists'] else "❌"
                size_mb = info['size'] / (1024*1024) if info['size'] else 0
                
                print(f"   {status} {file_type}: {info['filename']}")
                if info['exists']:
                    print(f"      📏 Dimensione: {size_mb:.2f} MB")
                    if info['last_modified']:
                        mod_time = datetime.fromtimestamp(info['last_modified'])
                        print(f"      📅 Modificato: {mod_time.strftime('%Y-%m-%d %H:%M:%S')}")
                
                self.results['files_found'][file_type] = info['exists']
            
        except Exception as e:
            print(f"   ❌ Errore rilevamento file: {e}")
            self.results['errors'].append(f"Files: {e}")
    
    def test_parsing(self):
        """Test parsing dati"""
        print("\n🔄 Test 5: Parsing Dati XML")
        
        if not hasattr(self, 'client'):
            print("   ❌ Client non disponibile")
            return
        
        # Test parsing prodotti
        self.test_products_parsing()
        
        # Test parsing stock
        self.test_stock_parsing()
        
        # Test parsing prezzi
        self.test_prices_parsing()
        
        # Test parsing dati stampa
        self.test_print_data_parsing()
    
    def test_products_parsing(self):
        """Test parsing prodotti"""
        print("\n   🛍️ Test Prodotti (primi 3):")
        
        try:
            products = self.client.get_products(limit=3)
            
            print(f"      ✅ Prodotti recuperati: {len(products)}")
            
            for i, product in enumerate(products, 1):
                print(f"      📦 Prodotto {i}:")
                print(f"         Ref: {product.get('supplier_ref', 'N/A')}")
                print(f"         Nome: {product.get('name', 'N/A')[:50]}...")
                print(f"         Tipo: {product.get('type', 'N/A')}")
                print(f"         Varianti: {len(product.get('variants', []))}")
                print(f"         Immagini: {len(product.get('images', []))}")
                print(f"         Stampabile: {product.get('is_printable', False)}")
            
            self.results['parsing_tests']['products'] = {
                'success': True,
                'count': len(products)
            }
            
        except Exception as e:
            print(f"      ❌ Errore parsing prodotti: {e}")
            self.results['parsing_tests']['products'] = {
                'success': False,
                'error': str(e)
            }
    
    def test_stock_parsing(self):
        """Test parsing stock"""
        print("\n   📦 Test Stock (primi 5 record):")
        
        try:
            stock_data = self.client.get_stock(limit=5)
            
            print(f"      ✅ Record stock recuperati: {len(stock_data)}")
            
            for i, stock in enumerate(stock_data[:3], 1):  # Mostra solo primi 3
                print(f"      📊 Stock {i}:")
                print(f"         SKU: {stock.get('sku', 'N/A')}")
                print(f"         Quantità: {stock.get('stock_quantity', 0)}")
                print(f"         Disponibilità: {stock.get('availability_status', 'N/A')}")
            
            self.results['parsing_tests']['stock'] = {
                'success': True,
                'count': len(stock_data)
            }
            
        except Exception as e:
            print(f"      ❌ Errore parsing stock: {e}")
            self.results['parsing_tests']['stock'] = {
                'success': False,
                'error': str(e)
            }
    
    def test_prices_parsing(self):
        """Test parsing prezzi"""
        print("\n   💰 Test Prezzi (primi 3):")
        
        try:
            prices = self.client.get_prices(limit=3)
            
            print(f"      ✅ Prezzi recuperati: {len(prices)}")
            
            for i, price in enumerate(prices, 1):
                print(f"      💵 Prezzo {i}:")
                print(f"         Ref: {price.get('supplier_ref', 'N/A')}")
                print(f"         Nome: {price.get('name', 'N/A')[:30]}...")
                print(f"         Fasce: {len(price.get('price_ranges', []))}")
                
                # Mostra prima fascia prezzo
                ranges = price.get('price_ranges', [])
                if ranges:
                    first_range = ranges[0]
                    print(f"         Prima fascia: €{first_range.get('price', 0)} (min: {first_range.get('min_quantity', 0)})")
            
            self.results['parsing_tests']['prices'] = {
                'success': True,
                'count': len(prices)
            }
            
        except Exception as e:
            print(f"      ❌ Errore parsing prezzi: {e}")
            self.results['parsing_tests']['prices'] = {
                'success': False,
                'error': str(e)
            }
    
    def test_print_data_parsing(self):
        """Test parsing dati stampa"""
        print("\n   🎨 Test Dati Stampa (primi 2):")
        
        try:
            print_data = self.client.get_print_data(limit=2)
            
            print(f"      ✅ Dati stampa recuperati: {len(print_data)}")
            
            for i, pdata in enumerate(print_data, 1):
                print(f"      🖨️ Stampa {i}:")
                print(f"         Ref: {pdata.get('supplier_ref', 'N/A')}")
                print(f"         Nome: {pdata.get('name', 'N/A')[:30]}...")
                print(f"         Job stampa: {len(pdata.get('print_jobs', []))}")
                
                # Mostra primo job
                jobs = pdata.get('print_jobs', [])
                if jobs:
                    first_job = jobs[0]
                    print(f"         Prima tecnica: {first_job.get('technique_name', 'N/A')}")
                    print(f"         Aree stampa: {len(first_job.get('areas', []))}")
            
            self.results['parsing_tests']['print_data'] = {
                'success': True,
                'count': len(print_data)
            }
            
        except Exception as e:
            print(f"      ❌ Errore parsing dati stampa: {e}")
            self.results['parsing_tests']['print_data'] = {
                'success': False,
                'error': str(e)
            }
    
    def print_summary(self):
        """Stampa riassunto test"""
        print("\n" + "=" * 50)
        print("📋 RIASSUNTO TEST MKTO")
        print("=" * 50)
        
        # Status generale
        total_tests = 5
        passed_tests = sum([
            self.results['database_setup'],
            self.results['supplier_created'],
            self.results['client_created'],
            any(self.results['files_found'].values()),
            any(test.get('success', False) for test in self.results['parsing_tests'].values())
        ])
        
        print(f"✅ Test superati: {passed_tests}/{total_tests}")
        
        # File trovati
        files_found = sum(self.results['files_found'].values())
        total_files = len(self.results['files_found'])
        print(f"📁 File XML trovati: {files_found}/{total_files}")
        
        # Parsing results
        print("\n🔄 Risultati Parsing:")
        for test_name, result in self.results['parsing_tests'].items():
            if result.get('success'):
                count = result.get('count', 0)
                print(f"   ✅ {test_name}: {count} record")
            else:
                print(f"   ❌ {test_name}: {result.get('error', 'Errore sconosciuto')}")
        
        # Errori
        if self.results['errors']:
            print(f"\n❌ Errori riscontrati: {len(self.results['errors'])}")
            for error in self.results['errors']:
                print(f"   • {error}")
        else:
            print(f"\n✅ Nessun errore critico riscontrato")
        
        # Raccomandazioni
        print(f"\n💡 Raccomandazioni:")
        
        if not all(self.results['files_found'].values()):
            missing_files = [k for k, v in self.results['files_found'].items() if not v]
            print(f"   • File XML mancanti: {', '.join(missing_files)}")
            print(f"   • Assicurati che i file XML siano nella directory: {BASE_DIR}")
        
        if passed_tests == total_tests and files_found == total_files:
            print(f"   🚀 Sistema pronto per sincronizzazione completa!")
            print(f"   • Esegui: python manage.py sync --supplier MKTO --dry-run")
            print(f"   • Poi: python manage.py sync --supplier MKTO")
        else:
            print(f"   ⚠️ Risolvi i problemi sopra prima della sincronizzazione")
        
        # Salva risultati
        self.save_results()
    
    def save_results(self):
        """Salva risultati test in file JSON"""
        try:
            results_file = BASE_DIR / 'test_mkto_results.json'
            
            # Prepara dati per JSON
            json_results = self.results.copy()
            json_results['timestamp'] = datetime.now().isoformat()
            json_results['base_dir'] = str(BASE_DIR)
            
            with open(results_file, 'w', encoding='utf-8') as f:
                json.dump(json_results, f, indent=2, ensure_ascii=False)
            
            print(f"\n💾 Risultati salvati in: {results_file}")
            
        except Exception as e:
            print(f"\n⚠️ Impossibile salvare risultati: {e}")


def main():
    """Funzione principale"""
    print("🔧 MKTO Parser Test Suite")
    print(f"📂 Directory: {BASE_DIR}")
    print(f"⏰ Inizio: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    tester = MKTOTester()
    tester.run_all_tests()
    
    print(f"\n⏰ Fine: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("🏁 Test completato!")


if __name__ == '__main__':
    main()
