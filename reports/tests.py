from datetime import date, timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from core.models import Breed
from inventory.models import Batch, MortalityRecord

from .services import batch_performance_report, mortality_report

User = get_user_model()

_seq = 0


def make_user(username, role):
    return User.objects.create_user(username=username, password='pass12345!', role=role)


def make_batch():
    global _seq
    _seq += 1
    breed = Breed.objects.create(name=f'Br{_seq}', bird_type='BROILER')
    return Batch.objects.create(
        batch_code=f'R{_seq}', breed=breed, bird_type='BROILER',
        date_acquired=date.today() - timedelta(days=20),
        initial_quantity=100, unit_cost='2.00',
    )


class ReportBuilderTests(TestCase):
    def test_batch_performance_has_row_per_batch(self):
        make_batch()
        make_batch()
        report = batch_performance_report()
        self.assertEqual(len(report['rows']), 2)
        self.assertIn('Code', report['headers'])

    def test_mortality_report_totals(self):
        b = make_batch()
        MortalityRecord.objects.create(batch=b, date=date.today(), quantity=5)
        MortalityRecord.objects.create(batch=b, date=date.today(), quantity=3)
        report = mortality_report()
        self.assertEqual(report['meta']['total'], 8)

    def test_mortality_date_filter(self):
        b = make_batch()
        MortalityRecord.objects.create(batch=b, date=date.today(), quantity=5)
        MortalityRecord.objects.create(batch=b, date=date.today() - timedelta(days=40),
                                       quantity=99)
        report = mortality_report(start=(date.today() - timedelta(days=7)).isoformat())
        self.assertEqual(report['meta']['total'], 5)  # old record excluded


class ReportAccessTests(TestCase):
    def setUp(self):
        make_user('mgr', User.Role.MANAGER)
        make_user('att', User.Role.ATTENDANT)

    def test_attendant_forbidden(self):
        self.client.login(username='att', password='pass12345!')
        self.assertEqual(self.client.get(reverse('report_index')).status_code, 403)

    def test_manager_can_view_index_and_report(self):
        self.client.login(username='mgr', password='pass12345!')
        self.assertEqual(self.client.get(reverse('report_index')).status_code, 200)
        self.assertEqual(
            self.client.get(reverse('report_detail', args=['mortality'])).status_code, 200)

    def test_unknown_report_404(self):
        self.client.login(username='mgr', password='pass12345!')
        self.assertEqual(
            self.client.get(reverse('report_detail', args=['nope'])).status_code, 404)


class ExportTests(TestCase):
    def setUp(self):
        make_user('mgr', User.Role.MANAGER)
        self.client.login(username='mgr', password='pass12345!')
        make_batch()

    def test_excel_export_content_type(self):
        resp = self.client.get(reverse('report_detail', args=['batch-performance']),
                               {'format': 'excel'})
        self.assertEqual(resp.status_code, 200)
        self.assertIn('spreadsheetml', resp['Content-Type'])
        self.assertIn('attachment', resp['Content-Disposition'])

    def test_pdf_export_content_type(self):
        resp = self.client.get(reverse('report_detail', args=['batch-performance']),
                               {'format': 'pdf'})
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp['Content-Type'], 'application/pdf')
        self.assertTrue(resp.content[:4] == b'%PDF')
