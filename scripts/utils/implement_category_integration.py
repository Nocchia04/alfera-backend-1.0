#!/usr/bin/env python
"""
Script per implementare l'integrazione completa delle categorie MKTO
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

from products.models import Category
from woocommerce_integration.client import WooCommerceClient
from django.db import transaction
import logging

logger = logging.getLogger('sync')

def load_category_analysis():
    """Carica i risultati dell'analisi categorie"""
    try:
        with open('mkto_categories_analysis.json', 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        print("❌ File mkto_categories_analysis.json non trovato!")
        print("   Esegui prima: python analyze_mkto_categories.py")
        return None
    except Exception as e:
        print(f"❌ Errore caricamento analisi: {e}")
        return None

def create_woocommerce_categories(wc_client, categories_mapping):
    """Crea le categorie MKTO originali su WooCommerce"""
    print(f"\n🏗️ Creazione categorie MKTO originali su WooCommerce...")
    
    created_categories = {}
    
    # Crea ogni categoria MKTO come categoria WooCommerce semplice
    for mkto_cat, woo_cat in categories_mapping.items():
        try:
            # Verifica se esiste già
            existing = wc_client.get_category_by_name(woo_cat)
            if existing:
                created_categories[mkto_cat] = existing['id']
                print(f"   ✅ Categoria esistente: {woo_cat} (ID: {existing['id']})")
            else:
                # Crea nuova categoria
                cat = wc_client.create_category({
                    'name': woo_cat,
                    'description': f'Categoria MKTO: {mkto_cat}',
                    'parent': 0  # Tutte le categorie al livello root per ora
                })
                if cat:
                    created_categories[mkto_cat] = cat['id']
                    print(f"   ✅ Creata categoria: {woo_cat} (ID: {cat['id']})")
                else:
                    print(f"   ❌ Errore creazione categoria: {woo_cat}")
        except Exception as e:
            print(f"   ❌ Errore categoria {woo_cat}: {e}")
    
    return created_categories

def sync_categories_to_db(categories_mapping, woocommerce_categories):
    """Sincronizza le categorie MKTO nel database Django"""
    print(f"\n💾 Sincronizzazione categorie MKTO nel database...")
    
    with transaction.atomic():
        for mkto_cat, woo_cat in categories_mapping.items():
            woo_id = woocommerce_categories.get(mkto_cat)
            
            # Genera slug pulito
            slug = woo_cat.lower().replace(' ', '-').replace('&', 'e').replace('/', '-')[:50]
            
            # Crea o aggiorna categoria Django
            category, created = Category.objects.get_or_create(
                name=woo_cat,  # Usa il nome WooCommerce (che è uguale a MKTO ma pulito)
                defaults={
                    'parent': None,  # Nessuna gerarchia per ora
                    'woocommerce_id': woo_id,
                    'mkto_mapping': mkto_cat,
                    'slug': slug
                }
            )
            
            if not created and woo_id:
                category.woocommerce_id = woo_id
                category.mkto_mapping = mkto_cat
                category.save()
            
            action = "Creata" if created else "Aggiornata"
            print(f"   ✅ {action} categoria DB: {woo_cat} (MKTO: {mkto_cat})")

def update_sync_service():
    """Aggiorna il servizio di sincronizzazione per usare le categorie"""
    print(f"\n🔄 Aggiornamento servizio sincronizzazione...")
    
    # Crea patch per sync_service.py
    patch_content = '''
# PATCH: Aggiunta gestione categorie MKTO
def _assign_product_category(self, product, mkto_categories):
    """Assegna categoria al prodotto basata sul mapping MKTO"""
    if not mkto_categories:
        return
    
    # Prendi la prima categoria valida
    mkto_category = mkto_categories[0] if isinstance(mkto_categories, list) else mkto_categories
    
    # Cerca categoria mappata
    from products.models import Category
    category = Category.objects.filter(mkto_mapping=mkto_category).first()
    
    if category:
        product.category = category
        product.save()
        logger.info(f"Categoria assegnata al prodotto {product.sku}: {category.name}")
    else:
        logger.warning(f"Categoria MKTO non mappata: {mkto_category}")
'''
    
    with open('sync_service_category_patch.py', 'w', encoding='utf-8') as f:
        f.write(patch_content)
    
    print(f"   ✅ Creato patch per sync_service.py")
    print(f"   📁 File: sync_service_category_patch.py")
    print(f"   💡 Integra manualmente nel sync_service.py")

def main():
    print("🚀 IMPLEMENTAZIONE INTEGRAZIONE CATEGORIE MKTO")
    print("=" * 60)
    
    # Carica analisi categorie
    analysis = load_category_analysis()
    if not analysis:
        return
    
    print(f"📊 Analisi caricata:")
    print(f"   🏷️ Categorie uniche: {analysis['total_unique_categories']}")
    print(f"   🏨 Categorie hotel-related: {len(analysis['hotel_related_categories'])}")
    
    # Inizializza client WooCommerce
    try:
        wc_client = WooCommerceClient()
        print(f"✅ Client WooCommerce inizializzato")
    except Exception as e:
        print(f"❌ Errore inizializzazione WooCommerce: {e}")
        return
    
    # Crea categorie su WooCommerce
    categories_mapping = analysis['suggested_woocommerce_mapping']
    woocommerce_categories = create_woocommerce_categories(wc_client, categories_mapping)
    
    # Sincronizza nel database Django
    sync_categories_to_db(categories_mapping, woocommerce_categories)
    
    # Aggiorna servizio sincronizzazione
    update_sync_service()
    
    # Salva mapping finale
    final_mapping = {
        'timestamp': analysis['timestamp'],
        'categories_created': len(woocommerce_categories),
        'woocommerce_mapping': woocommerce_categories,
        'mkto_to_woocommerce': categories_mapping
    }
    
    with open('category_integration_results.json', 'w', encoding='utf-8') as f:
        json.dump(final_mapping, f, indent=2, ensure_ascii=False)
    
    print(f"\n✅ INTEGRAZIONE CATEGORIE COMPLETATA!")
    print(f"   📁 Risultati salvati in: category_integration_results.json")
    print(f"   🏗️ Categorie create su WooCommerce: {len(woocommerce_categories)}")
    print(f"   💾 Categorie sincronizzate nel DB: {len(categories_mapping)}")
    
    print(f"\n🎯 PROSSIMI PASSI:")
    print(f"   1. Integra il patch nel sync_service.py")
    print(f"   2. Testa sincronizzazione con categorie")
    print(f"   3. Verifica categorie su WooCommerce")

if __name__ == '__main__':
    main()
