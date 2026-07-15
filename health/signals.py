"""Keep an EXPENSE finance.Transaction in sync with each costed HealthRecord.

Only records with cost > 0 have a transaction. If a record is edited so its
cost becomes 0, its transaction is removed. Deleting the record cascades to
delete the transaction (via the OneToOne on Transaction).
"""
from decimal import Decimal

from django.db.models.signals import post_save
from django.dispatch import receiver

from finance.models import Transaction

from .models import HealthRecord


@receiver(post_save, sender=HealthRecord)
def sync_health_expense(sender, instance, **kwargs):
    if instance.cost and Decimal(str(instance.cost)) > 0:
        Transaction.objects.update_or_create(
            health_record=instance,
            defaults={
                'type': Transaction.Type.EXPENSE,
                'source': Transaction.Source.HEALTH,
                'date': instance.date,
                'amount': instance.cost,
                'batch': instance.batch,
                'description': f'{instance.get_record_type_display()}: {instance.name}',
                'created_by': instance.created_by,
                'updated_by': instance.updated_by,
            },
        )
    else:
        # Cost is zero/none — ensure no dangling transaction remains.
        Transaction.objects.filter(health_record=instance).delete()
