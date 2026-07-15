from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from .models import Breed, ExpenseCategory, FeedType, IncomeCategory, Pen

User = get_user_model()


def make(username, role, password='pass12345!'):
    return User.objects.create_user(username=username, password=password, role=role)


class ReferenceModelTests(TestCase):
    def test_str_and_ordering(self):
        Breed.objects.create(name='Isa Brown', bird_type='LAYER')
        b = Breed.objects.get(name='Isa Brown')
        self.assertEqual(str(b), 'Isa Brown (Layer)')

    def test_feedtype_default_unit(self):
        ft = FeedType.objects.create(name='Starter', category='STARTER', unit_cost='120.00')
        self.assertEqual(ft.unit, 'kg')


class ReferenceAccessTests(TestCase):
    def setUp(self):
        make('own', User.Role.OWNER)
        make('mgr', User.Role.MANAGER)
        make('att', User.Role.ATTENDANT)

    def test_owner_can_view_settings(self):
        self.client.login(username='own', password='pass12345!')
        self.assertEqual(self.client.get(reverse('settings')).status_code, 200)
        self.assertEqual(self.client.get(reverse('breed_list')).status_code, 200)

    def test_manager_forbidden(self):
        self.client.login(username='mgr', password='pass12345!')
        self.assertEqual(self.client.get(reverse('settings')).status_code, 403)
        self.assertEqual(self.client.get(reverse('breed_list')).status_code, 403)

    def test_attendant_forbidden(self):
        self.client.login(username='att', password='pass12345!')
        self.assertEqual(self.client.get(reverse('breed_add')).status_code, 403)


class ReferenceCrudTests(TestCase):
    def setUp(self):
        self.owner = make('own', User.Role.OWNER)
        self.client.login(username='own', password='pass12345!')

    def test_create_sets_created_by(self):
        resp = self.client.post(reverse('breed_add'), {
            'name': 'Ross 308', 'bird_type': 'BROILER', 'description': '',
        })
        self.assertRedirects(resp, reverse('breed_list'))
        breed = Breed.objects.get(name='Ross 308')
        self.assertEqual(breed.created_by, self.owner)
        self.assertEqual(breed.updated_by, self.owner)

    def test_update_sets_updated_by_only(self):
        breed = Breed.objects.create(name='Cobb', bird_type='BROILER')
        # created_by intentionally None (created outside a request)
        resp = self.client.post(reverse('breed_edit', args=[breed.pk]), {
            'name': 'Cobb 500', 'bird_type': 'BROILER', 'description': 'updated',
        })
        self.assertRedirects(resp, reverse('breed_list'))
        breed.refresh_from_db()
        self.assertEqual(breed.name, 'Cobb 500')
        self.assertEqual(breed.updated_by, self.owner)
        self.assertIsNone(breed.created_by)  # not overwritten on edit

    def test_delete(self):
        pen = Pen.objects.create(name='Pen A', capacity=500)
        resp = self.client.post(reverse('pen_delete', args=[pen.pk]))
        self.assertRedirects(resp, reverse('pen_list'))
        self.assertFalse(Pen.objects.filter(pk=pen.pk).exists())

    def test_duplicate_name_rejected(self):
        ExpenseCategory.objects.create(name='Feed')
        resp = self.client.post(reverse('expensecategory_add'), {'name': 'Feed'})
        self.assertEqual(resp.status_code, 200)  # re-renders form with error
        self.assertEqual(ExpenseCategory.objects.filter(name='Feed').count(), 1)

    def test_income_category_crud_roundtrip(self):
        self.client.post(reverse('incomecategory_add'), {'name': 'Egg sales'})
        self.assertTrue(IncomeCategory.objects.filter(name='Egg sales').exists())


class SeedDemoCommandTests(TestCase):
    def test_seed_creates_data_and_is_idempotent(self):
        from io import StringIO

        from django.core.management import call_command

        from finance.models import Transaction
        from inventory.models import Batch
        from production.models import EggProduction

        call_command('seed_demo', stdout=StringIO())
        self.assertEqual(
            Batch.objects.filter(batch_code__startswith='DEMO-').count(), 2)
        self.assertEqual(User.objects.filter(username__startswith='demo_').count(), 3)
        self.assertTrue(EggProduction.objects.exists())
        # Feed/health/bird-sale should have produced transactions.
        self.assertTrue(Transaction.objects.filter(source='FEED').exists())
        self.assertTrue(Transaction.objects.filter(source='HEALTH').exists())
        self.assertTrue(Transaction.objects.filter(is_bird_sale=True).exists())

        # Bird sale of 50 reduces the broiler flock below its initial 400.
        broiler = Batch.objects.get(batch_code='DEMO-BROILER-01')
        self.assertLess(broiler.current_quantity, broiler.initial_quantity)

        # Running again is a no-op (no duplicates).
        call_command('seed_demo', stdout=StringIO())
        self.assertEqual(
            Batch.objects.filter(batch_code__startswith='DEMO-').count(), 2)

    def test_fresh_recreates(self):
        from io import StringIO

        from django.core.management import call_command

        from inventory.models import Batch

        call_command('seed_demo', stdout=StringIO())
        call_command('seed_demo', '--fresh', stdout=StringIO())
        self.assertEqual(
            Batch.objects.filter(batch_code__startswith='DEMO-').count(), 2)
