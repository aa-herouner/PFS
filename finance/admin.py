from django.contrib import admin

from .models import Transaction


@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = ('date', 'type', 'amount', 'source', 'batch', 'is_bird_sale')
    list_filter = ('type', 'source', 'is_bird_sale')
    search_fields = ('party', 'description')
