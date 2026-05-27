from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from apps.chat_logs.models import ConversationSession, ChatLog

User = get_user_model()


def _make_user(username, role='student'):
    return User.objects.create_user(
        username=username,
        email=f'{username}@example.com',
        password='secret123',
        display_name=username,
        role=role,
    )


def _jwt(client, user):
    from rest_framework_simplejwt.tokens import RefreshToken
    token = str(RefreshToken.for_user(user).access_token)
    client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')


class ChatLogsAPITests(APITestCase):
    """C1-C3: /api/logs/* endpoints"""

    def setUp(self):
        self.student = _make_user('stuA', 'student')
        self.other_student = _make_user('stuB', 'student')
        self.teacher = _make_user('teach1', 'teacher')

        self.s_active = ConversationSession.objects.create(
            user=self.student,
            dify_conversation_id='conv-active-1',
            status='active',
            title='活跃会话',
        )
        self.s_completed = ConversationSession.objects.create(
            user=self.student,
            dify_conversation_id='conv-done-1',
            status='completed',
            title='已完成会话',
        )
        self.s_other = ConversationSession.objects.create(
            user=self.other_student,
            dify_conversation_id='conv-other-1',
            status='active',
            title='他人的会话',
        )
        ChatLog.objects.create(
            session=self.s_active,
            dify_message_id='msg-1',
            query_text='你好',
            answer_text='你好同学',
            stage_key='stage_concept',
            message_index=1,
        )

    def test_C1_my_sessions_status_filter(self):
        _jwt(self.client, self.student)
        url = reverse('logs-sessions')

        # 不带过滤：当前学生 2 个会话
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.json()['count'], 2)

        # status=active 过滤
        resp_act = self.client.get(url, {'status': 'active'})
        self.assertEqual(resp_act.status_code, status.HTTP_200_OK)
        data = resp_act.json()
        self.assertEqual(data['count'], 1)
        self.assertEqual(data['data'][0]['dify_conversation_id'], 'conv-active-1')

        # status=completed 过滤
        resp_done = self.client.get(url, {'status': 'completed'})
        self.assertEqual(resp_done.json()['count'], 1)
        self.assertEqual(
            resp_done.json()['data'][0]['dify_conversation_id'], 'conv-done-1'
        )

    def test_C2_student_cannot_read_others_session_logs(self):
        _jwt(self.client, self.student)
        url = reverse('logs-session-detail', args=[self.s_other.id])
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_C3_teacher_can_read_any_student_session_logs(self):
        _jwt(self.client, self.teacher)
        url = reverse('logs-session-detail', args=[self.s_active.id])
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        body = resp.json()
        self.assertEqual(body['count'], 1)
        self.assertEqual(body['logs'][0]['query_text'], '你好')
        self.assertEqual(body['session']['dify_conversation_id'], 'conv-active-1')
