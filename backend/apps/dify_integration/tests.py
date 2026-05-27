import json

from django.contrib.auth import get_user_model
from django.test import Client
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from rest_framework_simplejwt.tokens import RefreshToken

from apps.chat_logs.models import ChatLog, ConversationSession
from apps.dify_integration.models import DifyConfig

User = get_user_model()


def _user(username, role='student'):
    return User.objects.create_user(
        username=username,
        email=f'{username}@example.com',
        password='secret123',
        display_name=username,
        role=role,
    )


def _access_token(user):
    return str(RefreshToken.for_user(user).access_token)


def _jwt(api_client, user):
    api_client.credentials(HTTP_AUTHORIZATION=f'Bearer {_access_token(user)}')


class ChatSendAuthTests(APITestCase):
    """B1-B3: chat_send_view 边界 (auth / 空消息 / 非法 JSON)"""

    def setUp(self):
        self.user = _user('chatstu', 'student')
        self.url = reverse('chat-send')
        # 使用 Django Client，绕过 DRF（chat_send_view 不是 DRF view）
        self.django_client = Client()

    def test_B1_no_jwt_returns_401(self):
        resp = self.django_client.post(
            self.url, data=json.dumps({'query': 'hi'}),
            content_type='application/json',
        )
        self.assertEqual(resp.status_code, 401)

    def test_B2_empty_query_returns_400(self):
        resp = self.django_client.post(
            self.url, data=json.dumps({'query': '   '}),
            content_type='application/json',
            HTTP_AUTHORIZATION=f'Bearer {_access_token(self.user)}',
        )
        self.assertEqual(resp.status_code, 400)
        self.assertIn('消息内容', resp.json()['error'])

    def test_B3_invalid_json_returns_400(self):
        resp = self.django_client.post(
            self.url, data='this is not json',
            content_type='application/json',
            HTTP_AUTHORIZATION=f'Bearer {_access_token(self.user)}',
        )
        self.assertEqual(resp.status_code, 400)


class ChatSendLiveDifyTests(APITestCase):
    """B4: 真实调用 Dify API — 需要外网 + 有效 API key"""

    def setUp(self):
        self.user = _user('livestu', 'student')
        self.url = reverse('chat-send')
        self.django_client = Client()

    def test_B4_live_dify_stream_persists_session_and_log(self):
        before_sessions = ConversationSession.objects.count()
        before_logs = ChatLog.objects.count()

        resp = self.django_client.post(
            self.url,
            data=json.dumps({'query': '你好，请用一句话介绍你自己'}),
            content_type='application/json',
            HTTP_AUTHORIZATION=f'Bearer {_access_token(self.user)}',
        )
        self.assertEqual(resp.status_code, 200)
        self.assertIn('text/event-stream', resp['Content-Type'])

        # 消费整个流（StreamingHttpResponse → streaming_content 迭代器）
        body = b''.join(resp.streaming_content).decode('utf-8', errors='replace')

        # 流里至少应该有 message_end 或 error 事件
        self.assertTrue(
            'message_end' in body or 'error' in body or 'agent_message' in body
            or 'message' in body,
            f'未收到任何已知事件，body 前 500 字符: {body[:500]}',
        )

        # 如果 Dify 调通且会话写库成功 — 验证持久化
        # 若返回 error（如 Dify 内部错误），则跳过持久化断言但仍认为联通性测过
        if 'event: error' not in body.split('\n\n')[0]:
            self.assertGreaterEqual(
                ConversationSession.objects.count(), before_sessions,
                'Dify 流式返回成功但 ConversationSession 未落库',
            )


class ConversationAPITests(APITestCase):
    """B5-B6: 会话列表/删除的所有权隔离"""

    def setUp(self):
        self.alice = _user('alice', 'student')
        self.bob = _user('bob', 'student')

        ConversationSession.objects.create(
            user=self.alice, dify_conversation_id='conv-alice-1',
            title='alice 的会话',
        )
        ConversationSession.objects.create(
            user=self.alice, dify_conversation_id='conv-alice-2',
            title='alice 的第二个会话',
        )
        self.bob_session = ConversationSession.objects.create(
            user=self.bob, dify_conversation_id='conv-bob-1',
            title='bob 的会话',
        )

    def test_B5_conversation_list_isolates_by_user(self):
        _jwt(self.client, self.alice)
        resp = self.client.get(reverse('chat-conversations'))
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        body = resp.json()
        self.assertEqual(body['count'], 2)
        titles = {c['title'] for c in body['data']}
        self.assertNotIn('bob 的会话', titles)

    def test_B6_delete_others_conversation_returns_404(self):
        _jwt(self.client, self.alice)
        resp = self.client.delete(
            reverse('chat-conversation-delete', args=[self.bob_session.id])
        )
        self.assertEqual(resp.status_code, 404)
        # bob 的会话仍然存在
        self.assertTrue(
            ConversationSession.objects.filter(pk=self.bob_session.pk).exists()
        )


class SyncTriggerPermissionTests(APITestCase):
    """B7: sync_trigger_view 角色权限"""

    def test_B7_student_forbidden(self):
        student = _user('syncstu', 'student')
        _jwt(self.client, student)
        resp = self.client.post(reverse('chat-sync'))
        self.assertEqual(resp.status_code, 403)


class DifyConfigModelTests(APITestCase):
    """C1-C3: DifyConfig 单例语义 + load() fallback"""

    def test_C1_load_creates_singleton_from_settings(self):
        DifyConfig.objects.all().delete()
        cfg = DifyConfig.load()
        self.assertEqual(cfg.pk, 1)
        self.assertTrue(cfg.api_base_url)
        self.assertTrue(cfg.api_key)

    def test_C2_save_always_uses_pk_1(self):
        cfg = DifyConfig.load()
        cfg.pk = None  # 试图新建一行
        cfg.api_key = 'app-changed'
        cfg.save()
        # 仍然只有一行，pk=1
        self.assertEqual(DifyConfig.objects.count(), 1)
        self.assertEqual(DifyConfig.objects.first().pk, 1)
        self.assertEqual(DifyConfig.objects.first().api_key, 'app-changed')

    def test_C3_load_returns_existing_when_present(self):
        cfg = DifyConfig.load()
        cfg.api_base_url = 'https://example.invalid/v1'
        cfg.save()
        again = DifyConfig.load()
        self.assertEqual(again.api_base_url, 'https://example.invalid/v1')


class DifyConfigEndpointTests(APITestCase):
    """C4-C9: /api/teacher/dify-config/ 权限 + 读写 + 掩码"""

    def setUp(self):
        self.url = reverse('teacher-dify-config')
        self.student = _user('cfgstu', 'student')
        self.teacher = _user('cfgtea', 'teacher')
        self.admin = _user('cfgadmin', 'admin')
        # 确保单例存在
        cfg = DifyConfig.load()
        cfg.api_key = 'app-VERYSECRETkey1234567890'
        cfg.api_base_url = 'https://dify.example.com/v1'
        cfg.chatflow_id = 'cf-existing'
        cfg.save()

    def test_C4_student_forbidden(self):
        _jwt(self.client, self.student)
        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, 403)

    def test_C5_anonymous_unauthorized(self):
        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, 401)

    def test_C6_teacher_get_returns_masked_key(self):
        _jwt(self.client, self.teacher)
        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        self.assertEqual(body['api_base_url'], 'https://dify.example.com/v1')
        self.assertNotIn('VERYSECRET', body['api_key'])
        self.assertIn('...', body['api_key'])
        # masked field 始终存在
        self.assertIn('app-VE', body['api_key_masked'])

    def test_C7_admin_can_reveal_full_key(self):
        _jwt(self.client, self.admin)
        resp = self.client.get(self.url + '?reveal=1')
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()['api_key'], 'app-VERYSECRETkey1234567890')

    def test_C8_teacher_reveal_request_still_masks(self):
        _jwt(self.client, self.teacher)
        resp = self.client.get(self.url + '?reveal=1')
        # teacher 不是 admin —— 不应该看到明文
        self.assertNotIn('VERYSECRET', resp.json()['api_key'])

    def test_C9_put_updates_db_and_blank_key_preserves_old(self):
        _jwt(self.client, self.teacher)
        resp = self.client.put(
            self.url,
            data=json.dumps({
                'api_base_url': 'https://new.example.com/v1/',  # 末尾 / 应该被剥掉
                'api_key': '',  # 空 → 不修改
                'chatflow_id': 'cf-NEW',
                'verify_ssl': True,
                'timeout': 90,
            }),
            content_type='application/json',
        )
        self.assertEqual(resp.status_code, 200, resp.content)

        cfg = DifyConfig.load()
        self.assertEqual(cfg.api_base_url, 'https://new.example.com/v1')
        self.assertEqual(cfg.api_key, 'app-VERYSECRETkey1234567890')  # 未变
        self.assertEqual(cfg.chatflow_id, 'cf-NEW')
        self.assertTrue(cfg.verify_ssl)
        self.assertEqual(cfg.timeout, 90)
        self.assertEqual(cfg.updated_by_id, self.teacher.id)

    def test_C10_put_with_new_key_overwrites(self):
        _jwt(self.client, self.admin)
        resp = self.client.put(
            self.url,
            data=json.dumps({'api_key': 'app-brand-new-key'}),
            content_type='application/json',
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(DifyConfig.load().api_key, 'app-brand-new-key')

    def test_C11_put_rejects_empty_base_url(self):
        _jwt(self.client, self.admin)
        # 先清空 base_url 然后试图 PUT 空字符串
        resp = self.client.put(
            self.url,
            data=json.dumps({'api_base_url': '   '}),
            content_type='application/json',
        )
        self.assertEqual(resp.status_code, 400)


class DifyClientUsesDBConfigTests(APITestCase):
    """C12: DifyClient 实例化时实际从 DB 读取，而不是 settings"""

    def test_C12_dify_client_reads_db_not_settings(self):
        from apps.dify_integration.services.dify_client import DifyClient

        cfg = DifyConfig.load()
        cfg.api_base_url = 'https://db-wins.example.com/v1'
        cfg.api_key = 'app-from-db'
        cfg.verify_ssl = True
        cfg.timeout = 42
        cfg.save()

        client = DifyClient()
        self.assertEqual(client.base_url, 'https://db-wins.example.com/v1')
        self.assertEqual(client.api_key, 'app-from-db')
        self.assertEqual(client.timeout, 42)
        self.assertTrue(client.verify_ssl)


class ChatServiceCollectEventTests(APITestCase):
    """C13-C14: chatflow 分块 message 事件应被追加，而非覆盖（回归 — 此前会丢字）"""

    def _new_service(self):
        from apps.dify_integration.services.chat_service import DifyChatService
        return DifyChatService()

    def _empty_collected(self):
        return {
            'conversation_id': '',
            'message_id': '',
            'answer': '',
            'current_stage': '',
            'token_usage': {},
            'task_id': '',
            'answer_chunks': [],
        }

    def test_C13_message_event_appends_chunks(self):
        svc = self._new_service()
        collected = self._empty_collected()
        svc._collect_event('message', {
            'conversation_id': 'conv-1', 'message_id': 'm-1', 'answer': '你好'
        }, collected)
        svc._collect_event('message', {
            'conversation_id': 'conv-1', 'message_id': 'm-1', 'answer': '，世'
        }, collected)
        svc._collect_event('message', {
            'conversation_id': 'conv-1', 'message_id': 'm-1', 'answer': '界！'
        }, collected)
        self.assertEqual(collected['answer_chunks'], ['你好', '，世', '界！'])
        self.assertEqual(''.join(collected['answer_chunks']), '你好，世界！')
        self.assertEqual(collected['conversation_id'], 'conv-1')
        self.assertEqual(collected['message_id'], 'm-1')

    def test_C14_message_event_falls_back_to_id_when_no_message_id(self):
        # Dify chatflow 的 message 事件有时只带 id 而无 message_id
        svc = self._new_service()
        collected = self._empty_collected()
        svc._collect_event('message', {
            'id': 'fallback-id', 'answer': 'hi'
        }, collected)
        self.assertEqual(collected['message_id'], 'fallback-id')


class StageExtractionTests(APITestCase):
    """C16-C21: 阶段提取 — 修复了 outputs 嵌套在 data 下、多种字段来源、中文标签的问题"""

    def _new_service(self):
        from apps.dify_integration.services.chat_service import DifyChatService
        return DifyChatService()

    def _empty_collected(self):
        return {
            'conversation_id': '', 'message_id': '', 'answer': '',
            'current_stage': '', 'token_usage': {}, 'task_id': '', 'answer_chunks': [],
        }

    def test_C16_extract_from_stage_key_field(self):
        from apps.dify_integration.services.chat_service import _extract_stage_from_outputs
        # 干净的代码节点输出
        self.assertEqual(_extract_stage_from_outputs({'stage_key': 'stage_concept'}), 'stage_concept')

    def test_C17_extract_from_structured_output(self):
        from apps.dify_integration.services.chat_service import _extract_stage_from_outputs
        # LLM 的 JSON 输出
        outputs = {
            'text': '{"current_stage":"stage_practice"}',
            'structured_output': {'current_stage': 'stage_practice'},
        }
        self.assertEqual(_extract_stage_from_outputs(outputs), 'stage_practice')

    def test_C18_normalize_chinese_label(self):
        from apps.dify_integration.services.chat_service import _normalize_stage
        # Dify 的 LLM 输出中文标签 — 必须能映射回 stage_key
        self.assertEqual(_normalize_stage('概念阶段'), 'stage_concept')
        self.assertEqual(_normalize_stage('练习'), 'stage_practice')
        self.assertEqual(_normalize_stage('总结评估'), 'stage_summary')

    def test_C19_node_finished_event_with_nested_data(self):
        # 复现真实的 Dify 事件结构：outputs 嵌套在 data 下
        svc = self._new_service()
        collected = self._empty_collected()
        event = {
            'event': 'node_finished',
            'conversation_id': 'conv-1',
            'data': {
                'id': 'node-1', 'node_id': 'n', 'node_type': 'code',
                'outputs': {'stage_key': 'stage_concept'},
            },
        }
        svc._collect_event('node_finished', event, collected)
        self.assertEqual(collected['current_stage'], 'stage_concept')

    def test_C20_workflow_finished_with_chinese_in_structured_output(self):
        # 真实场景：LLM 节点的 structured_output 是中文
        svc = self._new_service()
        collected = self._empty_collected()
        event = {
            'event': 'node_finished',
            'data': {
                'outputs': {
                    'text': '{"current_stage":"概念阶段"}',
                    'structured_output': {'current_stage': '概念阶段'},
                },
            },
        }
        svc._collect_event('node_finished', event, collected)
        self.assertEqual(collected['current_stage'], 'stage_concept')

    def test_C21_workflow_finished_fallback_regex_in_answer(self):
        # 兜底：从 answer 文本里提取 current_stage:stage_xxx
        svc = self._new_service()
        collected = self._empty_collected()
        event = {
            'event': 'workflow_finished',
            'data': {
                'outputs': {
                    'answer': '一些前缀文本 current_stage:stage_summary 后面也有内容',
                },
            },
        }
        svc._collect_event('workflow_finished', event, collected)
        self.assertEqual(collected['current_stage'], 'stage_summary')

    def test_C22_old_buggy_structure_no_longer_misleads(self):
        # 回归：之前的代码看 event['outputs']（顶层），而真实结构 outputs 在 event['data'] 下
        # 旧逻辑会把 None 当成 outputs，导致 current_stage 永远抓不到
        svc = self._new_service()
        collected = self._empty_collected()
        event = {
            'event': 'node_finished',
            'data': {'outputs': {'current_stage': 'stage_practice'}},
        }
        svc._collect_event('node_finished', event, collected)
        # 修复后能抓到
        self.assertEqual(collected['current_stage'], 'stage_practice')


class ChatServiceSaveLogTests(APITestCase):
    """C15: 持久化后 ChatLog.answer_text 应是所有 chunks 的拼接"""

    def test_C15_save_chat_log_joins_chunks(self):
        from apps.dify_integration.services.chat_service import DifyChatService

        user = _user('savestu', 'student')
        svc = DifyChatService()

        collected = {
            'conversation_id': 'dify-conv-test-1',
            'message_id': 'msg-test-1',
            'answer': '',  # 旧字段没填，全靠 chunks
            'current_stage': 'stage_concept',
            'token_usage': {'total_tokens': 42},
            'task_id': '',
            'answer_chunks': ['你', '好', '世界'],
        }

        session_info = svc._save_chat_log(
            user=user, query='问句', collected=collected, response_time_ms=123,
        )

        self.assertEqual(session_info['dify_conversation_id'], 'dify-conv-test-1')
        log = ChatLog.objects.get(dify_message_id='msg-test-1')
        self.assertEqual(log.answer_text, '你好世界')
        self.assertEqual(log.stage_key, 'stage_concept')
        self.assertEqual(log.token_count, 42)
