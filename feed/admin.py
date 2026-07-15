from django.contrib import admin

from .models import FeedConsumption, FeedPurchase


@admin.register(FeedPurchase)
class FeedPurchaseAdmin(admin.ModelAdmin):
    list_display = ('date', 'feed_type', 'quantity', 'unit_cost', 'supplier')
    list_filter = ('feed_type',)


@admin.register(FeedConsumption)
class FeedConsumptionAdmin(admin.ModelAdmin):
    list_display = ('date', 'batch', 'feed_type', 'quantity_kg')
    list_filter = ('feed_type',)
