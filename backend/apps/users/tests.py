from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from apps.dify_integration.models import DifyUserMapping

User = get_user_model()


class AuthAPITests(APITestCase):
    """A1-A7: /api/auth/* endpoints"""

    def _register_payload(self, **overrides):
        data = {
            'username': 'stu001',
            'email': 'stu001@example.com',
            'password': 'secret123',
            'display_name': '学生甲',
            'role': 'student',
        }
        data.update(overrides)
        return data

    def test_A1_register_success(self):
        url = reverse('auth-register')
        resp = self.client.post(url, self._register_payload(), format='json')
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        self.assertEqual(resp.data['username'], 'stu001')
        self.assertEqual(resp.data['role'], 'student')
        self.assertIn('access_token', resp.data)
        self.assertIn('refresh_token', resp.data)
        self.assertTrue(resp.data['dify_user_id'].startswith('dify_edu_'))

    def test_A2_register_short_password(self):
        # RegisterSerializer 没有密码确认字段，min_length=6 校验代之
        url = reverse('auth-register')
        resp = self.client.post(
            url, self._register_payload(password='123'), format='json'
        )
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('password', resp.data)

    def test_A3_register_duplicate_username(self):
        url = reverse('auth-register')
        first = self.client.post(url, self._register_payload(), format='json')
        self.assertEqual(first.status_code, status.HTTP_201_CREATED)

        dup = self.client.post(
            url,
            self._register_payload(email='other@example.com'),
            format='json',
        )
        self.assertEqual(dup.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('username', dup.data)

    def test_A4_register_triggers_dify_mapping_signal(self):
        url = reverse('auth-register')
        resp = self.client.post(url, self._register_payload(), format='json')
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)

        user = User.objects.get(username='stu001')
        mapping = DifyUserMapping.objects.get(user=user)
        self.assertTrue(mapping.dify_user_id.startswith('dify_edu_'))
        # signal-generated ID 是 dify_edu_ + 12位hex
        self.assertEqual(len(mapping.dify_user_id), len('dify_edu_') + 12)
        self.assertEqual(resp.data['dify_user_id'], mapping.dify_user_id)

    def test_A5_login_success_returns_jwt(self):
        # 先注册
        self.client.post(
            reverse('auth-register'), self._register_payload(), format='json'
        )

        resp = self.client.post(
            reverse('auth-login'),
            {'username': 'stu001', 'password': 'secret123'},
            format='json',
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertIn('access_token', resp.data)
        self.assertIn('refresh_token', resp.data)
        self.assertEqual(resp.data['username'], 'stu001')

    def test_A6_login_wrong_password(self):
        self.client.post(
            reverse('auth-register'), self._register_payload(), format='json'
        )
        resp = self.client.post(
            reverse('auth-login'),
            {'username': 'stu001', 'password': 'WRONG_PASS'},
            format='json',
        )
        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_A7_profile_requires_jwt(self):
        url = reverse('auth-profile')

        # 未携带 token → 401
        unauth = self.client.get(url)
        self.assertEqual(unauth.status_code, status.HTTP_401_UNAUTHORIZED)

        # 注册并携带 token → 200
        reg = self.client.post(
            reverse('auth-register'), self._register_payload(), format='json'
        )
        access = reg.data['access_token']
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {access}')
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data['username'], 'stu001')
        self.assertIn('dify_user_id', resp.data)
