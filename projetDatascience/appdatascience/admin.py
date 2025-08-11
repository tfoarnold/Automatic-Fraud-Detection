from django.contrib import admin
from .models import CustomUser, Transaction, Role

@admin.register(Role)
class RoleAdmin(admin.ModelAdmin):
    list_display = ['name']
    search_fields = ['name']

@admin.register(CustomUser)
class CustomUserAdmin(admin.ModelAdmin):
    list_display = ['name', 'phone', 'role', 'is_active', 'date_joined']
    list_filter = ['role', 'is_active', 'is_staff']
    search_fields = ['name', 'phone']
    readonly_fields = ['date_joined']

@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = ['reference', 'type', 'amount', 'origin', 'destination', 'result_predicted', 'date_enregistrement']
    list_filter = ['type', 'result_predicted', 'is_verified']
    search_fields = ['reference', 'origin__name', 'destination__name']
    readonly_fields = ['reference', 'date_enregistrement']
    
    fieldsets = (
        ('Transaction', {
            'fields': ('reference', 'type', 'step', 'date_enregistrement')
        }),
        ('Parties', {
            'fields': ('origin', 'destination')
        }),
        ('Montants', {
            'fields': ('amount', 'oldbalanceOrg', 'newbalanceOrig', 'oldbalanceDest', 'newbalanceDest')
        }),
        ('Détection Fraude', {
            'fields': ('result_predicted', 'confidence_score', 'is_verified', 'fraud_flag_reason')
        }),
    )