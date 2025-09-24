# 🏨 Hotel Sync - Sistema di Sincronizzazione Fornitori

**Sistema Django per la sincronizzazione automatica di prodotti per forniture alberghiere da fornitori multipli verso WooCommerce**

[![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://python.org)
[![Django](https://img.shields.io/badge/Django-4.2+-green.svg)](https://djangoproject.com)
[![WooCommerce](https://img.shields.io/badge/WooCommerce-API-purple.svg)](https://woocommerce.github.io/woocommerce-rest-api-docs/)
[![Status](https://img.shields.io/badge/Status-Production%20Ready-brightgreen.svg)]()

---

## 📋 Indice

- [🎯 Panoramica](#-panoramica)
- [✨ Funzionalità](#-funzionalità)
- [🏗️ Architettura](#️-architettura)
- [🚀 Installazione](#-installazione)
- [⚙️ Configurazione](#️-configurazione)
- [📊 Utilizzo](#-utilizzo)
- [🔧 Fornitori Supportati](#-fornitori-supportati)
- [📸 Gestione Immagini](#-gestione-immagini)
- [🛠️ Sviluppo](#️-sviluppo)
- [📚 API Reference](#-api-reference)
- [🚀 Deploy](#-deploy)
- [❓ FAQ](#-faq)

---

## 🎯 Panoramica

**Hotel Sync** è un sistema completo per automatizzare la sincronizzazione di prodotti per forniture alberghiere da diversi fornitori verso un e-commerce WooCommerce.

### 🎪 Problema Risolto
- **Sincronizzazione manuale** di migliaia di prodotti
- **Formati dati diversi** (XML, CSV, API REST)
- **Gestione immagini** complessa
- **Aggiornamenti** stock e prezzi frequenti
- **Categorizzazione** prodotti uniforme

### 🎯 Soluzione
Sistema unificato che:
- ✅ **Sincronizza automaticamente** prodotti da fornitori multipli
- ✅ **Gestisce immagini reali** con processing e upload automatico
- ✅ **Unifica categorie** con mapping intelligente
- ✅ **Aggiorna stock e prezzi** in tempo reale
- ✅ **Scala facilmente** per nuovi fornitori

---

## ✨ Funzionalità

### 🔄 Sincronizzazione Avanzata
- **Multi-formato**: XML, CSV, API REST
- **Batch processing**: Migliaia di prodotti
- **Delta sync**: Solo modifiche
- **Error recovery**: Gestione errori robusta
- **Logging completo**: Tracciabilità operazioni

### 📸 Gestione Immagini Intelligente
- **Download automatico** da URL fornitori
- **Processing PIL**: Ridimensionamento, conversione
- **Upload WooCommerce**: Media Library integration
- **Formati supportati**: JPEG, PNG, WebP
- **Fallback graceful**: Gestione errori immagini

### 🏷️ Categorizzazione Unificata
- **Mapping automatico** categorie fornitori → WooCommerce
- **Gerarchia mantenuta**: Struttura ad albero
- **Analisi intelligente**: Rilevamento categorie hotel-related
- **Creazione automatica**: Categorie mancanti

### 🎛️ Controllo Granulare
- **Demo mode**: Test con pochi prodotti
- **Full sync**: Sincronizzazione completa
- **Supplier-specific**: Per fornitore
- **Image-only**: Solo upload immagini

---

## 🏗️ Architettura

```
hotel_sync/
├── 🏢 hotel_sync/          # Configurazione Django
├── 📦 suppliers/           # Gestione fornitori
│   └── clients/           # Client API/Parser
├── 🛍️ products/           # Modelli prodotti unificati
├── 🔄 sync/               # Servizi sincronizzazione
├── 🛒 woocommerce_integration/ # Client WooCommerce
├── 📜 scripts/            # Script di utilità
│   ├── sync/             # Sincronizzazione
│   ├── test/             # Testing
│   ├── utils/            # Utilità
│   └── setup/            # Configurazione
├── 📁 data/              # File dati fornitori
└── 📚 docs/              # Documentazione
```

### 🧩 Componenti Principali

#### 🏭 **Supplier Clients**
```python
# Factory Pattern per creazione client
client = SupplierClientFactory.create_client(supplier)
products = client.get_products(limit=100)
```

#### 🔄 **Sync Service**
```python
# Orchestratore sincronizzazione
sync_service = SyncService()
result = sync_service.sync_supplier(supplier, sync_to_woocommerce=True)
```

#### 🛒 **WooCommerce Integration**
```python
# Client WooCommerce con gestione immagini
wc_client = WooCommerceClient()
product = wc_client.create_or_update_product(product_data)
```

#### 🖼️ **Image Handler**
```python
# Processing e upload immagini
image_handler = ImageHandler()
processed = image_handler.process_product_images(product_data)
```

---

## 🚀 Installazione

### 📋 Prerequisiti
- **Python 3.11+**
- **PostgreSQL** (produzione) / **SQLite** (sviluppo)
- **Redis** (opzionale, per caching)
- **WooCommerce** con API abilitata

### 🔧 Setup Rapido

```bash
# 1. Clone repository
git clone <repository-url>
cd hotel_sync

# 2. Virtual environment
python -m venv venv
source venv/bin/activate  # Linux/Mac
# o
venv\Scripts\activate     # Windows

# 3. Installa dipendenze
pip install -r requirements.txt

# 4. Configura environment
cp .env.example .env
# Modifica .env con le tue configurazioni

# 5. Setup database
python manage.py migrate

# 6. Carica fixture fornitori
python manage.py loaddata suppliers/fixtures/initial_suppliers.json
python manage.py loaddata suppliers/fixtures/bic_supplier.json

# 7. Test installazione
python scripts/test/test_mkto.py
python scripts/test/test_bic.py
```

---

## ⚙️ Configurazione

### 🔐 File `.env`

```bash
# Database
DATABASE_URL=postgres://user:pass@localhost/hotel_sync_db

# Redis (opzionale)
REDIS_URL=redis://localhost:6379/0

# WooCommerce API
WOOCOMMERCE_URL=https://your-site.com
WOOCOMMERCE_KEY=ck_your_consumer_key
WOOCOMMERCE_SECRET=cs_your_consumer_secret

# Percorsi dati fornitori
MAKITO_XML_PATH=/path/to/xml/files
BIC_CSV_PATH=/path/to/csv/file

# Django
SECRET_KEY=your-secret-key
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1
```

### 🗂️ Percorsi Dati

Posiziona i file dati nella directory `data/`:

```
data/
├── alldatafile_ita.xml          # MKTO Prodotti
├── allstockgroupedfile.xml      # MKTO Stock
├── pricefile_€805301.xml        # MKTO Prezzi
├── allprintdatafile_ita.xml     # MKTO Print Data
├── PrintPrices_ita.xml          # MKTO Print Prices
└── BGE_Masterfile_Distributor_EUR.csv  # BIC Prodotti
```

### 🛒 Setup WooCommerce

```bash
# Configura credenziali API
python scripts/setup/setup_woocommerce.py
```

---

## 📊 Utilizzo

### 🚀 Script Master

Il modo più semplice per usare il sistema:

```bash
# Script interattivo
python scripts/run_sync.py

# Sincronizzazione MKTO completa
python scripts/run_sync.py --supplier MKTO --full

# Demo BIC (10 prodotti)
python scripts/run_sync.py --supplier BIC --limit 10

# BIC con immagini
python scripts/run_sync.py --supplier BIC --images

# Test tutti i fornitori
python scripts/run_sync.py --test-all
```

### 🔧 Script Specifici

#### 📊 **MKTO (Web Service XML)**
```bash
# Sincronizzazione completa
python scripts/sync/sync_mkto_complete.py

# Con limiti
python scripts/sync/sync_mkto_complete.py --limit 50

# Solo DB locale
python scripts/sync/sync_mkto_complete.py --no-woocommerce

# Pulisci cache
python scripts/sync/sync_mkto_complete.py --clear-cache
```

#### 📊 **BIC (CSV)**
```bash
# Sincronizzazione prodotti
python scripts/sync/sync_bic_complete.py

# Con immagini reali
python scripts/sync/host_bic_images.py

# Lingua specifica
python scripts/sync/sync_bic_complete.py --language it
```

#### 🧪 **Testing**
```bash
# Test MKTO
python scripts/test/test_mkto.py

# Test BIC  
python scripts/test/test_bic.py
```

#### 🛠️ **Utilità**
```bash
# Analisi categorie MKTO
python scripts/utils/analyze_mkto_categories.py

# Setup categorie WooCommerce
python scripts/utils/implement_category_integration.py

# Fix SKU duplicati
python scripts/utils/fix_duplicate_skus.py
```

### 🎛️ Django Management Commands

```bash
# Sincronizzazione via Django command
python manage.py sync --supplier MKTO
python manage.py sync --supplier BIC --limit 10
```

---

## 🔧 Fornitori Supportati

### 🌐 **MKTO (Web Service XML)**

**Formato**: XML files multipli
**Prodotti**: ~50,000+
**Categorie**: Gerarchia complessa
**Lingue**: Italiano, Inglese

**File richiesti**:
- `alldatafile_ita.xml` - Prodotti e varianti
- `allstockgroupedfile.xml` - Stock
- `pricefile_€805301.xml` - Prezzi
- `allprintdatafile_ita.xml` - Dati stampa
- `PrintPrices_ita.xml` - Prezzi stampa

**Caratteristiche**:
- ✅ Parsing XML ottimizzato per file grandi
- ✅ Cache intelligente Redis
- ✅ Gestione varianti (colore, taglia)
- ✅ Mapping categorie automatico
- ✅ Generazione SKU unici

### 🖊️ **BIC (CSV)**

**Formato**: CSV multilingua
**Prodotti**: ~5,000+
**Categorie**: Brand-based
**Lingue**: IT, EN, FR, DE, ES

**File richiesto**:
- `BGE_Masterfile_Distributor_EUR.csv`

**Caratteristiche**:
- ✅ Selezione lingua preferita
- ✅ Prezzi a scaglioni
- ✅ Immagini reali con processing
- ✅ Dati packaging completi
- ✅ Upload immagini automatico

---

## 📸 Gestione Immagini

### 🔄 Pipeline Immagini

```python
# 1. Download da URL fornitore
image_data = image_handler._download_image(url)

# 2. Rilevamento formato
format = image_handler._detect_image_format(image_data)

# 3. Processing PIL
processed = image_handler._process_with_pil(image_data, filename)

# 4. Upload WooCommerce
wc_client.update_product_images(product_id, images)
```

### 🖼️ **Formati Supportati**
- ✅ **JPEG** - Conversione automatica
- ✅ **PNG** - Mantenimento trasparenza  
- ✅ **WebP** - Supporto moderno
- ❌ **PDF** - Skippo automatico

### 🎨 **Processing Features**
- **Ridimensionamento**: Max 800x600px
- **Compressione**: Qualità ottimizzata
- **Conversione**: Formato uniforme
- **Validazione**: Check integrità

### 🚀 **Upload Strategies**

#### **Metodo 1: Direct Media Upload**
```python
# Upload diretto su WordPress Media Library
response = requests.post(media_endpoint, files=files)
```

#### **Metodo 2: Temporary Server** 
```python
# Server HTTP temporaneo per hosting
python scripts/sync/host_bic_images.py
# Auto-stop dopo download WooCommerce
```

---

## 🛠️ Sviluppo

### 🏗️ Aggiungere Nuovo Fornitore

#### 1. **Creare Parser**
```python
# suppliers/clients/new_supplier_parser.py
class NewSupplierParser(BaseSupplierClient):
    def get_products(self, limit=None):
        # Implementa parsing specifico
        pass
```

#### 2. **Aggiornare Factory**
```python
# suppliers/clients/factory.py
elif supplier.supplier_type == 'NEW_SUPPLIER':
    return NewSupplierParser(supplier)
```

#### 3. **Aggiornare Models**
```python
# suppliers/models.py
SUPPLIER_TYPES = [
    ('NEW_SUPPLIER', 'New Supplier Name'),
    # ...
]
```

#### 4. **Data Mapper**
```python
# sync/services/data_mapper.py
def _map_new_supplier_product(self, raw_data, supplier):
    # Implementa mapping dati
    pass
```

### 🧪 Testing

```bash
# Test specifico fornitore
python scripts/test/test_new_supplier.py

# Test integrazione completa
python manage.py test

# Coverage
coverage run --source='.' manage.py test
coverage report
```

### 📊 Logging e Monitoring

```python
# Configurazione logging
LOGGING = {
    'version': 1,
    'handlers': {
        'file': {
            'level': 'ERROR',
            'class': 'logging.FileHandler',
            'filename': 'logs/sync.log',
        }
    },
    'loggers': {
        'sync': {
            'handlers': ['file'],
            'level': 'ERROR',
        }
    }
}
```

---

## 📚 API Reference

### 🏭 **SupplierClientFactory**

```python
# Crea client per fornitore
client = SupplierClientFactory.create_client(supplier)

# Metodi disponibili
products = client.get_products(limit=100)
stock = client.get_stock(product_code)
prices = client.get_prices(product_code)
```

### 🔄 **SyncService**

```python
# Sincronizzazione fornitore
sync_service = SyncService()
result = sync_service.sync_supplier(
    supplier=supplier,
    sync_to_woocommerce=True
)

# Risultato
{
    'sync_log': SyncLog,
    'stats': {
        'products_processed': 1000,
        'products_created': 800,
        'products_updated': 200,
        'errors_count': 0
    }
}
```

### 🛒 **WooCommerceClient**

```python
# Creazione/aggiornamento prodotto
wc_client = WooCommerceClient()
product = wc_client.create_or_update_product(product_data)

# Gestione categorie
category = wc_client.create_category({
    'name': 'Categoria Nome',
    'parent': parent_id
})

# Statistiche
stats = wc_client.get_product_stats()
```

### 🖼️ **ImageHandler**

```python
# Processing immagini prodotto
image_handler = ImageHandler()
processed = image_handler.process_product_images(product_data)

# Risultato
[
    {
        'src': 'processed_image_url',
        'alt': 'Alt text',
        'name': 'filename.jpg'
    }
]
```

---

## 🚀 Deploy

### 🐳 **Heroku Deployment**

```bash
# 1. Setup Heroku
heroku create hotel-sync-app
heroku addons:create heroku-postgresql:mini
heroku addons:create heroku-redis:mini

# 2. Config vars
heroku config:set SECRET_KEY=your-secret-key
heroku config:set WOOCOMMERCE_URL=https://your-site.com
heroku config:set WOOCOMMERCE_KEY=ck_key
heroku config:set WOOCOMMERCE_SECRET=cs_secret

# 3. Deploy
git push heroku main

# 4. Setup database
heroku run python manage.py migrate
heroku run python manage.py loaddata suppliers/fixtures/initial_suppliers.json

# 5. Scheduler per sync automatica
heroku addons:create scheduler:standard
# Aggiungi job: python manage.py sync --supplier MKTO
```

### 🔧 **File di Deploy**

**Procfile**:
```
web: gunicorn hotel_sync.wsgi --log-file -
worker: celery -A hotel_sync worker --loglevel=error
beat: celery -A hotel_sync beat --loglevel=error
```

**runtime.txt**:
```
python-3.11.0
```

### 🌐 **Docker** (Opzionale)

```dockerfile
# Dockerfile
FROM python:3.11
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
CMD ["gunicorn", "hotel_sync.wsgi:application"]
```

```yaml
# docker-compose.yml
version: '3.8'
services:
  web:
    build: .
    ports:
      - "8000:8000"
  postgres:
    image: postgres:13
    environment:
      POSTGRES_DB: hotel_sync
  redis:
    image: redis:alpine
```

---

## ❓ FAQ

### 🤔 **Domande Generali**

**Q: Quanti prodotti può gestire?**
A: Testato con 50,000+ prodotti MKTO. Scalabile con batch processing e caching.

**Q: Quanto tempo richiede una sincronizzazione completa?**
A: ~30-60 minuti per MKTO completo, ~10-15 minuti per BIC, dipende dalla connessione.

**Q: Le immagini vengono scaricate ogni volta?**
A: No, sistema di cache intelligente evita download duplicati.

### 🔧 **Problemi Comuni**

**Q: Errore "No URL Provided" per immagini**
A: Usa `host_bic_images.py` che crea server temporaneo per upload.

**Q: Prodotti non appaiono su WooCommerce**
A: Controlla che `woocommerce_id` sia impostato e status sia 'draft'.

**Q: File XML troppo grandi**
A: Parser MKTO usa streaming XML, ma aumenta memoria se necessario.

**Q: Redis non disponibile**
A: Sistema funziona senza Redis, usa cache locale automaticamente.

### 🚀 **Performance**

**Q: Come migliorare velocità sincronizzazione?**
A: 
- Usa Redis per caching
- Aumenta batch size
- Sincronizza solo delta (modifiche)
- Usa Celery per processing asincrono

**Q: Database PostgreSQL vs SQLite?**
A: PostgreSQL per produzione (concurrent access), SQLite per sviluppo.

---

## 🎯 **Roadmap**

### 🔮 **Prossime Funzionalità**
- [ ] **API REST** per controllo esterno
- [ ] **Dashboard web** per monitoring
- [ ] **Webhook WooCommerce** per sync bidirezionale  
- [ ] **AI categorization** per prodotti
- [ ] **Multi-store** support
- [ ] **Inventory management** avanzato

### 🛠️ **Miglioramenti Tecnici**
- [ ] **GraphQL API** per query complesse
- [ ] **Kubernetes** deployment
- [ ] **Elasticsearch** per ricerca prodotti
- [ ] **Message queues** per reliability
- [ ] **Microservices** architecture

---

## 📞 **Supporto**

### 🐛 **Bug Reports**
Apri issue su GitHub con:
- Descrizione dettagliata
- Logs errore
- Steps per riprodurre
- Ambiente (OS, Python version)

### 💡 **Feature Requests**
Proponi nuove funzionalità via GitHub Issues con:
- Caso d'uso specifico
- Benefici attesi
- Implementazione suggerita

### 📧 **Contatti**
- **Email**: support@hotel-sync.com
- **GitHub**: [Repository Link]
- **Docs**: [Documentation Link]

---

## 📄 **Licenza**

MIT License - Vedi file `LICENSE` per dettagli.

---

## 🙏 **Ringraziamenti**

- **Django Community** per il framework robusto
- **WooCommerce** per le API eccellenti  
- **Pillow** per image processing
- **Celery** per task asincroni
- **Tutti i contributori** del progetto

---

**🚀 Hotel Sync - Sincronizzazione Fornitori Semplificata**

*Made with ❤️ for the hospitality industry*
#   a l f e r a - b a c k e n d - 1 . 0  
 