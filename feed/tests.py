from datetime import date, timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.urls import reverse

from core.models import Breed, FeedType
from finance.models import Transaction
from inventory.models import Batch

from .models import FeedConsumption, FeedPurchase, feed_stock_level

User = get_user_model()


def make_user(username, role):
    return User.objects.create_user(username=username, password='pass12345!', role=role)


def make_feed_type(name='Starter'):
    return FeedType.objects.create(name=name, category='STARTER', unit='kg', unit_cost='100.00')


def make_batch():
    breed = Breed.objects.create(name='Ross', bird_type='BROILER')
    return Batch.objects.create(
        batch_code='B1', breed=breed, bird_type='BROILER',
        date_acquired=date.today() - timedelta(days=10),
        initial_quantity=500, unit_cost='2.00',
    )


class StockLevelTests(TestCase):
    def test_stock_is_purchases_minus_consumption(self):
        ft = make_feed_type()
        batch = make_batch()
        FeedPurchase.objects.create(feed_type=ft, date=date.today(), quantity='200', unit_cost='100')
        FeedConsumption.objects.create(batch=batch, feed_type=ft, date=date.today(), quantity_kg='60')
        self.assertEqual(feed_stock_level(ft), Decimal('140'))

    def test_stock_zero_when_no_activity(self):
        ft = make_feed_type()
        self.assertEqual(feed_stock_level(ft), Decimal('0'))


class AutoExpenseTests(TestCase):
    def test_purchase_creates_expense_transaction(self):
        ft = make_feed_type()
        p = FeedPurchase.objects.create(feed_type=ft, date=date.today(), quantity='100', unit_cost='120')
        txn = Transaction.objects.get(feed_purchase=p)
        self.assertEqual(txn.type, Transaction.Type.EXPENSE)
        self.assertEqual(txn.source, Transaction.Source.FEED)
        self.assertEqual(txn.amount, Decimal('12000.00'))
        self.assertTrue(txn.is_readonly)

    def test_editing_purchase_updates_transaction(self):
        ft = make_feed_type()
        p = FeedPurchase.objects.create(feed_type=ft, date=date.today(), quantity='100', unit_cost='120')
        p.quantity = Decimal('50')
        p.save()
        txn = Transaction.objects.get(feed_purchase=p)
        self.assertEqual(txn.amount, Decimal('6000.00'))
        self.assertEqual(Transaction.objects.filter(feed_purchase=p).count(), 1)

    def test_deleting_purchase_removes_transaction(self):
        ft = make_feed_type()
        p = FeedPurchase.objects.create(feed_type=ft, date=date.today(), quantity='100', unit_cost='120')
        pid = p.pk
        p.delete()
        self.assertFalse(Transaction.objects.filter(feed_purchase_id=pid).exists())


class ConsumptionValidationTests(TestCase):
    def test_consumption_exceeding_stock_rejected(self):
        ft = make_feed_type()
        batch = make_batch()
        FeedPurchase.objects.create(feed_type=ft, date=date.today(), quantity='50', unit_cost='100')
        rec = FeedConsumption(batch=batch, feed_type=ft, date=date.today(), quantity_kg=Decimal('80'))
        with self.assertRaises(ValidationError) as cm:
            rec.full_clean()
        self.assertIn('quantity_kg', cm.exception.error_dict)

    def test_future_date_rejected(self):
        ft = make_feed_type()
        batch = make_batch()
        FeedPurchase.objects.create(feed_type=ft, date=date.today(), quantity='50', unit_cost='100')
        rec = FeedConsumption(batch=batch, feed_type=ft,
                              date=date.today() + timedelta(days=1), quantity_kg=Decimal('10'))
        with self.assertRaises(ValidationError):
            rec.full_clean()

    def test_purchase_future_date_rejected(self):
        ft = make_feed_type()
        p = FeedPurchase(feed_type=ft, date=date.today() + timedelta(days=1),
                         quantity=Decimal('10'), unit_cost=Decimal('100'))
        with self.assertRaises(ValidationError):
            p.full_clean()


class FeedAccessTests(TestCase):
    def setUp(self):
        make_user('own', User.Role.OWNER)
        make_user('mgr', User.Role.MANAGER)
        make_user('att', User.Role.ATTENDANT)
        self.batch = make_batch()
        self.ft = make_feed_type()
        FeedPurchase.objects.create(feed_type=self.ft, date=date.today(), quantity='500', unit_cost='100')

    def test_all_roles_view_stock(self):
        for u in ('own', 'mgr', 'att'):
            self.client.login(username=u, password='pass12345!')
            self.assertEqual(self.client.get(reverse('feed_stock')).status_code, 200)

    def test_attendant_cannot_add_purchase(self):
        self.client.login(username='att', password='pass12345!')
        self.assertEqual(self.client.get(reverse('feed_purchase_add')).status_code, 403)

    def test_manager_can_add_purchase(self):
        self.client.login(username='mgr', password='pass12345!')
        self.assertEqual(self.client.get(reverse('feed_purchase_add')).status_code, 200)

    def test_attendant_can_record_consumption(self):
        self.client.login(username='att', password='pass12345!')
        url = reverse('feed_consumption_add', args=[self.batch.pk])
        self.assertEqual(self.client.get(url).status_code, 200)
        resp = self.client.post(url, {
            'feed_type': self.ft.pk, 'date': date.today().isoformat(), 'quantity_kg': '25',
        })
        self.assertRedirects(resp, reverse('batch_detail', args=[self.batch.pk]))
        self.assertEqual(FeedConsumption.objects.count(), 1)

    def test_purchase_via_view_posts_expense(self):
        self.client.login(username='mgr', password='pass12345!')
        self.client.post(reverse('feed_purchase_add'), {
            'feed_type': self.ft.pk, 'date': date.today().isoformat(),
            'quantity': '30', 'unit_cost': '110', 'supplier': 'Acme',
        })
        # setUp made 1 purchase (→1 txn); this adds a second
        self.assertEqual(Transaction.objects.filter(source='FEED').count(), 2)

    # --- purchase edit / delete --------------------------------------------
    def test_manager_can_edit_purchase_resyncs_expense(self):
        p = FeedPurchase.objects.create(feed_type=self.ft, date=date.today(),
                                        quantity='100', unit_cost='120')
        self.client.login(username='mgr', password='pass12345!')
        resp = self.client.post(reverse('feed_purchase_edit', args=[p.pk]), {
            'feed_type': self.ft.pk, 'date': date.today().isoformat(),
            'quantity': '100', 'unit_cost': '150', 'supplier': '',
        })
        self.assertRedirects(resp, reverse('feed_purchase_list'))
        self.assertEqual(Transaction.objects.get(feed_purchase=p).amount, Decimal('15000.00'))

    def test_deleting_purchase_via_view_removes_expense(self):
        p = FeedPurchase.objects.create(feed_type=self.ft, date=date.today(),
                                        quantity='100', unit_cost='120')
        pid = p.pk
        self.client.login(username='own', password='pass12345!')
        resp = self.client.post(reverse('feed_purchase_delete', args=[pid]))
        self.assertRedirects(resp, reverse('feed_purchase_list'))
        self.assertFalse(FeedPurchase.objects.filter(pk=pid).exists())
        self.assertFalse(Transaction.objects.filter(feed_purchase_id=pid).exists())

    def test_attendant_cannot_edit_or_delete_purchase(self):
        p = FeedPurchase.objects.create(feed_type=self.ft, date=date.today(),
                                        quantity='10', unit_cost='120')
        self.client.login(username='att', password='pass12345!')
        self.assertEqual(
            self.client.get(reverse('feed_purchase_edit', args=[p.pk])).status_code, 403)
        self.assertEqual(
            self.client.get(reverse('feed_purchase_delete', args=[p.pk])).status_code, 403)

    # --- consumption edit / delete -----------------------------------------
    def test_manager_can_edit_and_delete_consumption(self):
        c = FeedConsumption.objects.create(batch=self.batch, feed_type=self.ft,
                                           date=date.today(), quantity_kg='25')
        self.client.login(username='mgr', password='pass12345!')
        resp = self.client.post(reverse('feed_consumption_edit', args=[c.pk]), {
            'feed_type': self.ft.pk, 'date': date.today().isoformat(), 'quantity_kg': '40',
        })
        self.assertRedirects(resp, reverse('batch_detail', args=[self.batch.pk]))
        c.refresh_from_db()
        self.assertEqual(c.quantity_kg, Decimal('40'))
        resp = self.client.post(reverse('feed_consumption_delete', args=[c.pk]))
        self.assertRedirects(resp, reverse('batch_detail', args=[self.batch.pk]))
        self.assertFalse(FeedConsumption.objects.filter(pk=c.pk).exists())

    def test_attendant_cannot_delete_consumption(self):
        c = FeedConsumption.objects.create(batch=self.batch, feed_type=self.ft,
                                           date=date.today(), quantity_kg='25')
        self.client.login(username='att', password='pass12345!')
        self.assertEqual(
            self.client.get(reverse('feed_consumption_delete', args=[c.pk])).status_code, 403)
