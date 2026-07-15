"""Load demonstration data in one command.

    python manage.py seed_demo            # create demo data (skips if present)
    python manage.py seed_demo --fresh    # wipe demo data first, then create

Creates one user per role, reference data, and a layer + a broiler batch each
with ~3 weeks of mortality, feed, health and production records plus a few
sales. Records are created through the models so derived properties and the
feed/health→finance expense signals fire exactly as in normal use.
"""
from datetime import date, timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db import transaction

from core.models import (
    Breed,
    ExpenseCategory,
    FeedType,
    IncomeCategory,
    Pen,
)
from feed.models import FeedConsumption, FeedPurchase
from finance.models import Transaction
from health.models import HealthRecord, VaccinationSchedule
from inventory.models import Batch, MortalityRecord
from production.models import EggProduction, WeightRecord

User = get_user_model()

LAYER_CODE = 'DEMO-LAYER-01'
BROILER_CODE = 'DEMO-BROILER-01'


class Command(BaseCommand):
    help = 'Load demonstration data (idempotent; use --fresh to reset it).'

    def add_arguments(self, parser):
        parser.add_argument('--fresh', action='store_true',
                            help='Delete existing demo data before creating.')

    @transaction.atomic
    def handle(self, *args, **options):
        if options['fresh']:
            self._wipe()
            self.stdout.write('Wiped existing demo data.')

        if Batch.objects.filter(batch_code__in=[LAYER_CODE, BROILER_CODE]).exists():
            self.stdout.write(self.style.WARNING(
                'Demo data already present. Use --fresh to recreate.'))
            return

        owner = self._user('demo_owner', User.Role.OWNER)
        self._user('demo_manager', User.Role.MANAGER)
        self._user('demo_attendant', User.Role.ATTENDANT)

        layer_breed = self._breed('Isa Brown', 'LAYER')
        broiler_breed = self._breed('Ross 308', 'BROILER')
        pen_a = self._pen('Pen A', 1000)
        pen_b = self._pen('Pen B', 1500)
        layer_feed = self._feed_type('Layer Mash', 'LAYER_MASH', '95.00')
        broiler_feed = self._feed_type('Broiler Finisher', 'FINISHER', '110.00')
        egg_income = IncomeCategory.objects.get_or_create(name='Egg sales')[0]
        bird_income = IncomeCategory.objects.get_or_create(name='Bird sales')[0]
        misc_expense = ExpenseCategory.objects.get_or_create(name='Miscellaneous')[0]

        VaccinationSchedule.objects.get_or_create(
            vaccine_name='Newcastle (Lasota)', day_of_age=7,
            defaults={'bird_type': 'BROILER'})
        VaccinationSchedule.objects.get_or_create(
            vaccine_name='Gumboro', day_of_age=14,
            defaults={'bird_type': 'BROILER'})

        # Stock the store: purchases feed both batches (also posts expenses).
        FeedPurchase.objects.create(
            feed_type=layer_feed, date=self._days_ago(25), quantity=Decimal('500'),
            unit_cost=Decimal('95'), supplier='AgriFeeds Ltd',
            created_by=owner, updated_by=owner)
        FeedPurchase.objects.create(
            feed_type=broiler_feed, date=self._days_ago(25), quantity=Decimal('400'),
            unit_cost=Decimal('110'), supplier='AgriFeeds Ltd',
            created_by=owner, updated_by=owner)

        layer = self._layer_batch(owner, layer_breed, pen_a, layer_feed, egg_income)
        broiler = self._broiler_batch(owner, broiler_breed, pen_b, broiler_feed,
                                      bird_income, misc_expense)

        self.stdout.write(self.style.SUCCESS(
            f'Demo data loaded: layer "{layer.batch_code}" '
            f'({layer.current_quantity} birds) and broiler "{broiler.batch_code}" '
            f'({broiler.current_quantity} birds). '
            f'Users: demo_owner / demo_manager / demo_attendant (password: demo1234!).'))

    # -- builders -----------------------------------------------------------
    def _layer_batch(self, owner, breed, pen, feed, egg_income):
        batch = Batch.objects.create(
            batch_code=LAYER_CODE, breed=breed, bird_type='LAYER',
            supplier='Prime Chicks', date_acquired=self._days_ago(140),
            initial_quantity=500, unit_cost=Decimal('4.50'), pen=pen,
            created_by=owner, updated_by=owner)
        for i in range(21):
            d = self._days_ago(20 - i)
            if i % 5 == 0:
                MortalityRecord.objects.create(
                    batch=batch, date=d, quantity=1, record_type='MORTALITY',
                    cause='Natural', created_by=owner, updated_by=owner)
            FeedConsumption.objects.create(
                batch=batch, feed_type=feed, date=d, quantity_kg=Decimal('20'),
                created_by=owner, updated_by=owner)
            EggProduction.objects.create(
                batch=batch, date=d, eggs_collected=380 + i * 2, eggs_damaged=5,
                created_by=owner, updated_by=owner)
        HealthRecord.objects.create(
            batch=batch, date=self._days_ago(18), record_type='MEDICATION',
            name='Multivitamin', dosage='per water', administered_by='demo_attendant',
            cost=Decimal('300'), created_by=owner, updated_by=owner)
        # An egg sale.
        Transaction.objects.create(
            type='INCOME', income_category=egg_income, date=self._days_ago(2),
            amount=Decimal('4500'), quantity=Decimal('150'), unit_price=Decimal('30'),
            batch=batch, party='Local market', description='Crates of eggs',
            created_by=owner, updated_by=owner)
        return batch

    def _broiler_batch(self, owner, breed, pen, feed, bird_income, misc_expense):
        batch = Batch.objects.create(
            batch_code=BROILER_CODE, breed=breed, bird_type='BROILER',
            supplier='Prime Chicks', date_acquired=self._days_ago(28),
            initial_quantity=400, unit_cost=Decimal('2.20'), pen=pen,
            created_by=owner, updated_by=owner)
        for i in range(21):
            d = self._days_ago(20 - i)
            if i % 4 == 0:
                MortalityRecord.objects.create(
                    batch=batch, date=d, quantity=2, record_type='MORTALITY',
                    cause='Heat', created_by=owner, updated_by=owner)
            FeedConsumption.objects.create(
                batch=batch, feed_type=feed, date=d, quantity_kg=Decimal('15'),
                created_by=owner, updated_by=owner)
        # Weekly sample weights, climbing.
        for wk, wt in enumerate(['0.180', '0.550', '1.100', '1.800']):
            WeightRecord.objects.create(
                batch=batch, date=self._days_ago(21 - wk * 7), sample_size=20,
                average_weight=Decimal(wt), created_by=owner, updated_by=owner)
        HealthRecord.objects.create(
            batch=batch, date=self._days_ago(21), record_type='VACCINATION',
            name='Newcastle (Lasota)', administered_by='demo_attendant',
            cost=Decimal('0'), created_by=owner, updated_by=owner)
        HealthRecord.objects.create(
            batch=batch, date=self._days_ago(19), record_type='MEDICATION',
            name='Antibiotic', dosage='1ml/L', administered_by='demo_attendant',
            cost=Decimal('450'), created_by=owner, updated_by=owner)
        # A bird sale that reduces the flock.
        Transaction.objects.create(
            type='INCOME', income_category=bird_income, date=self._days_ago(1),
            amount=Decimal('12000'), quantity=Decimal('50'), unit_price=Decimal('240'),
            batch=batch, is_bird_sale=True, party='Wholesaler',
            description='Live broilers', created_by=owner, updated_by=owner)
        return batch

    # -- helpers ------------------------------------------------------------
    @staticmethod
    def _days_ago(n):
        return date.today() - timedelta(days=n)

    def _user(self, username, role):
        u, created = User.objects.get_or_create(
            username=username, defaults={'role': role})
        u.role = role
        if created:
            u.set_password('demo1234!')
        u.save()
        return u

    def _breed(self, name, bird_type):
        return Breed.objects.get_or_create(
            name=name, defaults={'bird_type': bird_type})[0]

    def _pen(self, name, capacity):
        return Pen.objects.get_or_create(
            name=name, defaults={'capacity': capacity})[0]

    def _feed_type(self, name, category, unit_cost):
        return FeedType.objects.get_or_create(
            name=name, defaults={'category': category, 'unit_cost': Decimal(unit_cost)})[0]

    def _wipe(self):
        # Delete demo batches (cascades records) and demo-only reference/users.
        # Transactions referencing demo batches: bird-sale/manual ones are
        # deleted here; feed/health-sourced ones cascade with their source.
        batches = Batch.objects.filter(batch_code__in=[LAYER_CODE, BROILER_CODE])
        Transaction.objects.filter(batch__in=batches).delete()
        FeedPurchase.objects.filter(
            feed_type__name__in=['Layer Mash', 'Broiler Finisher']).delete()
        batches.delete()
        FeedType.objects.filter(name__in=['Layer Mash', 'Broiler Finisher']).delete()
        Breed.objects.filter(name__in=['Isa Brown', 'Ross 308']).delete()
        Pen.objects.filter(name__in=['Pen A', 'Pen B']).delete()
        VaccinationSchedule.objects.filter(
            vaccine_name__in=['Newcastle (Lasota)', 'Gumboro']).delete()
        User.objects.filter(
            username__in=['demo_owner', 'demo_manager', 'demo_attendant']).delete()
