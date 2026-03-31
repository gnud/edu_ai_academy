from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase, APIClient
from rest_framework import status

from .models import Thread

User = get_user_model()


class PMThreadFindOrCreateTests(APITestCase):
    def setUp(self):
        self.alice = User.objects.create_user('alice', password='pw')
        self.bob   = User.objects.create_user('bob',   password='pw')
        self.carol = User.objects.create_user('carol',  password='pw')
        self.client = APIClient()

    def _post_thread(self, actor, participant_ids):
        self.client.force_authenticate(actor)
        return self.client.post('/api/messages/threads/', {
            'thread_type': 'pm',
            'subject': '',
            'participant_ids': participant_ids,
        }, format='json')

    def test_first_pm_creates_thread(self):
        res = self._post_thread(self.alice, [self.bob.id])
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(Thread.objects.filter(thread_type='pm').count(), 1)

    def test_second_pm_reuses_same_thread(self):
        res1 = self._post_thread(self.alice, [self.bob.id])
        res2 = self._post_thread(self.bob,   [self.alice.id])
        self.assertEqual(res1.data['id'], res2.data['id'])
        self.assertEqual(Thread.objects.filter(thread_type='pm').count(), 1)

    def test_different_pair_gets_different_thread(self):
        res_ab = self._post_thread(self.alice, [self.bob.id])
        res_ac = self._post_thread(self.alice, [self.carol.id])
        self.assertNotEqual(res_ab.data['id'], res_ac.data['id'])
        self.assertEqual(Thread.objects.filter(thread_type='pm').count(), 2)
