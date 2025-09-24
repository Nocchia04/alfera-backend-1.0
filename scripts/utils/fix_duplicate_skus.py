#!/usr/bin/env python
"""
Script per risolvere i duplicati SKU nelle varianti
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

from products.models import Product, ProductVariant
from suppliers.models import Supplier
from django.db import transaction

def main():
    print("🔧 FIX DUPLICATI SKU VARIANTI")
    print("=" * 50)
    
    try:
        mkto = Supplier.objects.get(code='MKTO')
        
        # 1. Trova varianti con SKU vuoti
        print("\n1️⃣ Ricerca varianti con SKU vuoti...")
        empty_sku_variants = ProductVariant.objects.filter(
            product__supplier=mkto,
            sku__in=['', None]
        )
        
        print(f"   📊 Varianti con SKU vuoti: {empty_sku_variants.count()}")
        
        # 2. Trova SKU duplicati
        print("\n2️⃣ Ricerca SKU duplicati...")
        from django.db.models import Count
        
        duplicate_skus = ProductVariant.objects.filter(
            product__supplier=mkto
        ).values('sku').annotate(
            count=Count('sku')
        ).filter(count__gt=1)
        
        print(f"   📊 SKU duplicati: {duplicate_skus.count()}")
        
        # 3. Fix SKU vuoti
        print("\n3️⃣ Fix SKU vuoti...")
        fixed_empty = 0
        
        with transaction.atomic():
            for variant in empty_sku_variants:
                try:
                    # Genera nuovo SKU
                    new_sku = f"MAK_{variant.product.supplier_ref}"
                    if variant.color:
                        new_sku += f"_{variant.color.replace('/', '').replace(' ', '')}"
                    if variant.size and variant.size != 'S/T':
                        new_sku += f"_{variant.size.replace('/', '').replace(' ', '')}"
                    
                    # Verifica unicità
                    counter = 1
                    original_sku = new_sku
                    while ProductVariant.objects.filter(sku=new_sku).exists():
                        new_sku = f"{original_sku}_{counter}"
                        counter += 1
                    
                    variant.sku = new_sku
                    variant.save()
                    fixed_empty += 1
                    
                    if fixed_empty % 10 == 0:
                        print(f"      Processati {fixed_empty}...")
                        
                except Exception as e:
                    print(f"      ❌ Errore variante {variant.id}: {e}")
        
        print(f"   ✅ SKU vuoti risolti: {fixed_empty}")
        
        # 4. Fix duplicati
        print("\n4️⃣ Fix SKU duplicati...")
        fixed_duplicates = 0
        
        for dup_info in duplicate_skus:
            sku = dup_info['sku']
            if not sku:  # Skip empty SKUs (already fixed)
                continue
                
            duplicates = ProductVariant.objects.filter(
                product__supplier=mkto,
                sku=sku
            ).order_by('id')
            
            # Mantieni il primo, rinomina gli altri
            for i, variant in enumerate(duplicates):
                if i == 0:
                    continue  # Mantieni il primo
                
                try:
                    # Genera nuovo SKU unico
                    new_sku = f"{sku}_{variant.product.id}_{i}"
                    
                    # Verifica unicità
                    counter = 1
                    original_new_sku = new_sku
                    while ProductVariant.objects.filter(sku=new_sku).exists():
                        new_sku = f"{original_new_sku}_{counter}"
                        counter += 1
                    
                    variant.sku = new_sku
                    variant.save()
                    fixed_duplicates += 1
                    
                except Exception as e:
                    print(f"      ❌ Errore duplicato {variant.id}: {e}")
        
        print(f"   ✅ SKU duplicati risolti: {fixed_duplicates}")
        
        # 5. Statistiche finali
        print("\n5️⃣ Statistiche finali...")
        
        total_variants = ProductVariant.objects.filter(product__supplier=mkto).count()
        empty_skus_remaining = ProductVariant.objects.filter(
            product__supplier=mkto,
            sku__in=['', None]
        ).count()
        
        duplicates_remaining = ProductVariant.objects.filter(
            product__supplier=mkto
        ).values('sku').annotate(
            count=Count('sku')
        ).filter(count__gt=1).count()
        
        print(f"   📊 Varianti totali MKTO: {total_variants}")
        print(f"   📊 SKU vuoti rimanenti: {empty_skus_remaining}")
        print(f"   📊 SKU duplicati rimanenti: {duplicates_remaining}")
        
        if empty_skus_remaining == 0 and duplicates_remaining == 0:
            print(f"\n✅ TUTTI I DUPLICATI RISOLTI!")
            print(f"💡 Ora puoi eseguire di nuovo la sincronizzazione:")
            print(f"   python sync_mkto_complete.py")
        else:
            print(f"\n⚠️ Alcuni problemi rimangono da risolvere")
            
    except Supplier.DoesNotExist:
        print(f"❌ Fornitore MKTO non trovato!")
    except Exception as e:
        print(f"❌ Errore: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    main()
