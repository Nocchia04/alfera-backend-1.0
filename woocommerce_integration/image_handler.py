"""
Gestore immagini per WooCommerce - Download e conversione
"""
import os
import logging
import requests
from typing import Optional, Dict, Any, List
from urllib.parse import urlparse, urljoin
from PIL import Image
import io
import base64
from django.conf import settings
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile

logger = logging.getLogger('sync')

class ImageHandler:
    """Gestisce download e upload immagini per WooCommerce"""
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })
        
        # Directory temporanea per immagini
        self.temp_dir = os.path.join(settings.MEDIA_ROOT, 'temp_images')
        os.makedirs(self.temp_dir, exist_ok=True)
        
        # Formati supportati
        self.supported_formats = ['JPEG', 'JPG', 'PNG', 'GIF', 'WEBP']
        self.max_size = 5 * 1024 * 1024  # 5MB max
        
    def process_image_url(self, image_url: str, product_sku: str) -> Optional[Dict[str, Any]]:
        """
        Processa URL immagine e la prepara per WooCommerce
        
        Args:
            image_url: URL dell'immagine
            product_sku: SKU del prodotto per naming
            
        Returns:
            Dict con dati immagine processata o None se errore
        """
        if not image_url or not image_url.strip():
            return None
            
        try:
            logger.info(f"Processando immagine per {product_sku}: {image_url[:100]}...")
            
            # Step 1: Download immagine
            image_data = self._download_image(image_url)
            if not image_data:
                logger.warning(f"Download fallito per {image_url}")
                return None
            
            # Step 2: Verifica e converti immagine
            processed_image = self._process_image_data(image_data, product_sku)
            if not processed_image:
                logger.warning(f"Processing fallito per {product_sku}")
                return None
            
            # Step 3: Salva temporaneamente
            temp_path = self._save_temp_image(processed_image, product_sku)
            if not temp_path:
                logger.warning(f"Salvataggio temporaneo fallito per {product_sku}")
                return None
            
            # Step 4: Prepara dati per WooCommerce
            return {
                'src': temp_path,
                'alt': f'Immagine {product_sku}',
                'name': f'{product_sku}_image.jpg'
            }
            
        except Exception as e:
            logger.error(f"Errore processing immagine {product_sku}: {e}")
            return None
    
    def _download_image(self, url: str) -> Optional[bytes]:
        """Download immagine da URL"""
        try:
            # Timeout ragionevole
            response = self.session.get(url, timeout=30, stream=True)
            
            if response.status_code != 200:
                logger.warning(f"HTTP {response.status_code} per {url}")
                return None
            
            # Verifica Content-Type
            content_type = response.headers.get('content-type', '').lower()
            logger.debug(f"Content-Type: {content_type}")
            
            # Scarica contenuto
            content = b''
            for chunk in response.iter_content(chunk_size=8192):
                content += chunk
                if len(content) > self.max_size:
                    logger.warning(f"Immagine troppo grande: {len(content)} bytes")
                    return None
            
            if len(content) < 100:  # Troppo piccola per essere un'immagine
                logger.warning(f"Contenuto troppo piccolo: {len(content)} bytes")
                return None
                
            return content
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Errore download {url}: {e}")
            return None
    
    def _process_image_data(self, image_data: bytes, product_sku: str) -> Optional[bytes]:
        """Processa e converti dati immagine"""
        try:
            # Prova a rilevare il formato
            image_format = self._detect_image_format(image_data)
            
            if not image_format:
                logger.warning(f"Formato immagine non riconosciuto per {product_sku}")
                return None
            
            # Se non è PDF, prova PIL
            if image_format != 'PDF':
                return self._process_with_pil(image_data, product_sku)
            else:
                logger.warning(f"PDF rilevato per {product_sku}, non supportato come immagine")
                return None
                
        except Exception as e:
            logger.error(f"Errore processing immagine {product_sku}: {e}")
            return None
    
    def _detect_image_format(self, data: bytes) -> Optional[str]:
        """Rileva formato del file"""
        if not data:
            return None
            
        # Signatures comuni
        if data.startswith(b'\xff\xd8\xff'):
            return 'JPEG'
        elif data.startswith(b'\x89PNG\r\n\x1a\n'):
            return 'PNG'
        elif data.startswith(b'GIF8'):
            return 'GIF'
        elif data.startswith(b'RIFF') and b'WEBP' in data[:20]:
            return 'WEBP'
        elif data.startswith(b'%PDF'):
            return 'PDF'
        elif b'Adobe' in data[:100] or b'adobe' in data[:100].lower():
            return 'PDF'
        
        # Prova PIL per altri formati
        try:
            with Image.open(io.BytesIO(data)) as img:
                return img.format
        except:
            pass
            
        return None
    
    def _process_with_pil(self, image_data: bytes, product_sku: str) -> Optional[bytes]:
        """Processa immagine con PIL"""
        try:
            # Apri immagine
            with Image.open(io.BytesIO(image_data)) as img:
                # Converti in RGB se necessario
                if img.mode in ('RGBA', 'LA', 'P'):
                    # Crea sfondo bianco per trasparenze
                    background = Image.new('RGB', img.size, (255, 255, 255))
                    if img.mode == 'P':
                        img = img.convert('RGBA')
                    background.paste(img, mask=img.split()[-1] if img.mode == 'RGBA' else None)
                    img = background
                elif img.mode != 'RGB':
                    img = img.convert('RGB')
                
                # Ridimensiona se troppo grande
                max_dimension = 1200
                if img.width > max_dimension or img.height > max_dimension:
                    img.thumbnail((max_dimension, max_dimension), Image.Resampling.LANCZOS)
                    logger.info(f"Ridimensionata immagine {product_sku}: {img.size}")
                
                # Salva come JPEG
                output = io.BytesIO()
                img.save(output, format='JPEG', quality=85, optimize=True)
                
                processed_data = output.getvalue()
                logger.info(f"Immagine processata {product_sku}: {len(processed_data)} bytes")
                
                return processed_data
                
        except Exception as e:
            logger.error(f"Errore PIL per {product_sku}: {e}")
            return None
    
    def _save_temp_image(self, image_data: bytes, product_sku: str) -> Optional[str]:
        """Salva immagine temporaneamente"""
        try:
            filename = f"{product_sku}_temp.jpg"
            temp_path = os.path.join(self.temp_dir, filename)
            
            with open(temp_path, 'wb') as f:
                f.write(image_data)
            
            logger.debug(f"Immagine salvata temporaneamente: {temp_path}")
            return temp_path
            
        except Exception as e:
            logger.error(f"Errore salvataggio temp {product_sku}: {e}")
            return None
    
    def process_product_images(self, product_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Processa tutte le immagini di un prodotto"""
        processed_images = []
        
        images = product_data.get('images', [])
        product_sku = product_data.get('sku', 'unknown')
        
        for i, image_url in enumerate(images):
            if not image_url:
                continue
                
            processed_image = self.process_image_url(image_url, f"{product_sku}_{i}")
            
            if processed_image:
                processed_images.append(processed_image)
            else:
                # Fallback: usa URL originale (WooCommerce potrebbe gestirlo)
                logger.warning(f"Fallback URL originale per {product_sku}: {image_url}")
                processed_images.append({
                    'src': image_url,
                    'alt': f'Immagine {product_sku}',
                    'name': f'{product_sku}_image_{i}'
                })
        
        return processed_images
    
    def cleanup_temp_images(self, max_age_hours: int = 24):
        """Pulisce immagini temporanee vecchie"""
        try:
            import time
            current_time = time.time()
            
            for filename in os.listdir(self.temp_dir):
                file_path = os.path.join(self.temp_dir, filename)
                
                if os.path.isfile(file_path):
                    file_age = current_time - os.path.getctime(file_path)
                    if file_age > (max_age_hours * 3600):
                        os.remove(file_path)
                        logger.debug(f"Rimossa immagine temp vecchia: {filename}")
                        
        except Exception as e:
            logger.error(f"Errore cleanup temp images: {e}")

# Istanza globale
image_handler = ImageHandler()
