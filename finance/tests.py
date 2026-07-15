from datetime import date, timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from core.models import Breed, ExpenseCategory, IncomeCategory
from inventory.models import Batch

from .models import Transaction
from .services import batch_profit_loss, period_summary

User = get_user_model()

_seq = 0


def make_user(username, role):
    return User.objects.create_user(username=username, password='pass12345!', role=role)


def make_batch(qty=100, unit_cost='2.00'):
    global _seq
    _seq += 1
    breed = Breed.objects.create(name=f'Br{_seq}', bird_type='BROILER')
    return Batch.objects.create(
        batch_code=f'F{_seq}', breed=breed, bird_type='BROILER',
        date_acquired=date.today() - timedelta(days=30),
        initial_quantity=qty, unit_cost=unit_cost,
    )


class BirdSaleTests(TestCase):
    def setUp(self):
        self.income_cat = IncomeCategory.objects.create(name='Bird sales')
        self.owner = make_user('own', User.Role.OWNER)
        self.client.login(username='own', password='pass12345!')

    def test_bird_sale_reduces_current_quantity(self):
        batch = make_batch(qty=100)
        self.assertEqual(batch.current_quantity, 100)
        Transaction.objects.create(
            type='INCOME', income_category=self.income_cat, date=date.today(),
            amount='5000', batch=batch, quantity=30, is_bird_sale=True)
        self.assertEqual(batch.total_sold, 30)
        self.assertEqual(batch.current_quantity, 70)

    def test_bird_sale_over_count_blocked_in_form(self):
        batch = make_batch(qty=50)
        resp = self.client.post(reverse('transaction_add'), {
            'type': 'INCOME', 'income_category': self.income_cat.pk,
            'date': date.today().isoformat(), 'amount': '9000',
            'batch': batch.pk, 'is_bird_sale': 'on', 'quantity': '80',
            'unit_price': '', 'party': '', 'description': '',
        })
        self.assertEqual(resp.status_code, 200)  # re-rendered with error
        self.assertEqual(batch.transactions.filter(is_bird_sale=True).count(), 0)

    def test_bird_sale_within_count_succeeds(self):
        batch = make_batch(qty=50)
        resp = self.client.post(reverse('transaction_add'), {
            'type': 'INCOME', 'income_category': self.income_cat.pk,
            'date': date.today().isoformat(), 'amount': '3000',
            'batch': batch.pk, 'is_bird_sale': 'on', 'quantity': '20',
            'unit_price': '150', 'party': 'Market', 'description': 'Live birds',
        })
        self.assertRedirects(resp, reverse('transaction_list'))
        batch.refresh_from_db()
        self.assertEqual(batch.current_quantity, 30)


class ReadOnlyTxnTests(TestCase):
    def setUp(self):
        make_user('own', User.Role.OWNER)
        self.client.login(username='own', password='pass12345!')

    def _feed_txn(self):
        # A FEED-source (auto) transaction, as the feed signal would create.
        return Transaction.objects.create(
            type='EXPENSE', source='FEED', date=date.today(), amount='500')

    def test_auto_txn_is_readonly(self):
        self.assertTrue(self._feed_txn().is_readonly)

    def test_cannot_edit_auto_txn(self):
        txn = self._feed_txn()
        self.assertEqual(self.client.get(reverse('transaction_edit', args=[txn.pk])).status_code, 403)

    def test_cannot_delete_auto_txn(self):
        txn = self._feed_txn()
        self.assertEqual(self.client.get(reverse('transaction_delete', args=[txn.pk])).status_code, 403)


class ProfitLossTests(TestCase):
    def test_period_summary_profit(self):
        inc = IncomeCategory.objects.create(name='Eggs')
        exp = ExpenseCategory.objects.create(name='Misc')
        Transaction.objects.create(type='INCOME', income_category=inc, date=date.today(), amount='1000')
        Transaction.objects.create(type='EXPENSE', expense_category=exp, date=date.today(), amount='400')
        s = period_summary()
        self.assertEqual(s['income'], Decimal('1000'))
        self.assertEqual(s['expense'], Decimal('400'))
        self.assertEqual(s['profit'], Decimal('600'))

    def test_batch_pl_includes_acquisition_and_cost_per_bird(self):
        batch = make_batch(qty=100, unit_cost='2.00')  # acquisition = 200
        exp = ExpenseCategory.objects.create(name='Vet')
        Transaction.objects.create(type='EXPENSE', expense_category=exp, date=date.today(),
                                   amount='300', batch=batch)
        inc = IncomeCategory.objects.create(name='Sales')
        Transaction.objects.create(type='INCOME', income_category=inc, date=date.today(),
                                   amount='1000', batch=batch)
        pl = batch_profit_loss(batch)
        self.assertEqual(pl['acquisition_cost'], Decimal('200.00'))
        self.assertEqual(pl['expense_with_acquisition'], Decimal('500.00'))  # 300 + 200
        self.assertEqual(pl['net'], Decimal('500.00'))  # 1000 - 500
        self.assertEqual(pl['cost_per_bird'], Decimal('5.00'))  # 500 / 100


class FinanceAccessTests(TestCase):
    def setUp(self):
        make_user('mgr', User.Role.MANAGER)
        make_user('att', User.Role.ATTENDANT)

    def test_attendant_forbidden(self):
        self.client.login(username='att', password='pass12345!')
        self.assertEqual(self.client.get(reverse('transaction_list')).status_code, 403)
        self.assertEqual(self.client.get(reverse('profit_loss')).status_code, 403)

    def test_manager_allowed(self):
        self.client.login(username='mgr', password='pass12345!')
        self.assertEqual(self.client.get(reverse('transaction_list')).status_code, 200)
        self.assertEqual(self.client.get(reverse('profit_loss')).status_code, 200)


class AddTransactionChoiceTests(TestCase):
    def setUp(self):
        make_user('mgr', User.Role.MANAGER)
        self.client.login(username='mgr', password='pass12345!')

    def test_list_offers_income_and_expense_choice(self):
        html = self.client.get(reverse('transaction_list')).content.decode()
        add = reverse('transaction_add')
        self.assertIn(f'{add}?type=INCOME', html)
        self.assertIn(f'{add}?type=EXPENSE', html)

    def test_type_preselected_from_query_income(self):
        resp = self.client.get(reverse('transaction_add') + '?type=INCOME')
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.context['form'].initial.get('type'), 'INCOME')
        self.assertIn('Add income', resp.content.decode())

    def test_type_preselected_from_query_expense(self):
        resp = self.client.get(reverse('transaction_add') + '?type=EXPENSE')
        self.assertEqual(resp.context['form'].initial.get('type'), 'EXPENSE')
        self.assertIn('Add expense', resp.content.decode())

    def test_bad_type_query_ignored(self):
        resp = self.client.get(reverse('transaction_add') + '?type=BOGUS')
        self.assertEqual(resp.status_code, 200)
        self.assertIsNone(resp.context['form'].initial.get('type'))

    def test_type_still_changeable_on_submit(self):
        # Arrived via INCOME but submitting EXPENSE must still work (preselect
        # is a shortcut, not a lock).
        exp = ExpenseCategory.objects.create(name='Feed misc')
        resp = self.client.post(reverse('transaction_add') + '?type=INCOME', {
            'type': 'EXPENSE', 'expense_category': exp.pk,
            'date': date.today().isoformat(), 'amount': '500',
            'income_category': '', 'batch': '', 'quantity': '',
            'unit_price': '', 'party': '', 'description': '',
        })
        self.assertRedirects(resp, reverse('transaction_list'))
        self.assertEqual(Transaction.objects.filter(type='EXPENSE').count(), 1)
