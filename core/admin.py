from django.contrib import admin

from .models import Breed, ExpenseCategory, FeedType, IncomeCategory, Pen


@admin.register(Breed)
class BreedAdmin(admin.ModelAdmin):
    list_display = ('name', 'bird_type')
    list_filter = ('bird_type',)


@admin.register(Pen)
class PenAdmin(admin.ModelAdmin):
    list_display = ('name', 'capacity')


@admin.register(FeedType)
class FeedTypeAdmin(admin.ModelAdmin):
    list_display = ('name', 'category', 'unit', 'unit_cost')
    list_filter = ('category',)


@admin.register(ExpenseCategory)
class ExpenseCategoryAdmin(admin.ModelAdmin):
    list_display = ('name',)


@admin.register(IncomeCategory)
class IncomeCategoryAdmin(admin.ModelAdmin):
    list_display = ('name',)
