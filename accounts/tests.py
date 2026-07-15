from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

User = get_user_model()


class RoleFactoryMixin:
    """Helpers to make users of each role."""

    def make(self, username, role, password='pass12345!', **extra):
        return User.objects.create_user(
            username=username, password=password, role=role, **extra
        )


class AuthFlowTests(RoleFactoryMixin, TestCase):
    def test_login_redirects_to_dashboard(self):
        self.make('owner1', User.Role.OWNER)
        resp = self.client.post(
            reverse('login'),
            {'username': 'owner1', 'password': 'pass12345!'},
        )
        self.assertRedirects(resp, reverse('dashboard'))

    def test_successful_login_shows_success_message(self):
        self.make('owner1', User.Role.OWNER, first_name='Ada')
        resp = self.client.post(
            reverse('login'),
            {'username': 'owner1', 'password': 'pass12345!'},
            follow=True,
        )
        msgs = list(resp.context['messages'])
        self.assertEqual(len(msgs), 1)
        self.assertEqual(msgs[0].level_tag, 'success')
        self.assertIn('Welcome back, Ada', str(msgs[0]))

    def test_incorrect_login_shows_error_message(self):
        self.make('owner1', User.Role.OWNER)
        resp = self.client.post(
            reverse('login'),
            {'username': 'owner1', 'password': 'wrong-password'},
        )
        self.assertEqual(resp.status_code, 200)  # re-rendered, not redirected
        msgs = list(resp.context['messages'])
        self.assertEqual(len(msgs), 1)
        self.assertEqual(msgs[0].level_tag, 'error')
        self.assertIn('Incorrect username or password', str(msgs[0]))

    def test_logout_requires_post(self):
        self.make('m1', User.Role.MANAGER)
        self.client.login(username='m1', password='pass12345!')
        # GET should not log the user out (Django 5 logout is POST-only).
        self.client.get(reverse('logout'))
        resp = self.client.get(reverse('profile'))
        self.assertEqual(resp.status_code, 200)  # still authenticated


class RoleAccessTests(RoleFactoryMixin, TestCase):
    def test_anonymous_redirected_to_login(self):
        resp = self.client.get(reverse('user_list'))
        self.assertEqual(resp.status_code, 302)
        self.assertIn(reverse('login'), resp.url)

    def test_attendant_cannot_reach_user_management(self):
        self.make('att', User.Role.ATTENDANT)
        self.client.login(username='att', password='pass12345!')
        resp = self.client.get(reverse('user_list'))
        self.assertEqual(resp.status_code, 403)

    def test_manager_cannot_reach_user_management(self):
        self.make('mgr', User.Role.MANAGER)
        self.client.login(username='mgr', password='pass12345!')
        resp = self.client.get(reverse('user_list'))
        self.assertEqual(resp.status_code, 403)

    def test_owner_can_reach_user_management(self):
        self.make('own', User.Role.OWNER)
        self.client.login(username='own', password='pass12345!')
        resp = self.client.get(reverse('user_list'))
        self.assertEqual(resp.status_code, 200)

    def test_superuser_bypasses_role_check(self):
        su = User.objects.create_superuser('root', password='pass12345!')
        # default role is ATTENDANT, but superuser should still pass
        self.assertEqual(su.role, User.Role.ATTENDANT)
        self.client.login(username='root', password='pass12345!')
        resp = self.client.get(reverse('user_list'))
        self.assertEqual(resp.status_code, 200)


class UserManagementTests(RoleFactoryMixin, TestCase):
    def setUp(self):
        self.owner = self.make('boss', User.Role.OWNER)
        self.client.login(username='boss', password='pass12345!')

    def test_owner_creates_user_with_role(self):
        resp = self.client.post(reverse('user_add'), {
            'username': 'newatt',
            'first_name': 'New', 'last_name': 'Attendant',
            'email': 'n@example.com', 'phone': '',
            'role': User.Role.ATTENDANT,
            'password1': 'strongpass987', 'password2': 'strongpass987',
        })
        self.assertRedirects(resp, reverse('user_list'))
        u = User.objects.get(username='newatt')
        self.assertEqual(u.role, User.Role.ATTENDANT)

    def test_toggle_deactivates_other_user(self):
        target = self.make('victim', User.Role.MANAGER)
        resp = self.client.post(reverse('user_toggle', args=[target.pk]))
        self.assertRedirects(resp, reverse('user_list'))
        target.refresh_from_db()
        self.assertFalse(target.is_active)

    def test_owner_cannot_deactivate_self(self):
        resp = self.client.post(reverse('user_toggle', args=[self.owner.pk]))
        self.owner.refresh_from_db()
        self.assertTrue(self.owner.is_active)  # unchanged


class ProfileTests(RoleFactoryMixin, TestCase):
    def test_password_change_keeps_user_logged_in(self):
        self.make('changer', User.Role.ATTENDANT)
        self.client.login(username='changer', password='pass12345!')
        resp = self.client.post(reverse('password_change_own'), {
            'old_password': 'pass12345!',
            'new_password1': 'brandnewpass456',
            'new_password2': 'brandnewpass456',
        })
        self.assertRedirects(resp, reverse('profile'))
        # Session still valid → profile reachable
        self.assertEqual(self.client.get(reverse('profile')).status_code, 200)
