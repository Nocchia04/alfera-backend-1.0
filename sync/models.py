"""
Modelli per la gestione delle sincronizzazioni
"""
from django.db import models
from django.utils import timezone
from suppliers.models import Supplier


class SyncTask(models.Model):
    """Task di sincronizzazione programmati"""
    
    TASK_TYPES = [
        ('FULL_SYNC', 'Sincronizzazione Completa'),
        ('PRODUCTS_SYNC', 'Sincronizzazione Prodotti'),
        ('STOCK_SYNC', 'Sincronizzazione Stock'),
        ('PRICES_SYNC', 'Sincronizzazione Prezzi'),
        ('WOOCOMMERCE_SYNC', 'Sincronizzazione WooCommerce'),
    ]
    
    STATUS_CHOICES = [
        ('PENDING', 'In Attesa'),
        ('RUNNING', 'In Esecuzione'),
        ('SUCCESS', 'Completato'),
        ('ERROR', 'Errore'),
        ('CANCELLED', 'Annullato'),
    ]
    
    PRIORITY_CHOICES = [
        (1, 'Bassa'),
        (2, 'Normale'),
        (3, 'Alta'),
        (4, 'Critica'),
    ]
    
    # Configurazione task
    supplier = models.ForeignKey(Supplier, null=True, blank=True, on_delete=models.CASCADE, related_name='sync_tasks')
    task_type = models.CharField(max_length=20, choices=TASK_TYPES, verbose_name="Tipo Task")
    priority = models.IntegerField(choices=PRIORITY_CHOICES, default=2, verbose_name="Priorità")
    
    # Stato
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING', verbose_name="Stato")
    
    # Programmazione
    scheduled_at = models.DateTimeField(default=timezone.now, verbose_name="Programmato per")
    started_at = models.DateTimeField(null=True, blank=True, verbose_name="Iniziato il")
    completed_at = models.DateTimeField(null=True, blank=True, verbose_name="Completato il")
    
    # Risultati
    items_processed = models.IntegerField(default=0, verbose_name="Elementi Elaborati")
    items_success = models.IntegerField(default=0, verbose_name="Successi")
    items_errors = models.IntegerField(default=0, verbose_name="Errori")
    
    # Dettagli
    error_message = models.TextField(blank=True, verbose_name="Messaggio Errore")
    task_data = models.JSONField(default=dict, blank=True, verbose_name="Dati Task")
    result_data = models.JSONField(default=dict, blank=True, verbose_name="Risultati")
    
    # Metadati
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Creato il")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Aggiornato il")
    
    # Celery
    celery_task_id = models.CharField(max_length=255, blank=True, verbose_name="Celery Task ID")
    
    class Meta:
        verbose_name = "Task di Sincronizzazione"
        verbose_name_plural = "Task di Sincronizzazione"
        ordering = ['-priority', 'scheduled_at']
    
    def __str__(self):
        supplier_name = self.supplier.name if self.supplier else "Tutti"
        return f"{supplier_name} - {self.get_task_type_display()} - {self.get_status_display()}"
    
    @property
    def duration(self):
        """Durata del task"""
        if self.started_at:
            end_time = self.completed_at or timezone.now()
            return end_time - self.started_at
        return None
    
    def mark_running(self):
        """Marca il task come in esecuzione"""
        self.status = 'RUNNING'
        self.started_at = timezone.now()
        self.save()
    
    def mark_completed(self, status='SUCCESS', error_message=''):
        """Marca il task come completato"""
        self.status = status
        self.completed_at = timezone.now()
        if error_message:
            self.error_message = error_message
        self.save()


class DataMapping(models.Model):
    """Mapping dei dati tra fornitori e sistema unificato"""
    
    MAPPING_TYPES = [
        ('CATEGORY', 'Categoria'),
        ('ATTRIBUTE', 'Attributo'),
        ('STATUS', 'Stato'),
        ('FIELD', 'Campo'),
    ]
    
    supplier = models.ForeignKey(Supplier, on_delete=models.CASCADE, related_name='data_mappings')
    mapping_type = models.CharField(max_length=20, choices=MAPPING_TYPES, verbose_name="Tipo Mapping")
    
    # Mapping
    source_field = models.CharField(max_length=200, verbose_name="Campo Sorgente")
    source_value = models.CharField(max_length=500, verbose_name="Valore Sorgente")
    target_field = models.CharField(max_length=200, verbose_name="Campo Destinazione")
    target_value = models.CharField(max_length=500, verbose_name="Valore Destinazione")
    
    # Configurazione
    is_active = models.BooleanField(default=True, verbose_name="Attivo")
    transformation_rule = models.TextField(blank=True, verbose_name="Regola di Trasformazione")
    
    # Metadati
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Mapping Dati"
        verbose_name_plural = "Mapping Dati"
        unique_together = ['supplier', 'mapping_type', 'source_field', 'source_value']
    
    def __str__(self):
        return f"{self.supplier.name} - {self.source_field}: {self.source_value} → {self.target_value}"


class SyncRule(models.Model):
    """Regole di sincronizzazione personalizzate"""
    
    supplier = models.ForeignKey(Supplier, on_delete=models.CASCADE, related_name='sync_rules')
    
    # Regola
    name = models.CharField(max_length=200, verbose_name="Nome Regola")
    description = models.TextField(blank=True, verbose_name="Descrizione")
    
    # Condizioni (JSON con struttura per filtri)
    conditions = models.JSONField(default=dict, verbose_name="Condizioni")
    
    # Azioni (JSON con azioni da eseguire)
    actions = models.JSONField(default=dict, verbose_name="Azioni")
    
    # Configurazione
    is_active = models.BooleanField(default=True, verbose_name="Attiva")
    priority = models.IntegerField(default=100, verbose_name="Priorità")
    
    # Statistiche
    times_applied = models.IntegerField(default=0, verbose_name="Volte Applicata")
    last_applied = models.DateTimeField(null=True, blank=True, verbose_name="Ultima Applicazione")
    
    # Metadati
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Regola di Sincronizzazione"
        verbose_name_plural = "Regole di Sincronizzazione"
        ordering = ['priority', 'name']
    
    def __str__(self):
        return f"{self.supplier.name} - {self.name}"


class SyncError(models.Model):
    """Errori dettagliati durante le sincronizzazioni"""
    
    ERROR_TYPES = [
        ('API_ERROR', 'Errore API'),
        ('PARSING_ERROR', 'Errore Parsing'),
        ('VALIDATION_ERROR', 'Errore Validazione'),
        ('MAPPING_ERROR', 'Errore Mapping'),
        ('WOOCOMMERCE_ERROR', 'Errore WooCommerce'),
        ('SYSTEM_ERROR', 'Errore Sistema'),
    ]
    
    SEVERITY_LEVELS = [
        ('LOW', 'Basso'),
        ('MEDIUM', 'Medio'),
        ('HIGH', 'Alto'),
        ('CRITICAL', 'Critico'),
    ]
    
    # Riferimenti
    sync_task = models.ForeignKey(SyncTask, null=True, blank=True, on_delete=models.CASCADE, related_name='errors')
    supplier = models.ForeignKey(Supplier, on_delete=models.CASCADE, related_name='sync_errors')
    
    # Errore
    error_type = models.CharField(max_length=20, choices=ERROR_TYPES, verbose_name="Tipo Errore")
    severity = models.CharField(max_length=10, choices=SEVERITY_LEVELS, default='MEDIUM', verbose_name="Severità")
    
    # Dettagli
    error_code = models.CharField(max_length=50, blank=True, verbose_name="Codice Errore")
    error_message = models.TextField(verbose_name="Messaggio Errore")
    
    # Contesto
    context_data = models.JSONField(default=dict, blank=True, verbose_name="Dati Contesto")
    stack_trace = models.TextField(blank=True, verbose_name="Stack Trace")
    
    # Identificatori oggetto con errore
    object_type = models.CharField(max_length=50, blank=True, verbose_name="Tipo Oggetto")
    object_id = models.CharField(max_length=100, blank=True, verbose_name="ID Oggetto")
    
    # Stato
    is_resolved = models.BooleanField(default=False, verbose_name="Risolto")
    resolution_notes = models.TextField(blank=True, verbose_name="Note Risoluzione")
    resolved_at = models.DateTimeField(null=True, blank=True, verbose_name="Risolto il")
    
    # Metadati
    occurred_at = models.DateTimeField(default=timezone.now, verbose_name="Occorso il")
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = "Errore di Sincronizzazione"
        verbose_name_plural = "Errori di Sincronizzazione"
        ordering = ['-occurred_at']
    
    def __str__(self):
        return f"{self.supplier.name} - {self.get_error_type_display()} - {self.error_message[:50]}"
    
    def mark_resolved(self, notes=''):
        """Marca l'errore come risolto"""
        self.is_resolved = True
        self.resolved_at = timezone.now()
        if notes:
            self.resolution_notes = notes
        self.save()