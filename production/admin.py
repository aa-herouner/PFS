from django.contrib import admin

from .models import EggProduction, WeightRecord


@admin.register(EggProduction)
class EggProductionAdmin(admin.ModelAdmin):
    list_display = ('date', 'batch', 'eggs_collected', 'eggs_damaged')
    list_filter = ('batch',)


@admin.register(WeightRecord)
class WeightRecordAdmin(admin.ModelAdmin):
    list_display = ('date', 'batch', 'sample_size', 'average_weight')
    list_filter = ('batch',)
