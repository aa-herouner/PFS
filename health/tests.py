from datetime import date, timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.urls import reverse

from core.models import Breed
from finance.models import Transaction
from inventory.models import Batch

from .models import HealthRecord, VaccinationSchedule
from .services import batch_vaccination_status, due_vaccinations

User = get_user_model()


def make_user(username, role):
    return User.objects.create_user(username=username, password='pass12345!', role=role)


_batch_seq = 0


def make_batch(age_days=10, bird_type='BROILER', breed=None, status='ACTIVE'):
    global _batch_seq
    _batch_seq += 1
    if breed is None:
        breed = Breed.objects.create(name=f'Ross{_batch_seq}', bird_type=bird_type)
    return Batch.objects.create(
        batch_code=f'B{_batch_seq}', breed=breed, bird_type=bird_type,
        date_acquired=date.today() - timedelta(days=age_days),
        initial_quantity=500, unit_cost='2.00', status=status,
    )


class HealthExpenseTests(TestCase):
    def test_costed_record_creates_expense(self):
        batch = make_batch()
        rec = HealthRecord.objects.create(
            batch=batch, date=date.today(), record_type='MEDICATION',
            name='Antibiotic', cost='250.00')
        txn = Transaction.objects.get(health_record=rec)
        self.assertEqual(txn.type, Transaction.Type.EXPENSE)
        self.assertEqual(txn.source, Transaction.Source.HEALTH)
        self.assertEqual(txn.amount, Decimal('250.00'))
        self.assertEqual(txn.batch, batch)

    def test_zero_cost_record_creates_no_expense(self):
        batch = make_batch()
        rec = HealthRecord.objects.create(
            batch=batch, date=date.today(), record_type='VACCINATION',
            name='Gumboro', cost='0')
        self.assertFalse(Transaction.objects.filter(health_record=rec).exists())

    def test_editing_cost_to_zero_removes_expense(self):
        batch = make_batch()
        rec = HealthRecord.objects.create(
            batch=batch, date=date.today(), record_type='MEDICATION',
            name='Vitamin', cost='100')
        self.assertTrue(Transaction.objects.filter(health_record=rec).exists())
        rec.cost = Decimal('0')
        rec.save()
        self.assertFalse(Transaction.objects.filter(health_record=rec).exists())

    def test_deleting_record_removes_expense(self):
        batch = make_batch()
        rec = HealthRecord.objects.create(
            batch=batch, date=date.today(), record_type='TREATMENT',
            name='Deworm', cost='80')
        rid = rec.pk
        rec.delete()
        self.assertFalse(Transaction.objects.filter(health_record_id=rid).exists())


class HealthValidationTests(TestCase):
    def test_future_date_rejected(self):
        batch = make_batch()
        rec = HealthRecord(batch=batch, date=date.today() + timedelta(days=1),
                           record_type='MEDICATION', name='X', cost='1')
        with self.assertRaises(ValidationError):
            rec.full_clean()

    def test_negative_cost_rejected(self):
        batch = make_batch()
        rec = HealthRecord(batch=batch, date=date.today(),
                           record_type='MEDICATION', name='X', cost=Decimal('-5'))
        with self.assertRaises(ValidationError):
            rec.full_clean()


class VaccinationScheduleTests(TestCase):
    def test_overdue_when_batch_past_day_and_no_record(self):
        batch = make_batch(age_days=20, bird_type='BROILER')
        VaccinationSchedule.objects.create(vaccine_name='Gumboro', day_of_age=14,
                                           bird_type='BROILER')
        rows = batch_vaccination_status(batch)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]['status'], 'overdue')

    def test_done_when_matching_vaccination_recorded(self):
        batch = make_batch(age_days=20, bird_type='BROILER')
        VaccinationSchedule.objects.create(vaccine_name='Gumboro', day_of_age=14,
                                           bird_type='BROILER')
        HealthRecord.objects.create(batch=batch, date=date.today(),
                                    record_type='VACCINATION', name='Gumboro', cost='0')
        rows = batch_vaccination_status(batch)
        self.assertEqual(rows[0]['status'], 'done')

    def test_upcoming_when_far_from_due(self):
        batch = make_batch(age_days=2, bird_type='BROILER')
        VaccinationSchedule.objects.create(vaccine_name='Newcastle', day_of_age=21,
                                           bird_type='BROILER')
        rows = batch_vaccination_status(batch)
        self.assertEqual(rows[0]['status'], 'upcoming')

    def test_bird_type_mismatch_excluded(self):
        batch = make_batch(age_days=20, bird_type='LAYER')
        VaccinationSchedule.objects.create(vaccine_name='Broiler-only', day_of_age=14,
                                           bird_type='BROILER')
        self.assertEqual(batch_vaccination_status(batch), [])

    def test_blank_bird_type_applies_to_all(self):
        batch = make_batch(age_days=20, bird_type='LAYER')
        VaccinationSchedule.objects.create(vaccine_name='Universal', day_of_age=14,
                                           bird_type='')
        rows = batch_vaccination_status(batch)
        self.assertEqual(len(rows), 1)

    def test_multiple_bird_types_apply_to_each(self):
        # One schedule ticking both Layer and Broiler applies to both.
        layer = make_batch(age_days=20, bird_type='LAYER')
        broiler = make_batch(age_days=20, bird_type='BROILER')
        breeder = make_batch(age_days=20, bird_type='BREEDER')
        VaccinationSchedule.objects.create(vaccine_name='Newcastle', day_of_age=14,
                                           bird_type='LAYER,BROILER')
        self.assertEqual(len(batch_vaccination_status(layer)), 1)
        self.assertEqual(len(batch_vaccination_status(broiler)), 1)
        # Breeder wasn't ticked, so it's excluded.
        self.assertEqual(batch_vaccination_status(breeder), [])

    def test_bird_type_list_and_display(self):
        s = VaccinationSchedule.objects.create(vaccine_name='X', day_of_age=1,
                                               bird_type='LAYER,BROILER')
        self.assertEqual(s.bird_type_list, ['LAYER', 'BROILER'])
        self.assertEqual(s.bird_type_display, 'Layer, Broiler')
        s2 = VaccinationSchedule.objects.create(vaccine_name='Y', day_of_age=1, bird_type='')
        self.assertEqual(s2.bird_type_display, 'Any')

    def test_form_saves_checked_types_as_csv(self):
        from .forms import VaccinationScheduleForm
        form = VaccinationScheduleForm(data={
            'vaccine_name': 'Gumboro', 'day_of_age': 14,
            'bird_type': ['LAYER', 'BROILER'], 'breed': '', 'notes': '',
        })
        self.assertTrue(form.is_valid(), form.errors)
        obj = form.save()
        self.assertEqual(obj.bird_type, 'LAYER,BROILER')

    def test_due_vaccinations_only_active_batches(self):
        active = make_batch(age_days=20, bird_type='BROILER')
        sold = make_batch(age_days=20, bird_type='BROILER', status=Batch.Status.SOLD)
        VaccinationSchedule.objects.create(vaccine_name='Gumboro', day_of_age=14,
                                           bird_type='BROILER')
        alerts = due_vaccinations()
        batches = {a['batch'].pk for a in alerts}
        self.assertIn(active.pk, batches)
        self.assertNotIn(sold.pk, batches)


class HealthAccessTests(TestCase):
    def setUp(self):
        make_user('own', User.Role.OWNER)
        make_user('att', User.Role.ATTENDANT)
        self.batch = make_batch()

    def test_attendant_can_record_health(self):
        self.client.login(username='att', password='pass12345!')
        url = reverse('health_add', args=[self.batch.pk])
        self.assertEqual(self.client.get(url).status_code, 200)
        resp = self.client.post(url, {
            'date': date.today().isoformat(), 'record_type': 'MEDICATION',
            'name': 'Antibiotic', 'dosage': '1ml', 'administered_by': 'Sam',
            'cost': '150', 'notes': '',
        })
        self.assertRedirects(resp, reverse('batch_detail', args=[self.batch.pk]))
        self.assertEqual(HealthRecord.objects.count(), 1)
        self.assertEqual(Transaction.objects.filter(source='HEALTH').count(), 1)

    def test_vaccination_name_comes_from_schedule(self):
        from .forms import HealthRecordForm
        VaccinationSchedule.objects.create(vaccine_name='Gumboro', day_of_age=14,
                                           bird_type='BROILER')
        form = HealthRecordForm(batch=self.batch, data={
            'date': date.today().isoformat(), 'record_type': 'VACCINATION',
            'vaccine_choice': 'Gumboro', 'name': '', 'dosage': '',
            'administered_by': '', 'cost': '0', 'notes': '',
        })
        self.assertTrue(form.is_valid(), form.errors)
        rec = form.save()
        self.assertEqual(rec.name, 'Gumboro')

    def test_vaccination_requires_choice_not_free_text(self):
        from .forms import HealthRecordForm
        VaccinationSchedule.objects.create(vaccine_name='Gumboro', day_of_age=14,
                                           bird_type='BROILER')
        form = HealthRecordForm(batch=self.batch, data={
            'date': date.today().isoformat(), 'record_type': 'VACCINATION',
            'vaccine_choice': '', 'name': 'Made-up vaccine', 'dosage': '',
            'administered_by': '', 'cost': '0', 'notes': '',
        })
        self.assertFalse(form.is_valid())
        self.assertIn('vaccine_choice', form.errors)

    def test_vaccine_choices_filtered_to_batch(self):
        from .forms import HealthRecordForm
        # self.batch is BROILER; a LAYER-only vaccine must not be offered.
        VaccinationSchedule.objects.create(vaccine_name='Broiler-vax', day_of_age=1,
                                           bird_type='BROILER')
        VaccinationSchedule.objects.create(vaccine_name='Layer-vax', day_of_age=1,
                                           bird_type='LAYER')
        form = HealthRecordForm(batch=self.batch)
        offered = [c[0] for c in form.fields['vaccine_choice'].choices]
        self.assertIn('Broiler-vax', offered)
        self.assertNotIn('Layer-vax', offered)

    def test_medication_still_uses_typed_name(self):
        from .forms import HealthRecordForm
        form = HealthRecordForm(batch=self.batch, data={
            'date': date.today().isoformat(), 'record_type': 'MEDICATION',
            'vaccine_choice': '', 'name': 'Antibiotic', 'dosage': '1ml',
            'administered_by': 'Sam', 'cost': '0', 'notes': '',
        })
        self.assertTrue(form.is_valid(), form.errors)
        self.assertEqual(form.save().name, 'Antibiotic')

    def test_medication_without_name_rejected(self):
        from .forms import HealthRecordForm
        form = HealthRecordForm(batch=self.batch, data={
            'date': date.today().isoformat(), 'record_type': 'TREATMENT',
            'vaccine_choice': '', 'name': '', 'dosage': '',
            'administered_by': '', 'cost': '0', 'notes': '',
        })
        self.assertFalse(form.is_valid())
        self.assertIn('name', form.errors)

    def test_manager_can_edit_health_record(self):
        rec = HealthRecord.objects.create(
            batch=self.batch, date=date.today(), record_type='MEDICATION',
            name='Vitamin', cost='100')
        make_user('mgr', User.Role.MANAGER)
        self.client.login(username='mgr', password='pass12345!')
        resp = self.client.post(reverse('health_edit', args=[rec.pk]), {
            'date': date.today().isoformat(), 'record_type': 'MEDICATION',
            'vaccine_choice': '', 'name': 'Vitamin B', 'dosage': '2ml',
            'administered_by': 'Sam', 'cost': '150', 'notes': '',
        })
        self.assertRedirects(resp, reverse('batch_detail', args=[self.batch.pk]))
        rec.refresh_from_db()
        self.assertEqual(rec.name, 'Vitamin B')
        # Linked expense re-synced to the new cost.
        self.assertEqual(Transaction.objects.get(health_record=rec).amount, Decimal('150.00'))

    def test_deleting_health_record_removes_expense(self):
        rec = HealthRecord.objects.create(
            batch=self.batch, date=date.today(), record_type='MEDICATION',
            name='Antibiotic', cost='250')
        rid = rec.pk
        self.assertTrue(Transaction.objects.filter(health_record_id=rid).exists())
        self.client.login(username='own', password='pass12345!')
        resp = self.client.post(reverse('health_delete', args=[rid]))
        self.assertRedirects(resp, reverse('batch_detail', args=[self.batch.pk]))
        self.assertFalse(HealthRecord.objects.filter(pk=rid).exists())
        self.assertFalse(Transaction.objects.filter(health_record_id=rid).exists())

    def test_attendant_cannot_edit_or_delete_health(self):
        rec = HealthRecord.objects.create(
            batch=self.batch, date=date.today(), record_type='MEDICATION',
            name='X', cost='10')
        self.client.login(username='att', password='pass12345!')
        self.assertEqual(self.client.get(reverse('health_edit', args=[rec.pk])).status_code, 403)
        self.assertEqual(self.client.get(reverse('health_delete', args=[rec.pk])).status_code, 403)

    def test_attendant_cannot_manage_schedule(self):
        self.client.login(username='att', password='pass12345!')
        self.assertEqual(self.client.get(reverse('schedule_list')).status_code, 403)

    def test_owner_can_manage_schedule(self):
        self.client.login(username='own', password='pass12345!')
        self.assertEqual(self.client.get(reverse('schedule_list')).status_code, 200)
