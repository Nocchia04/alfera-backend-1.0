#!/usr/bin/env python
"""
🚀 HOTEL SYNC - Script Master di Sincronizzazione
Orchestratore principale per sincronizzazione fornitori
"""
import os
import sys
import argparse
from pathlib import Path

# Setup Django
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(BASE_DIR))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'hotel_sync.settings')

try:
    import django
    django.setup()
except Exception as e:
    print(f"❌ Errore setup Django: {e}")
    sys.exit(1)

def main():
    print("🚀 HOTEL SYNC - Sistema di Sincronizzazione Fornitori")
    print("=" * 60)
    
    parser = argparse.ArgumentParser(
        description="Sistema di sincronizzazione fornitori hotel",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Esempi d'uso:

  # Sincronizzazione MKTO completa
  python scripts/run_sync.py --supplier MKTO --full

  # Sincronizzazione BIC con solo 10 prodotti (demo)
  python scripts/run_sync.py --supplier BIC --limit 10

  # Sincronizzazione BIC con immagini
  python scripts/run_sync.py --supplier BIC --images

  # Test tutti i fornitori
  python scripts/run_sync.py --test-all

  # Solo categorie MKTO
  python scripts/run_sync.py --categories-only
        """
    )
    
    parser.add_argument('--supplier', choices=['MKTO', 'BIC', 'ALL'], 
                       help='Fornitore da sincronizzare')
    parser.add_argument('--full', action='store_true', 
                       help='Sincronizzazione completa (tutti i prodotti)')
    parser.add_argument('--limit', type=int, 
                       help='Limita numero prodotti (per demo/test)')
    parser.add_argument('--images', action='store_true', 
                       help='Include upload immagini reali')
    parser.add_argument('--no-woocommerce', action='store_true', 
                       help='Solo DB locale, salta WooCommerce')
    parser.add_argument('--test-all', action='store_true', 
                       help='Testa tutti i fornitori')
    parser.add_argument('--categories-only', action='store_true', 
                       help='Solo analisi e creazione categorie MKTO')
    
    args = parser.parse_args()
    
    if args.test_all:
        run_all_tests()
    elif args.categories_only:
        run_categories_setup()
    elif args.supplier:
        run_supplier_sync(args)
    else:
        print("❓ Cosa vuoi fare?")
        print("   1. Sincronizzazione MKTO completa")
        print("   2. Sincronizzazione BIC completa") 
        print("   3. Sincronizzazione BIC con immagini")
        print("   4. Demo MKTO (10 prodotti)")
        print("   5. Demo BIC (10 prodotti)")
        print("   6. Test tutti i fornitori")
        print("   7. Setup categorie MKTO")
        
        choice = input("\nScegli (1-7): ").strip()
        
        if choice == '1':
            run_mkto_full()
        elif choice == '2':
            run_bic_full()
        elif choice == '3':
            run_bic_with_images()
        elif choice == '4':
            run_mkto_demo()
        elif choice == '5':
            run_bic_demo()
        elif choice == '6':
            run_all_tests()
        elif choice == '7':
            run_categories_setup()
        else:
            print("❌ Scelta non valida")

def run_supplier_sync(args):
    """Esegue sincronizzazione fornitore specifico"""
    if args.supplier == 'MKTO':
        if args.images:
            print("⚠️ MKTO non supporta upload immagini separate")
        run_mkto_sync(args.limit, args.no_woocommerce)
    elif args.supplier == 'BIC':
        if args.images:
            run_bic_with_images()
        else:
            run_bic_sync(args.limit, args.no_woocommerce)
    elif args.supplier == 'ALL':
        print("🔄 Sincronizzazione tutti i fornitori...")
        run_mkto_sync(args.limit, args.no_woocommerce)
        if not args.images:
            run_bic_sync(args.limit, args.no_woocommerce)
        else:
            run_bic_with_images()

def run_mkto_sync(limit=None, no_woocommerce=False):
    """Sincronizzazione MKTO"""
    print(f"\n🔄 SINCRONIZZAZIONE MKTO")
    print("-" * 30)
    
    os.chdir(BASE_DIR)
    cmd = f"python scripts/sync/sync_mkto_complete.py"
    if limit:
        cmd += f" --limit {limit}"
    if no_woocommerce:
        cmd += " --no-woocommerce"
    
    os.system(cmd)

def run_bic_sync(limit=None, no_woocommerce=False):
    """Sincronizzazione BIC senza immagini"""
    print(f"\n🔄 SINCRONIZZAZIONE BIC")
    print("-" * 30)
    
    cmd = f"python scripts/sync/sync_bic_complete.py"
    if limit:
        cmd += f" --limit {limit}"
    if no_woocommerce:
        cmd += " --no-woocommerce"
    
    os.system(cmd)

def run_bic_with_images():
    """Sincronizzazione BIC con immagini"""
    print(f"\n🖼️ SINCRONIZZAZIONE BIC CON IMMAGINI")
    print("-" * 40)
    
    # Prima sincronizza prodotti
    os.system("python scripts/sync/sync_bic_complete.py")
    
    # Poi carica immagini
    print(f"\n📸 Caricamento immagini BIC...")
    os.system("python scripts/sync/host_bic_images.py")

def run_mkto_full():
    """MKTO completo"""
    run_mkto_sync()

def run_bic_full():
    """BIC completo"""
    run_bic_sync()

def run_mkto_demo():
    """MKTO demo 10 prodotti"""
    run_mkto_sync(limit=10)

def run_bic_demo():
    """BIC demo 10 prodotti"""  
    run_bic_sync(limit=10)

def run_all_tests():
    """Test tutti i fornitori"""
    print(f"\n🧪 TEST TUTTI I FORNITORI")
    print("=" * 40)
    
    print(f"\n📋 Test MKTO...")
    os.system("python scripts/test/test_mkto.py")
    
    print(f"\n📋 Test BIC...")
    os.system("python scripts/test/test_bic.py")

def run_categories_setup():
    """Setup categorie MKTO"""
    print(f"\n🏷️ SETUP CATEGORIE MKTO")
    print("-" * 30)
    
    print(f"📊 Analisi categorie...")
    os.system("python scripts/utils/analyze_mkto_categories.py")
    
    print(f"\n🔄 Integrazione categorie...")
    os.system("python scripts/utils/implement_category_integration.py")

if __name__ == '__main__':
    main()
