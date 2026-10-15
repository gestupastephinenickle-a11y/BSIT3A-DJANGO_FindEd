from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse


class HomeViewTests(TestCase):
    def test_home_renders_for_authenticated_user(self):
        user = get_user_model().objects.create_user(username='admin', password='secret1234')

        self.client.force_login(user)
        response = self.client.get(reverse('dashboard'))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'dashboard.html')

    def test_dashboard_is_public(self):
        response = self.client.get(reverse('dashboard'))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'dashboard.html')

    def test_finder_is_public(self):
        response = self.client.get(reverse('finder'))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'home.html')

    def test_dashboard_finds_it_room(self):
        user = get_user_model().objects.create_user(username='admin', password='secret1234')
        self.client.force_login(user)
        response = self.client.get(reverse('dashboard') + '?q=IT+2-101')

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Information Technology Building')
        self.assertContains(response, '2nd Floor')
        self.assertContains(response, '101')
