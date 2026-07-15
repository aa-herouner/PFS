from datetime import date, timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.urls import reverse

from core.models import Breed, FeedType
from feed.models import FeedConsumption
from inventory.models import Batch

from .models import EggProduction, WeightRecord
from .services import feed_conversion_ratio, total_weight_gain

User = get_user_model()

_seq = 0


def make_user(username, role):
    return User.objects.create_user(username=username, password='pass12345!', role=role)


def make_batch(bird_type='LAYER', qty=200, age_days=100):
    global _seq
    _seq += 1
    breed = Breed.objects.create(name=f'Br{_seq}', bird_type=bird_type)
    return Batch.objects.create(
        batch_code=f'P{_seq}', breed=breed, bird_type=bird_type,
        date_acquired=date.today() - timedelta(days=age_days),
        initial_quantity=qty, unit_cost='2.00',
    )


class EggProductionTests(TestCase):
    def test_crates(self):
        b = make_batch('LAYER', qty=200)
        e = EggProduction.objects.create(batch=b, date=date.today(), eggs_collected=150)
        self.assertEqual(e.crates, Decimal('5'))

    def test_hen_day_percentage(self):
        b = make_batch('LAYER', qty=200)
        e = EggProduction.objects.create(batch=b, date=date.today(), eggs_collected=150)
        # 150/200*100 = 75.00
        self.assertEqual(e.hen_day_percentage, Decimal('75.00'))

    def test_damaged_cannot_exceed_collected(self):
        b = make_batch('LAYER')
        e = EggProduction(batch=b, date=date.today(), eggs_collected=10, eggs_damaged=20)
        with self.assertRaises(ValidationError):
            e.full_clean()

    def test_future_date_rejected(self):
        b = make_batch('LAYER')
        e = EggProduction(batch=b, date=date.today() + timedelta(days=1), eggs_collected=10)
        with self.assertRaises(ValidationError):
            e.full_clean()


class WeightRecordTests(TestCase):
    def test_positive_validation(self):
        b = make_batch('BROILER')
        w = WeightRecord(batch=b, date=date.today(), sample_size=0, average_weight=Decimal('1'))
        with self.assertRaises(ValidationError):
            w.full_clean()

    def test_weight_gain(self):
        b = make_batch('BROILER', qty=100)
        WeightRecord.objects.create(batch=b, date=date.today() - timedelta(days=14),
                                    sample_size=10, average_weight=Decimal('0.400'))
        WeightRecord.objects.create(batch=b, date=date.today(),
                                    sample_size=10, average_weight=Decimal('1.400'))
        # gain per bird = 1.0 kg × 100 birds = 100 kg
        self.assertEqual(total_weight_gain(b), Decimal('100.000'))


class FCRTests(TestCase):
    def _feed(self, batch, kg):
        ft = FeedType.objects.create(name=f'F{batch.pk}', category='LAYER_MASH', unit_cost='1')
        FeedConsumption.objects.create(batch=batch, feed_type=ft, date=date.today(),
                                       quantity_kg=Decimal(str(kg)))

    def test_layer_fcr_feed_per_dozen(self):
        b = make_batch('LAYER', qty=200)
        self._feed(b, 120)
        EggProduction.objects.create(batch=b, date=date.today(), eggs_collected=240)  # 20 dozen
        # 120 kg / 20 dozen = 6.0
        self.assertEqual(feed_conversion_ratio(b), Decimal('6.000'))

    def test_broiler_fcr_feed_per_gain(self):
        b = make_batch('BROILER', qty=100)
        self._feed(b, 200)
        WeightRecord.objects.create(batch=b, date=date.today() - timedelta(days=14),
                                    sample_size=10, average_weight=Decimal('0.400'))
        WeightRecord.objects.create(batch=b, date=date.today(),
                                    sample_size=10, average_weight=Decimal('1.400'))
        # 200 kg feed / 100 kg gain = 2.0
        self.assertEqual(feed_conversion_ratio(b), Decimal('2.000'))

    def test_fcr_none_without_data(self):
        b = make_batch('LAYER')
        self.assertIsNone(feed_conversion_ratio(b))


class ProductionEntryRoutingTests(TestCase):
    def setUp(self):
        make_user('att', User.Role.ATTENDANT)
        self.client.login(username='att', password='pass12345!')

    def test_layer_batch_gets_egg_form(self):
        b = make_batch('LAYER')
        resp = self.client.get(reverse('production_add', args=[b.pk]))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'eggs_collected')
        self.assertNotContains(resp, 'average_weight')

    def test_broiler_batch_gets_weight_form(self):
        b = make_batch('BROILER')
        resp = self.client.get(reverse('production_add', args=[b.pk]))
        self.assertContains(resp, 'average_weight')
        self.assertNotContains(resp, 'eggs_collected')

    def test_attendant_can_record_eggs(self):
        b = make_batch('LAYER', qty=200)
        resp = self.client.post(reverse('production_add', args=[b.pk]), {
            'date': date.today().isoformat(), 'eggs_collected': 180,
            'eggs_damaged': 5, 'notes': '',
        })
        self.assertRedirects(resp, reverse('batch_detail', args=[b.pk]))
        self.assertEqual(b.egg_production.count(), 1)

    def test_attendant_can_record_weight(self):
        b = make_batch('BROILER')
        resp = self.client.post(reverse('production_add', args=[b.pk]), {
            'date': date.today().isoformat(), 'sample_size': 10,
            'average_weight': '1.250', 'notes': '',
        })
        self.assertRedirects(resp, reverse('batch_detail', args=[b.pk]))
        self.assertEqual(b.weight_records.count(), 1)


class ProductionEditDeleteTests(TestCase):
    def setUp(self):
        make_user('mgr', User.Role.MANAGER)
        make_user('att', User.Role.ATTENDANT)

    def test_manager_can_edit_egg_record(self):
        b = make_batch('LAYER', qty=200)
        e = EggProduction.objects.create(batch=b, date=date.today(), eggs_collected=150)
        self.client.login(username='mgr', password='pass12345!')
        resp = self.client.post(reverse('egg_edit', args=[e.pk]), {
            'date': date.today().isoformat(), 'eggs_collected': 190,
            'eggs_damaged': 2, 'notes': '',
        })
        self.assertRedirects(resp, reverse('batch_detail', args=[b.pk]))
        e.refresh_from_db()
        self.assertEqual(e.eggs_collected, 190)

    def test_manager_can_delete_egg_record(self):
        b = make_batch('LAYER', qty=200)
        e = EggProduction.objects.create(batch=b, date=date.today(), eggs_collected=150)
        self.client.login(username='mgr', password='pass12345!')
        resp = self.client.post(reverse('egg_delete', args=[e.pk]))
        self.assertRedirects(resp, reverse('batch_detail', args=[b.pk]))
        self.assertFalse(EggProduction.objects.filter(pk=e.pk).exists())

    def test_manager_can_edit_and_delete_weight(self):
        b = make_batch('BROILER')
        w = WeightRecord.objects.create(batch=b, date=date.today(),
                                        sample_size=10, average_weight='1.200')
        self.client.login(username='mgr', password='pass12345!')
        resp = self.client.post(reverse('weight_edit', args=[w.pk]), {
            'date': date.today().isoformat(), 'sample_size': 12,
            'average_weight': '1.400', 'notes': '',
        })
        self.assertRedirects(resp, reverse('batch_detail', args=[b.pk]))
        w.refresh_from_db()
        self.assertEqual(w.average_weight, Decimal('1.400'))
        resp = self.client.post(reverse('weight_delete', args=[w.pk]))
        self.assertFalse(WeightRecord.objects.filter(pk=w.pk).exists())

    def test_attendant_cannot_edit_or_delete(self):
        b = make_batch('LAYER', qty=200)
        e = EggProduction.objects.create(batch=b, date=date.today(), eggs_collected=150)
        self.client.login(username='att', password='pass12345!')
        self.assertEqual(self.client.get(reverse('egg_edit', args=[e.pk])).status_code, 403)
        self.assertEqual(self.client.get(reverse('egg_delete', args=[e.pk])).status_code, 403)
