#!/usr/bin/env python
"""
Script per analizzare le categorie negli XML MKTO
"""
import os
import sys
import django
from pathlib import Path
from collections import Counter

# Setup Django
BASE_DIR = Path(__file__).resolve().parent
sys.path.append(str(BASE_DIR))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'hotel_sync.settings')

try:
    django.setup()
except Exception as e:
    print(f"❌ Errore setup Django: {e}")
    sys.exit(1)

from suppliers.models import Supplier
from suppliers.clients.factory import SupplierClientFactory
import json
from datetime import datetime

def main():
    print("🔍 ANALISI CATEGORIE MKTO")
    print("=" * 50)
    
    try:
        # Recupera fornitore MKTO
        mkto = Supplier.objects.get(code='MKTO')
        client = SupplierClientFactory.create_client(mkto)
        
        print(f"📁 Analizzando file XML in: {mkto.xml_path}")
        
        # Analizza TUTTI i prodotti per integrazione completa
        print(f"\n📦 Recupero TUTTI i prodotti per analisi completa...")
        print(f"   ⏳ Questo potrebbe richiedere alcuni minuti...")
        products = client.get_products(force_refresh=True)
        
        print(f"✅ Prodotti analizzati: {len(products)}")
        
        # Contatori per analisi
        all_categories = []
        category_levels = {1: [], 2: [], 3: [], 4: [], 5: []}
        products_with_categories = 0
        
        print(f"\n🔍 Analisi categorie...")
        
        for product in products:
            categories = product.get('categories', [])
            
            if categories:
                products_with_categories += 1
                
                # Aggiungi tutte le categorie alla lista
                for category in categories:
                    if category and category.strip():
                        all_categories.append(category.strip())
            
            # Analizza anche i dati raw per struttura XML
            raw_data = product.get('raw_data', {})
            if 'categories' in raw_data:
                cat_data = raw_data['categories']
                for i in range(1, 6):
                    name_key = f'category_name_{i}'
                    if cat_data.get(name_key):
                        category_levels[i].append(cat_data[name_key])
        
        # Statistiche generali
        print(f"\n📊 STATISTICHE CATEGORIE:")
        print(f"   📦 Prodotti con categorie: {products_with_categories}/{len(products)} ({products_with_categories/len(products)*100:.1f}%)")
        print(f"   🏷️ Categorie totali trovate: {len(all_categories)}")
        print(f"   🎯 Categorie uniche: {len(set(all_categories))}")
        
        # Analisi per livello
        print(f"\n📋 CATEGORIE PER LIVELLO:")
        for level in range(1, 6):
            categories = category_levels[level]
            unique_categories = set(categories)
            if unique_categories:
                print(f"   Livello {level}: {len(unique_categories)} categorie uniche")
                
                # Mostra le più comuni
                counter = Counter(categories)
                most_common = counter.most_common(5)
                for category, count in most_common:
                    print(f"      • {category} ({count} prodotti)")
        
        # Top categorie generali
        print(f"\n🏆 TOP 10 CATEGORIE PIÙ COMUNI:")
        category_counter = Counter(all_categories)
        for i, (category, count) in enumerate(category_counter.most_common(10), 1):
            print(f"   {i:2}. {category} ({count} prodotti)")
        
        # Esempi di struttura gerarchica
        print(f"\n🌳 ESEMPI STRUTTURA GERARCHICA:")
        hierarchy_examples = []
        
        for product in products[:10]:  # Primi 10 prodotti
            raw_data = product.get('raw_data', {})
            if 'categories' in raw_data:
                cat_data = raw_data['categories']
                hierarchy = []
                
                for i in range(1, 6):
                    name_key = f'category_name_{i}'
                    if cat_data.get(name_key):
                        hierarchy.append(cat_data[name_key])
                
                if hierarchy:
                    hierarchy_path = ' > '.join(hierarchy)
                    if hierarchy_path not in hierarchy_examples:
                        hierarchy_examples.append(hierarchy_path)
                        if len(hierarchy_examples) >= 5:
                            break
        
        for i, example in enumerate(hierarchy_examples, 1):
            print(f"   {i}. {example}")
        
        # Analisi mapping necessario
        print(f"\n💡 ANALISI MAPPING:")
        unique_categories = set(all_categories)
        
        # Categorie che potrebbero essere per hotel
        hotel_related = []
        for cat in unique_categories:
            cat_lower = cat.lower()
            if any(keyword in cat_lower for keyword in ['hotel', 'casa', 'cucina', 'bagno', 'camera', 'ufficio', 'pulizia', 'tessile']):
                hotel_related.append(cat)
        
        if hotel_related:
            print(f"   🏨 Categorie potenzialmente hotel-related ({len(hotel_related)}):")
            for cat in sorted(hotel_related)[:10]:
                print(f"      • {cat}")
        
        # Suggerimenti mapping
        print(f"\n🎯 RACCOMANDAZIONI:")
        print(f"   • Creare mapping categorie MKTO → Categorie WooCommerce")
        print(f"   • Utilizzare gerarchia a {max(len(cats) for cats in category_levels.values() if cats)} livelli")
        print(f"   • Focus su categorie hotel-related per il cliente")
        
        # Salva risultati per integrazione
        print(f"\n💾 Salvataggio risultati analisi...")
        save_category_analysis(unique_categories, hierarchy_examples, category_counter)
        
        print(f"\n✅ ANALISI COMPLETA TERMINATA!")
        print(f"   📁 Risultati salvati in: mkto_categories_analysis.json")
        print(f"   📊 Prodotti analizzati: {len(products)}")
        print(f"   🏷️ Categorie uniche: {len(unique_categories)}")
        print(f"\n💡 Prossimi passi:")
        print(f"   1. Creare mapping categorie MKTO → WooCommerce")
        print(f"   2. Implementare creazione automatica categorie")
        print(f"   3. Testare sincronizzazione con categorie")
        
    except Exception as e:
        print(f"❌ Errore: {e}")
        import traceback
        traceback.print_exc()

def save_category_analysis(unique_categories, hierarchy_examples, category_counter):
    """Salva i risultati dell'analisi categorie"""
    try:
        analysis_data = {
            'timestamp': datetime.now().isoformat(),
            'total_unique_categories': len(unique_categories),
            'categories_list': sorted(list(unique_categories)),
            'hierarchy_examples': hierarchy_examples,
            'top_categories': [
                {'name': cat, 'count': count} 
                for cat, count in category_counter.most_common(20)
            ],
            'hotel_related_categories': [
                cat for cat in unique_categories 
                if any(keyword in cat.lower() for keyword in [
                    'hotel', 'casa', 'cucina', 'bagno', 'camera', 'ufficio', 
                    'pulizia', 'tessile', 'tovaglia', 'asciugamano', 'lenzuol',
                    'sapone', 'shampoo', 'amenity', 'reception', 'ristorante'
                ])
            ],
            'suggested_woocommerce_mapping': generate_woocommerce_mapping(unique_categories)
        }
        
        with open('mkto_categories_analysis.json', 'w', encoding='utf-8') as f:
            json.dump(analysis_data, f, indent=2, ensure_ascii=False)
            
    except Exception as e:
        print(f"⚠️ Errore salvataggio: {e}")

def generate_woocommerce_mapping(categories):
    """Genera mapping 1:1 mantenendo le categorie MKTO originali"""
    mapping = {}
    
    # Mapping diretto: ogni categoria MKTO diventa categoria WooCommerce identica
    for category in categories:
        # Usa la categoria MKTO esatta come nome WooCommerce
        # Pulisce solo caratteri problematici per WooCommerce
        clean_category = category.replace('&', 'e').replace('/', ' - ')
        mapping[category] = clean_category
    
    return mapping

if __name__ == '__main__':
    main()
