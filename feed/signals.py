"""Keep an EXPENSE finance.Transaction in sync with each FeedPurchase.

A FeedPurchase owns exactly one auto-created expense transaction
(source=FEED). Creating/editing a purchase upserts it; deleting the purchase
cascades to delete it (via the OneToOne on Transaction). This enforces the
plan's 'no double entry' rule — feed costs appear in finance automatically and
are read-only there.
"""
from django.db.models.signals import post_save
from django.dispatch import receiver

from finance.models import Transaction

from .models import FeedPurchase


@receiver(post_save, sender=FeedPurchase)
def sync_feed_expense(sender, instance, **kwargs):
    Transaction.objects.update_or_create(
        feed_purchase=instance,
        defaults={
            'type': Transaction.Type.EXPENSE,
            'source': Transaction.Source.FEED,
            'date': instance.date,
            'amount': instance.total_cost,
            'quantity': instance.quantity,
            'unit_price': instance.unit_cost,
            'party': instance.supplier,
            'description': f'Feed purchase: {instance.feed_type}',
            'created_by': instance.created_by,
            'updated_by': instance.updated_by,
        },
    )
