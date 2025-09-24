"""
Modelli per la gestione dei fornitori e delle loro API
"""
from django.db import models
from django.utils import timezone


class Supplier(models.Model):
    """Modello per i fornitori"""
    
    SUPPLIER_TYPES = [
        ('MIDOCEAN', 'Midocean'),
        ('MAKITO', 'Makito'),
        ('BIC', 'BIC'),
    ]
    
    name = models.CharField(max_length=100, verbose_name="Nome Fornitore")
    code = models.CharField(max_length=20, unique=True, verbose_name="Codice")
    supplier_type = models.CharField(max_length=20, choices=SUPPLIER_TYPES, verbose_name="Tipo")
    is_active = models.BooleanField(default=True, verbose_name="Attivo")
    
    # Configurazione API
    api_base_url = models.URLField(blank=True, verbose_name="URL Base API")
    api_key = models.CharField(max_length=255, blank=True, verbose_name="API Key")
    api_secret = models.CharField(max_length=255, blank=True, verbose_name="API Secret")
    
    # Configurazione XML (per Makito)
    xml_path = models.CharField(max_length=500, blank=True, verbose_name="Percorso File XML")
    
    # Configurazione CSV (per BIC)
    csv_path = models.CharField(max_length=500, blank=True, verbose_name="Percorso File CSV")
    
    # Metadati
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Creato il")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Aggiornato il")
    last_sync = models.DateTimeField(null=True, blank=True, verbose_name="Ultima Sincronizzazione")
    
    class Meta:
        verbose_name = "Fornitore"
        verbose_name_plural = "Fornitori"
        ordering = ['name']
    
    def __str__(self):
        return f"{self.name} ({self.code})"
    
    @property
    def is_api_configured(self):
        """Verifica se l'API è configurata correttamente"""
        if self.supplier_type == 'MIDOCEAN':
            return bool(self.api_base_url and self.api_key)
        elif self.supplier_type == 'MAKITO':
            return bool(self.xml_path)
        elif self.supplier_type == 'BIC':
            return bool(self.csv_path)
        return False


class SupplierEndpoint(models.Model):
    """Configurazione degli endpoint API per ogni fornitore"""
    
    ENDPOINT_TYPES = [
        ('PRODUCTS', 'Prodotti'),
        ('STOCK', 'Magazzino'),
        ('PRICES', 'Prezzi'),
        ('PRINT_DATA', 'Dati Stampa'),
        ('PRINT_PRICES', 'Prezzi Stampa'),
    ]
    
    supplier = models.ForeignKey(Supplier, on_delete=models.CASCADE, related_name='endpoints')
    endpoint_type = models.CharField(max_length=20, choices=ENDPOINT_TYPES, verbose_name="Tipo Endpoint")
    url = models.URLField(verbose_name="URL Endpoint")
    is_active = models.BooleanField(default=True, verbose_name="Attivo")
    
    # Configurazioni specifiche
    update_frequency = models.IntegerField(default=3600, verbose_name="Frequenza Aggiornamento (secondi)")  # 1 ora default
    last_update = models.DateTimeField(null=True, blank=True, verbose_name="Ultimo Aggiornamento")
    
    class Meta:
        verbose_name = "Endpoint Fornitore"
        verbose_name_plural = "Endpoint Fornitori"
        unique_together = ['supplier', 'endpoint_type']
    
    def __str__(self):
        return f"{self.supplier.name} - {self.get_endpoint_type_display()}"


class SyncLog(models.Model):
    """Log delle sincronizzazioni"""
    
    STATUS_CHOICES = [
        ('PENDING', 'In Attesa'),
        ('RUNNING', 'In Esecuzione'),
        ('SUCCESS', 'Completata'),
        ('ERROR', 'Errore'),
        ('PARTIAL', 'Parziale'),
    ]
    
    SYNC_TYPES = [
        ('FULL', 'Completa'),
        ('PRODUCTS', 'Solo Prodotti'),
        ('STOCK', 'Solo Magazzino'),
        ('PRICES', 'Solo Prezzi'),
        ('MANUAL', 'Manuale'),
    ]
    
    supplier = models.ForeignKey(Supplier, on_delete=models.CASCADE, related_name='sync_logs')
    sync_type = models.CharField(max_length=20, choices=SYNC_TYPES, verbose_name="Tipo Sincronizzazione")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING', verbose_name="Stato")
    
    # Contatori
    products_processed = models.IntegerField(default=0, verbose_name="Prodotti Elaborati")
    products_created = models.IntegerField(default=0, verbose_name="Prodotti Creati")
    products_updated = models.IntegerField(default=0, verbose_name="Prodotti Aggiornati")
    products_errors = models.IntegerField(default=0, verbose_name="Errori Prodotti")
    
    # Tempi
    started_at = models.DateTimeField(default=timezone.now, verbose_name="Iniziato il")
    completed_at = models.DateTimeField(null=True, blank=True, verbose_name="Completato il")
    
    # Dettagli
    error_message = models.TextField(blank=True, verbose_name="Messaggio di Errore")
    details = models.JSONField(default=dict, blank=True, verbose_name="Dettagli")
    
    class Meta:
        verbose_name = "Log Sincronizzazione"
        verbose_name_plural = "Log Sincronizzazioni"
        ordering = ['-started_at']
    
    def __str__(self):
        return f"{self.supplier.name} - {self.get_sync_type_display()} - {self.get_status_display()}"
    
    @property
    def duration(self):
        """Durata della sincronizzazione"""
        if self.completed_at:
            return self.completed_at - self.started_at
        return timezone.now() - self.started_at
    
    def mark_completed(self, status='SUCCESS'):
        """Marca la sincronizzazione come completata"""
        self.status = status
        self.completed_at = timezone.now()
        self.save()
        
        # Aggiorna last_sync del fornitore
        if status == 'SUCCESS':
            self.supplier.last_sync = self.completed_at
            self.supplier.save()


class SupplierRateLimit(models.Model):
    """Configurazione rate limiting per API fornitori"""
    
    supplier = models.OneToOneField(Supplier, on_delete=models.CASCADE, related_name='rate_limit')
    requests_per_minute = models.IntegerField(default=60, verbose_name="Richieste per Minuto")
    requests_per_hour = models.IntegerField(default=1000, verbose_name="Richieste per Ora")
    concurrent_requests = models.IntegerField(default=5, verbose_name="Richieste Simultanee")
    
    # Tracking
    current_minute_requests = models.IntegerField(default=0)
    current_hour_requests = models.IntegerField(default=0)
    last_reset_minute = models.DateTimeField(default=timezone.now)
    last_reset_hour = models.DateTimeField(default=timezone.now)
    
    class Meta:
        verbose_name = "Rate Limit Fornitore"
        verbose_name_plural = "Rate Limits Fornitori"
    
    def __str__(self):
        return f"{self.supplier.name} - Rate Limit"
    
    def can_make_request(self):
        """Verifica se è possibile fare una richiesta"""
        now = timezone.now()
        
        # Reset contatori se necessario
        if (now - self.last_reset_minute).seconds >= 60:
            self.current_minute_requests = 0
            self.last_reset_minute = now
        
        if (now - self.last_reset_hour).seconds >= 3600:
            self.current_hour_requests = 0
            self.last_reset_hour = now
        
        # Verifica limiti
        if self.current_minute_requests >= self.requests_per_minute:
            return False
        if self.current_hour_requests >= self.requests_per_hour:
            return False
        
        return True
    
    def increment_requests(self):
        """Incrementa i contatori delle richieste"""
        self.current_minute_requests += 1
        self.current_hour_requests += 1
        self.save()