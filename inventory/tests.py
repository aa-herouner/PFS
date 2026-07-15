from datetime import date, timedelta

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.urls import reverse

from core.models import Breed, Pen

from .models import Batch, MortalityRecord

User = get_user_model()


def make_user(username, role):
    return User.objects.create_user(username=username, password='pass12345!', role=role)


def make_batch(**overrides):
    breed = Breed.objects.create(name='Ross 308', bird_type='BROILER')
    defaults = dict(
        batch_code='B001', breed=breed, bird_type='BROILER',
        date_acquired=date.today() - timedelta(days=21),
        initial_quantity=1000, unit_cost='2.50',
    )
    defaults.update(overrides)
    return Batch.objects.create(**defaults)


class BatchDerivedTests(TestCase):
    def test_current_quantity_reduces_with_mortality_and_culls(self):
        batch = make_batch(initial_quantity=1000)
        MortalityRecord.objects.create(batch=batch, date=date.today(), quantity=30,
                                       record_type='MORTALITY')
        MortalityRecord.objects.create(batch=batch, date=date.today(), quantity=10,
                                       record_type='CULL')
        self.assertEqual(batch.total_mortality, 30)
        self.assertEqual(batch.total_culls, 10)
        self.assertEqual(batch.current_quantity, 960)

    def test_current_quantity_never_negative(self):
        batch = make_batch(initial_quantity=10)
        # can't exceed via clean(), but property must still floor at 0 if data drifts
        MortalityRecord.objects.create(batch=batch, date=date.today(), quantity=10)
        self.assertEqual(batch.current_quantity, 0)

    def test_age_in_days_and_weeks(self):
        batch = make_batch(date_acquired=date.today() - timedelta(days=21))
        self.assertEqual(batch.age_in_days, 21)
        self.assertEqual(batch.age_in_weeks, 3)

    def test_mortality_rate(self):
        batch = make_batch(initial_quantity=200)
        MortalityRecord.objects.create(batch=batch, date=date.today(), quantity=10)
        MortalityRecord.objects.create(batch=batch, date=date.today(), quantity=10,
                                       record_type='CULL')
        # (10 + 10) / 200 * 100 = 10.0
        self.assertEqual(batch.mortality_rate, 10.0)

    def test_mortality_rate_zero_initial(self):
        batch = make_batch(initial_quantity=1)
        self.assertEqual(batch.mortality_rate, 0.0)

    def test_total_cost(self):
        batch = make_batch(initial_quantity=1000, unit_cost='2.50')
        self.assertEqual(batch.total_cost, 2500)


class MortalityValidationTests(TestCase):
    def test_quantity_exceeding_current_is_rejected(self):
        batch = make_batch(initial_quantity=100)
        rec = MortalityRecord(batch=batch, date=date.today(), quantity=150)
        with self.assertRaises(ValidationError) as cm:
            rec.full_clean()
        self.assertIn('quantity', cm.exception.error_dict)

    def test_future_date_rejected(self):
        batch = make_batch()
        rec = MortalityRecord(batch=batch, date=date.today() + timedelta(days=1), quantity=1)
        with self.assertRaises(ValidationError) as cm:
            rec.full_clean()
        self.assertIn('date', cm.exception.error_dict)

    def test_edit_does_not_double_count_own_quantity(self):
        batch = make_batch(initial_quantity=100)
        rec = MortalityRecord.objects.create(batch=batch, date=date.today(), quantity=100)
        # current is now 0; editing this record to 90 must be allowed
        rec.quantity = 90
        rec.full_clean()  # should not raise

    def test_valid_record_passes(self):
        batch = make_batch(initial_quantity=100)
        rec = MortalityRecord(batch=batch, date=date.today(), quantity=5)
        rec.full_clean()  # no exception


class BatchPenCapacityTests(TestCase):
    def _make_batch_obj(self, pen, qty, code='P1'):
        breed = Breed.objects.create(name=f'Ross 308 {code}', bird_type='BROILER')
        return Batch(batch_code=code, breed=breed, bird_type='BROILER',
                     date_acquired=date.today() - timedelta(days=1),
                     initial_quantity=qty, unit_cost='2.50', pen=pen)

    def test_quantity_over_pen_capacity_rejected(self):
        pen = Pen.objects.create(name='Pen A', capacity=500)
        batch = self._make_batch_obj(pen, 600)
        with self.assertRaises(ValidationError) as cm:
            batch.full_clean()
        self.assertIn('initial_quantity', cm.exception.error_dict)

    def test_quantity_within_pen_capacity_passes(self):
        pen = Pen.objects.create(name='Pen A', capacity=500)
        batch = self._make_batch_obj(pen, 500)
        batch.full_clean()  # no exception

    def test_capacity_accounts_for_other_batches_in_pen(self):
        pen = Pen.objects.create(name='Pen A', capacity=500)
        self._make_batch_obj(pen, 300, code='P1').save()
        # 300 already placed; 250 more overflows the 500-bird pen.
        batch = self._make_batch_obj(pen, 250, code='P2')
        with self.assertRaises(ValidationError) as cm:
            batch.full_clean()
        self.assertIn('initial_quantity', cm.exception.error_dict)

    def test_no_pen_means_no_capacity_check(self):
        batch = self._make_batch_obj(None, 100000)
        batch.full_clean()  # unassigned batch: nothing to exceed


class BatchCodeGenerationTests(TestCase):
    def _breed(self, bird_type, tag):
        return Breed.objects.create(name=f'Breed {tag}', bird_type=bird_type)

    def _make(self, bird_type, tag, year=2026):
        return Batch.objects.create(
            breed=self._breed(bird_type, tag), bird_type=bird_type,
            date_acquired=date(year, 6, 1), initial_quantity=100, unit_cost='2.00')

    def test_blank_code_is_auto_generated(self):
        b = self._make('BROILER', 'a')
        self.assertEqual(b.batch_code, 'BRO-2026-001')

    def test_sequence_increments_per_type_and_year(self):
        self._make('BROILER', 'a')
        b2 = self._make('BROILER', 'b')
        self.assertEqual(b2.batch_code, 'BRO-2026-002')

    def test_prefix_and_sequence_are_per_bird_type(self):
        b_broiler = self._make('BROILER', 'a')
        b_layer = self._make('LAYER', 'b')
        b_breeder = self._make('BREEDER', 'c')
        self.assertEqual(b_broiler.batch_code, 'BRO-2026-001')
        self.assertEqual(b_layer.batch_code, 'LAY-2026-001')
        self.assertEqual(b_breeder.batch_code, 'BRE-2026-001')

    def test_sequence_is_per_year(self):
        self._make('BROILER', 'a', year=2025)
        b = self._make('BROILER', 'b', year=2026)
        self.assertEqual(b.batch_code, 'BRO-2026-001')

    def test_generated_codes_are_unique(self):
        codes = {self._make('BROILER', str(i)).batch_code for i in range(5)}
        self.assertEqual(len(codes), 5)

    def test_manual_code_is_respected(self):
        b = Batch.objects.create(
            batch_code='CUSTOM-1', breed=self._breed('LAYER', 'x'),
            bird_type='LAYER', date_acquired=date(2026, 6, 1),
            initial_quantity=100, unit_cost='2.00')
        self.assertEqual(b.batch_code, 'CUSTOM-1')


class BatchAccessTests(TestCase):
    def setUp(self):
        self.batch = make_batch()
        make_user('own', User.Role.OWNER)
        make_user('mgr', User.Role.MANAGER)
        make_user('att', User.Role.ATTENDANT)

    def test_all_roles_can_view_list_and_detail(self):
        for uname in ('own', 'mgr', 'att'):
            self.client.login(username=uname, password='pass12345!')
            self.assertEqual(self.client.get(reverse('batch_list')).status_code, 200)
            self.assertEqual(
                self.client.get(reverse('batch_detail', args=[self.batch.pk])).status_code, 200)

    def test_attendant_cannot_create_batch(self):
        self.client.login(username='att', password='pass12345!')
        self.assertEqual(self.client.get(reverse('batch_add')).status_code, 403)

    def test_manager_can_create_batch(self):
        self.client.login(username='mgr', password='pass12345!')
        self.assertEqual(self.client.get(reverse('batch_add')).status_code, 200)

    def test_attendant_can_record_mortality(self):
        self.client.login(username='att', password='pass12345!')
        url = reverse('mortality_add', args=[self.batch.pk])
        self.assertEqual(self.client.get(url).status_code, 200)
        resp = self.client.post(url, {
            'date': date.today().isoformat(), 'record_type': 'MORTALITY',
            'quantity': 5, 'cause': 'heat', 'notes': '',
        })
        self.assertRedirects(resp, reverse('batch_detail', args=[self.batch.pk]))
        self.assertEqual(self.batch.mortality_records.count(), 1)

    def test_overcount_mortality_via_view_is_blocked(self):
        self.client.login(username='att', password='pass12345!')
        url = reverse('mortality_add', args=[self.batch.pk])
        resp = self.client.post(url, {
            'date': date.today().isoformat(), 'record_type': 'MORTALITY',
            'quantity': 99999, 'cause': '', 'notes': '',
        })
        self.assertEqual(resp.status_code, 200)  # re-rendered with error
        self.assertEqual(self.batch.mortality_records.count(), 0)

    # --- flock disable (status change) -------------------------------------
    def test_manager_can_disable_flock(self):
        self.client.login(username='mgr', password='pass12345!')
        resp = self.client.post(reverse('batch_status', args=[self.batch.pk]),
                                {'status': 'DEPOPULATED'})
        self.assertRedirects(resp, reverse('batch_detail', args=[self.batch.pk]))
        self.batch.refresh_from_db()
        self.assertEqual(self.batch.status, 'DEPOPULATED')

    def test_disable_keeps_records(self):
        MortalityRecord.objects.create(batch=self.batch, date=date.today(), quantity=3)
        self.client.login(username='own', password='pass12345!')
        self.client.post(reverse('batch_status', args=[self.batch.pk]), {'status': 'SOLD'})
        self.batch.refresh_from_db()
        self.assertEqual(self.batch.status, 'SOLD')
        self.assertEqual(self.batch.mortality_records.count(), 1)  # history intact

    def test_invalid_status_rejected(self):
        self.client.login(username='own', password='pass12345!')
        self.client.post(reverse('batch_status', args=[self.batch.pk]), {'status': 'BOGUS'})
        self.batch.refresh_from_db()
        self.assertEqual(self.batch.status, 'ACTIVE')  # unchanged

    def test_attendant_cannot_change_status(self):
        self.client.login(username='att', password='pass12345!')
        resp = self.client.post(reverse('batch_status', args=[self.batch.pk]),
                                {'status': 'SOLD'})
        self.assertEqual(resp.status_code, 403)

    # --- mortality edit / delete -------------------------------------------
    def test_manager_can_edit_mortality(self):
        rec = MortalityRecord.objects.create(batch=self.batch, date=date.today(), quantity=5)
        self.client.login(username='mgr', password='pass12345!')
        resp = self.client.post(reverse('mortality_edit', args=[rec.pk]), {
            'date': date.today().isoformat(), 'record_type': 'MORTALITY',
            'quantity': 8, 'cause': 'updated', 'notes': '',
        })
        self.assertRedirects(resp, reverse('batch_detail', args=[self.batch.pk]))
        rec.refresh_from_db()
        self.assertEqual(rec.quantity, 8)

    def test_deleting_mortality_restores_current_quantity(self):
        start = self.batch.current_quantity
        rec = MortalityRecord.objects.create(batch=self.batch, date=date.today(), quantity=10)
        self.assertEqual(self.batch.current_quantity, start - 10)
        self.client.login(username='own', password='pass12345!')
        resp = self.client.post(reverse('mortality_delete', args=[rec.pk]))
        self.assertRedirects(resp, reverse('batch_detail', args=[self.batch.pk]))
        self.assertEqual(self.batch.current_quantity, start)  # count restored

    def test_attendant_cannot_delete_mortality(self):
        rec = MortalityRecord.objects.create(batch=self.batch, date=date.today(), quantity=5)
        self.client.login(username='att', password='pass12345!')
        self.assertEqual(
            self.client.get(reverse('mortality_delete', args=[rec.pk])).status_code, 403)
        self.assertEqual(
            self.client.get(reverse('mortality_edit', args=[rec.pk])).status_code, 403)


class BatchListFilterTests(TestCase):
    def setUp(self):
        self.batch = make_batch(batch_code='LAYER-1', bird_type='LAYER')
        make_user('own', User.Role.OWNER)
        self.client.login(username='own', password='pass12345!')

    def test_search_by_code(self):
        resp = self.client.get(reverse('batch_list'), {'q': 'LAYER'})
        self.assertContains(resp, 'LAYER-1')

    def test_filter_by_type_excludes_others(self):
        resp = self.client.get(reverse('batch_list'), {'bird_type': 'BROILER'})
        self.assertNotContains(resp, 'LAYER-1')
