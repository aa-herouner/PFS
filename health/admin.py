from django.contrib import admin

from .models import HealthRecord, VaccinationSchedule


@admin.register(HealthRecord)
class HealthRecordAdmin(admin.ModelAdmin):
    list_display = ('date', 'batch', 'record_type', 'name', 'cost')
    list_filter = ('record_type',)
    search_fields = ('name',)


@admin.register(VaccinationSchedule)
class VaccinationScheduleAdmin(admin.ModelAdmin):
    list_display = ('vaccine_name', 'day_of_age', 'bird_type_display', 'breed')
