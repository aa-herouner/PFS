from django.contrib import admin

from .models import Batch, MortalityRecord


class MortalityInline(admin.TabularInline):
    model = MortalityRecord
    extra = 0


@admin.register(Batch)
class BatchAdmin(admin.ModelAdmin):
    list_display = ('batch_code', 'breed', 'bird_type', 'status', 'initial_quantity', 'date_acquired')
    list_filter = ('bird_type', 'status')
    search_fields = ('batch_code', 'supplier')
    inlines = [MortalityInline]


@admin.register(MortalityRecord)
class MortalityRecordAdmin(admin.ModelAdmin):
    list_display = ('batch', 'date', 'record_type', 'quantity')
    list_filter = ('record_type',)
