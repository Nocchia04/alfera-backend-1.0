"""
Modelli unificati per prodotti da tutti i fornitori
"""
from django.db import models
from django.utils import timezone
from suppliers.models import Supplier


class Category(models.Model):
    """Categorie prodotti unificate"""
    
    name = models.CharField(max_length=200, verbose_name="Nome Categoria")
    slug = models.SlugField(unique=True, verbose_name="Slug")
    parent = models.ForeignKey('self', null=True, blank=True, on_delete=models.CASCADE, related_name='children')
    
    # Mapping con WooCommerce
    woocommerce_id = models.IntegerField(null=True, blank=True, verbose_name="ID WooCommerce")
    
    # Mapping con fornitori
    mkto_mapping = models.CharField(max_length=200, blank=True, verbose_name="Mapping MKTO", help_text="Categoria MKTO originale")
    
    # Metadati
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Categoria"
        verbose_name_plural = "Categorie"
        ordering = ['name']
    
    def __str__(self):
        if self.parent:
            return f"{self.parent.name} > {self.name}"
        return self.name


class Product(models.Model):
    """Prodotto unificato da tutti i fornitori"""
    
    # Identificatori
    supplier = models.ForeignKey(Supplier, on_delete=models.CASCADE, related_name='products')
    supplier_ref = models.CharField(max_length=100, verbose_name="Riferimento Fornitore")
    sku = models.CharField(max_length=100, unique=True, verbose_name="SKU")
    
    # Informazioni base
    name = models.CharField(max_length=500, verbose_name="Nome Prodotto")
    description = models.TextField(blank=True, verbose_name="Descrizione")
    short_description = models.TextField(blank=True, verbose_name="Descrizione Breve")
    
    # Categorizzazione
    category = models.ForeignKey(Category, null=True, blank=True, on_delete=models.SET_NULL, related_name='products')
    brand = models.CharField(max_length=100, blank=True, verbose_name="Brand")
    
    # Caratteristiche fisiche
    material = models.CharField(max_length=200, blank=True, verbose_name="Materiale")
    color = models.CharField(max_length=100, blank=True, verbose_name="Colore")
    dimensions = models.CharField(max_length=200, blank=True, verbose_name="Dimensioni")
    weight = models.DecimalField(max_digits=10, decimal_places=3, null=True, blank=True, verbose_name="Peso (g)")
    
    # 🆕 PREZZO PRINCIPALE
    base_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, verbose_name="Prezzo Base")
    currency = models.CharField(max_length=3, default='EUR', verbose_name="Valuta")
    
    # Immagini
    main_image = models.URLField(blank=True, verbose_name="Immagine Principale")
    images = models.JSONField(default=list, blank=True, verbose_name="Immagini")
    
    # Stampa
    is_printable = models.BooleanField(default=False, verbose_name="Stampabile")
    print_areas = models.JSONField(default=list, blank=True, verbose_name="Aree di Stampa")
    
    # WooCommerce
    woocommerce_id = models.IntegerField(null=True, blank=True, verbose_name="ID WooCommerce")
    woocommerce_status = models.CharField(max_length=20, default='draft', verbose_name="Stato WooCommerce")
    last_woo_sync = models.DateTimeField(null=True, blank=True, verbose_name="Ultima Sync WooCommerce")
    
    # Stato
    is_active = models.BooleanField(default=True, verbose_name="Attivo")
    
    # Metadati
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Creato il")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Aggiornato il")
    supplier_updated_at = models.DateTimeField(null=True, blank=True, verbose_name="Aggiornato dal Fornitore")
    
    class Meta:
        verbose_name = "Prodotto"
        verbose_name_plural = "Prodotti"
        ordering = ['name']
        unique_together = ['supplier', 'supplier_ref']
    
    def __str__(self):
        return f"{self.name} ({self.sku})"
    
    @property
    def has_stock(self):
        """Verifica se il prodotto ha stock disponibile"""
        return self.variants.filter(stock__stock_quantity__gt=0).exists()
    
    @property
    def total_stock(self):
        """Stock totale di tutte le varianti"""
        return sum(variant.current_stock for variant in self.variants.all())


class ProductVariant(models.Model):
    """Varianti del prodotto (colori, taglie, ecc.)"""
    
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='variants')
    
    # Identificatori
    supplier_variant_ref = models.CharField(max_length=100, verbose_name="Rif. Variante Fornitore")
    sku = models.CharField(max_length=100, unique=True, verbose_name="SKU Variante")
    
    # Caratteristiche variante
    color = models.CharField(max_length=100, blank=True, verbose_name="Colore")
    size = models.CharField(max_length=50, blank=True, verbose_name="Taglia")
    color_code = models.CharField(max_length=20, blank=True, verbose_name="Codice Colore")
    
    # Immagini specifiche variante
    image = models.URLField(blank=True, verbose_name="Immagine Variante")
    
    # Identificatori esterni
    gtin = models.CharField(max_length=50, blank=True, verbose_name="GTIN/EAN")
    
    # WooCommerce
    woocommerce_variation_id = models.IntegerField(null=True, blank=True, verbose_name="ID Variazione WooCommerce")
    
    # Stato
    is_active = models.BooleanField(default=True, verbose_name="Attiva")
    
    # Metadati
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Variante Prodotto"
        verbose_name_plural = "Varianti Prodotto"
        unique_together = ['product', 'supplier_variant_ref']
    
    def __str__(self):
        parts = [self.product.name]
        if self.color:
            parts.append(self.color)
        if self.size:
            parts.append(self.size)
        return ' - '.join(parts)
    
    @property
    def current_stock(self):
        """Stock attuale della variante"""
        try:
            return self.stock.stock_quantity
        except Stock.DoesNotExist:
            return 0
    
    @property
    def current_price(self):
        """Prezzo attuale della variante"""
        try:
            return self.prices.filter(is_active=True).first().price
        except (Price.DoesNotExist, AttributeError):
            return None


class Stock(models.Model):
    """Gestione stock per le varianti"""
    
    variant = models.OneToOneField(ProductVariant, on_delete=models.CASCADE, related_name='stock')
    
    # Stock
    stock_quantity = models.IntegerField(default=0, verbose_name="Quantità in Stock")
    reserved_quantity = models.IntegerField(default=0, verbose_name="Quantità Riservata")
    
    # Disponibilità
    availability_status = models.CharField(max_length=50, default='available', verbose_name="Stato Disponibilità")
    next_arrival_date = models.DateField(null=True, blank=True, verbose_name="Prossimo Arrivo")
    next_arrival_quantity = models.IntegerField(null=True, blank=True, verbose_name="Quantità Prossimo Arrivo")
    
    # Metadati
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Aggiornato il")
    supplier_updated_at = models.DateTimeField(null=True, blank=True, verbose_name="Aggiornato dal Fornitore")
    
    class Meta:
        verbose_name = "Stock"
        verbose_name_plural = "Stock"
    
    def __str__(self):
        return f"{self.variant.sku} - Stock: {self.stock_quantity}"
    
    @property
    def available_quantity(self):
        """Quantità disponibile (stock - riservato)"""
        return max(0, self.stock_quantity - self.reserved_quantity)


class Price(models.Model):
    """Prezzi per le varianti con fasce quantità"""
    
    variant = models.ForeignKey(ProductVariant, on_delete=models.CASCADE, related_name='prices')
    
    # Prezzo
    price = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Prezzo")
    currency = models.CharField(max_length=3, default='EUR', verbose_name="Valuta")
    
    # Fascia quantità
    min_quantity = models.IntegerField(default=1, verbose_name="Quantità Minima")
    max_quantity = models.IntegerField(null=True, blank=True, verbose_name="Quantità Massima")
    
    # Validità
    valid_from = models.DateField(default=timezone.now, verbose_name="Valido dal")
    valid_until = models.DateField(null=True, blank=True, verbose_name="Valido fino al")
    
    # Stato
    is_active = models.BooleanField(default=True, verbose_name="Attivo")
    
    # Metadati
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Prezzo"
        verbose_name_plural = "Prezzi"
        ordering = ['min_quantity']
    
    def __str__(self):
        return f"{self.variant.sku} - €{self.price} (min: {self.min_quantity})"


class PrintOption(models.Model):
    """Opzioni di stampa per i prodotti"""
    
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='print_options')
    
    # Area di stampa
    position_name = models.CharField(max_length=100, verbose_name="Nome Posizione")
    position_code = models.CharField(max_length=50, verbose_name="Codice Posizione")
    
    # Dimensioni area
    max_width = models.DecimalField(max_digits=6, decimal_places=2, verbose_name="Larghezza Max (mm)")
    max_height = models.DecimalField(max_digits=6, decimal_places=2, verbose_name="Altezza Max (mm)")
    
    # Tecniche disponibili
    available_techniques = models.JSONField(default=list, verbose_name="Tecniche Disponibili")
    max_colors = models.IntegerField(default=1, verbose_name="Colori Massimi")
    
    # Immagini template
    template_image = models.URLField(blank=True, verbose_name="Immagine Template")
    
    class Meta:
        verbose_name = "Opzione di Stampa"
        verbose_name_plural = "Opzioni di Stampa"
        unique_together = ['product', 'position_code']
    
    def __str__(self):
        return f"{self.product.name} - {self.position_name}"


class PrintPrice(models.Model):
    """Prezzi di stampa per tecniche e quantità"""
    
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='print_prices')
    
    # Tecnica
    technique_code = models.CharField(max_length=50, verbose_name="Codice Tecnica")
    technique_name = models.CharField(max_length=200, verbose_name="Nome Tecnica")
    
    # Prezzi
    setup_cost = models.DecimalField(max_digits=8, decimal_places=2, default=0, verbose_name="Costo Impostazione")
    unit_price = models.DecimalField(max_digits=6, decimal_places=3, verbose_name="Prezzo Unitario")
    
    # Fascia quantità
    min_quantity = models.IntegerField(default=1, verbose_name="Quantità Minima")
    max_quantity = models.IntegerField(null=True, blank=True, verbose_name="Quantità Massima")
    
    # Colori aggiuntivi
    additional_color_price = models.DecimalField(max_digits=6, decimal_places=3, default=0, verbose_name="Prezzo Colore Aggiuntivo")
    
    # Metadati
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Prezzo Stampa"
        verbose_name_plural = "Prezzi Stampa"
        ordering = ['technique_name', 'min_quantity']
    
    def __str__(self):
        return f"{self.product.name} - {self.technique_name} - €{self.unit_price}"