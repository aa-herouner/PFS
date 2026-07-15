from datetime import date, timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from core.models import Breed, FeedType, IncomeCategory
from feed.models import FeedPurchase
from health.models import VaccinationSchedule
from inventory.models import Batch, MortalityRecord
from production.models import EggProduction

from . import services

User = get_user_model()

_seq = 0


def make_user(username, role):
    return User.objects.create_user(username=username, password='pass12345!', role=role)


def make_batch(bird_type='LAYER', qty=200, age_days=100, status='ACTIVE'):
    global _seq
    _seq += 1
    breed = Breed.objects.create(name=f'Br{_seq}', bird_type=bird_type)
    return Batch.objects.create(
        batch_code=f'D{_seq}', breed=breed, bird_type=bird_type,
        date_acquired=date.today() - timedelta(days=age_days),
        initial_quantity=qty, unit_cost='2.00', status=status,
    )


class KpiTests(TestCase):
    def test_live_birds_and_mortality_rate(self):
        b = make_batch('LAYER', qty=200)
        MortalityRecord.objects.create(batch=b, date=date.today(), quantity=20)
        k = services.kpis()
        self.assertEqual(k['total_birds'], 180)
        self.assertEqual(k['active_batches'], 1)
        self.assertEqual(k['mortality_rate'], Decimal('10.00'))  # 20/200

    def test_eggs_today_and_week(self):
        b = make_batch('LAYER', qty=200)
        EggProduction.objects.create(batch=b, date=date.today(), eggs_collected=100)
        EggProduction.objects.create(batch=b, date=date.today() - timedelta(days=3),
                                     eggs_collected=90)
        k = services.kpis()
        self.assertEqual(k['eggs_today'], 100)
        self.assertEqual(k['eggs_week'], 190)

    def test_sold_batch_excluded_from_live_birds(self):
        make_batch('LAYER', qty=100, status='ACTIVE')
        make_batch('LAYER', qty=500, status='SOLD')
        self.assertEqual(services.kpis()['total_birds'], 100)


class AlertTests(TestCase):
    def test_low_feed_stock_alert(self):
        ft = FeedType.objects.create(name='Starter', category='STARTER', unit_cost='1')
        FeedPurchase.objects.create(feed_type=ft, date=date.today(), quantity='10', unit_cost='1')
        msgs = [a['message'] for a in services.alerts()]
        self.assertTrue(any('Low feed stock' in m for m in msgs))

    def test_overdue_vaccination_alert(self):
        make_batch('BROILER', qty=100, age_days=30)
        VaccinationSchedule.objects.create(vaccine_name='Gumboro', day_of_age=14,
                                           bird_type='BROILER')
        msgs = [a['message'] for a in services.alerts()]
        self.assertTrue(any('Vaccination overdue' in m for m in msgs))

    def test_mortality_spike_alert(self):
        b = make_batch('BROILER', qty=1000, age_days=10)
        # 30 of ~1000 today = 3% ≥ 2% threshold
        MortalityRecord.objects.create(batch=b, date=date.today(), quantity=30)
        msgs = [a['message'] for a in services.alerts()]
        self.assertTrue(any('Mortality spike' in m for m in msgs))

    def test_no_spike_below_threshold(self):
        b = make_batch('BROILER', qty=1000, age_days=10)
        MortalityRecord.objects.create(batch=b, date=date.today(), quantity=5)  # 0.5%
        msgs = [a['message'] for a in services.alerts()]
        self.assertFalse(any('Mortality spike' in m for m in msgs))


class DashboardViewTests(TestCase):
    def test_requires_login(self):
        resp = self.client.get(reverse('dashboard'))
        self.assertEqual(resp.status_code, 302)

    def test_renders_for_any_role(self):
        make_user('att', User.Role.ATTENDANT)
        self.client.login(username='att', password='pass12345!')
        resp = self.client.get(reverse('dashboard'))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'Dashboard')
