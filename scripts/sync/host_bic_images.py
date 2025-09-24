#!/usr/bin/env python
"""
Hosting temporaneo immagini BIC processate
"""
import os
import sys
import django
from pathlib import Path
import http.server
import socketserver
import threading
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
from woocommerce_integration.image_handler import ImageHandler
from products.models import Product
from suppliers.models import Supplier

def start_image_server():
    """Avvia server HTTP temporaneo per immagini"""
    
    # Directory per immagini
    images_dir = os.path.join(BASE_DIR, 'temp_bic_images')
    os.makedirs(images_dir, exist_ok=True)
    
    # Cambia directory
    os.chdir(images_dir)
    
    # Server HTTP semplice
    PORT = 8080
    Handler = http.server.SimpleHTTPRequestHandler
    
    with socketserver.TCPServer(("", PORT), Handler) as httpd:
        print(f"📡 Server immagini avviato su http://localhost:{PORT}")
        print(f"📁 Directory: {images_dir}")
        httpd.serve_forever()

def host_and_upload():
    """Processa, hosta e carica immagini"""
    
    print("🌐 HOSTING E UPLOAD IMMAGINI BIC")
    print("=" * 50)
    
    # Directory immagini temporanea
    images_dir = os.path.join(BASE_DIR, 'temp_bic_images')
    os.makedirs(images_dir, exist_ok=True)
    
    try:
        # 1. Processa e salva immagini
        bic_supplier = Supplier.objects.get(code='BIC')
        products_with_wc = Product.objects.filter(
            supplier=bic_supplier,
            woocommerce_id__gt=0
        )[:3]
        
        image_handler = ImageHandler()
        wc_client = WooCommerceClient()
        
        print("📷 PROCESSING IMMAGINI...")
        
        product_images = {}  # {product_id: [image_files]}
        
        for product in products_with_wc:
            print(f"\n🔄 Processing: {product.name}")
            
            # Recupera dati originali
            from suppliers.clients.factory import SupplierClientFactory
            client = SupplierClientFactory.create_client(bic_supplier)
            original_products = client.get_products(limit=200)
            
            original_product = None
            for orig in original_products:
                if orig.get('sku') == product.sku:
                    original_product = orig
                    break
            
            if not original_product:
                continue
            
            images = original_product.get('images', [])
            saved_images = []
            
            for i, img_url in enumerate(images):
                try:
                    # Download e processing
                    image_data = image_handler._download_image(img_url)
                    if not image_data:
                        continue
                    
                    formato = image_handler._detect_image_format(image_data)
                    if formato == 'PDF' or formato not in image_handler.supported_formats:
                        continue
                    
                    processed_data = image_handler._process_with_pil(image_data, f"{product.sku}_{i}")
                    if not processed_data:
                        continue
                    
                    # Salva file
                    filename = f"{product.sku}_{i}.jpg"
                    file_path = os.path.join(images_dir, filename)
                    
                    with open(file_path, 'wb') as f:
                        f.write(processed_data)
                    
                    saved_images.append(filename)
                    print(f"   ✅ Salvata: {filename}")
                    
                except Exception as e:
                    print(f"   ❌ Errore: {e}")
            
            if saved_images:
                product_images[product.woocommerce_id] = saved_images
        
        print(f"\n📊 Immagini processate per {len(product_images)} prodotti")
        
        # 2. Avvia server in background
        print(f"\n📡 Avvio server temporaneo...")
        
        def run_server():
            os.chdir(images_dir)
            PORT = 8080
            Handler = http.server.SimpleHTTPRequestHandler
            with socketserver.TCPServer(("", PORT), Handler) as httpd:
                httpd.serve_forever()
        
        server_thread = threading.Thread(target=run_server, daemon=True)
        server_thread.start()
        
        time.sleep(2)  # Aspetta avvio server
        
        print(f"✅ Server avviato su http://localhost:8080")
        
        # 3. Aggiorna prodotti WooCommerce
        print(f"\n🔄 AGGIORNAMENTO WOOCOMMERCE...")
        
        success_count = 0
        
        for wc_id, image_files in product_images.items():
            try:
                print(f"\n📦 Aggiornamento prodotto {wc_id}...")
                
                # Prepara URL immagini
                images_data = []
                for filename in image_files:
                    image_url = f"http://localhost:8080/{filename}"
                    images_data.append({
                        'src': image_url,
                        'alt': f'Immagine prodotto',
                        'name': filename
                    })
                    print(f"   🔗 {image_url}")
                
                # Aggiorna prodotto
                update_data = {'images': images_data}
                response = wc_client.wcapi.put(f"products/{wc_id}", update_data)
                
                if response.status_code == 200:
                    print(f"   ✅ Aggiornato!")
                    success_count += 1
                else:
                    print(f"   ❌ Errore: {response.status_code}")
                    print(f"      {response.text[:200]}")
                
            except Exception as e:
                print(f"   ❌ Errore prodotto {wc_id}: {e}")
        
        print(f"\n📊 RISULTATI:")
        print(f"   ✅ Prodotti aggiornati: {success_count}")
        print(f"   📡 Server attivo su: http://localhost:8080")
        print(f"   📁 Immagini in: {images_dir}")
        
        if success_count > 0:
            print(f"\n🎉 SUCCESSO! Immagini BIC caricate!")
            print(f"💡 Verifico che WooCommerce abbia scaricato le immagini...")
            
            # Aspetta che WooCommerce scarichi le immagini
            print(f"\n⏳ Attendo 30 secondi per il download da parte di WooCommerce...")
            for i in range(30, 0, -1):
                print(f"   ⏱️ {i} secondi rimanenti...", end='\r')
                time.sleep(1)
            
            print(f"\n🔍 Verifica finale prodotti...")
            
            # Verifica che le immagini siano state scaricate da WooCommerce
            images_downloaded = True
            for wc_id in product_images.keys():
                try:
                    response = wc_client.wcapi.get(f"products/{wc_id}")
                    if response.status_code == 200:
                        product_data = response.json()
                        images = product_data.get('images', [])
                        print(f"   📦 Prodotto {wc_id}: {len(images)} immagini")
                        
                        # Verifica se le immagini hanno URL WooCommerce (non più localhost)
                        for img in images:
                            img_src = img.get('src', '')
                            if 'localhost:8080' in img_src:
                                print(f"      ⏳ Immagine ancora in download: {img_src[-30:]}")
                                images_downloaded = False
                            else:
                                print(f"      ✅ Immagine scaricata da WC: {img_src[-30:]}")
                    else:
                        print(f"   ❌ Errore verifica prodotto {wc_id}")
                except Exception as e:
                    print(f"   ⚠️ Errore verifica {wc_id}: {e}")
            
            if images_downloaded:
                print(f"\n✅ Tutte le immagini sono state scaricate da WooCommerce!")
                print(f"🛑 Arresto automatico del server...")
            else:
                print(f"\n⏳ Alcune immagini sono ancora in download...")
                print(f"🔄 Attendo altri 30 secondi...")
                
                for i in range(30, 0, -1):
                    print(f"   ⏱️ {i} secondi rimanenti...", end='\r')
                    time.sleep(1)
                
                print(f"\n🛑 Arresto server (timeout raggiunto)")
        else:
            print(f"\n⚠️ Nessun prodotto aggiornato - arresto server")
        
        print(f"\n🏁 COMPLETATO! Server arrestato automaticamente")
        print(f"📁 File immagini salvati in: {images_dir}")
        print(f"💡 Puoi eliminare la directory se non serve più")
            
    except Exception as e:
        print(f"❌ Errore: {e}")

if __name__ == '__main__':
    host_and_upload()
