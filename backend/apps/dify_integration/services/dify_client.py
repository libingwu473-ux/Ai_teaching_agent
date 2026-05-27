import json
import httpx
import logging
from django.conf import settings

logger = logging.getLogger('dify')


class DifyClient:
    """Dify API 客户端封装"""

    def __init__(self):
        from apps.dify_integration.models import DifyConfig
        cfg = DifyConfig.load()
        self.base_url = (cfg.api_base_url or settings.DIFY_CONFIG['API_BASE_URL']).rstrip('/')
        self.api_key = cfg.api_key or settings.DIFY_CONFIG['API_KEY']
        self.timeout = cfg.timeout or settings.DIFY_CONFIG.get('TIMEOUT', 60)
        self.max_retries = cfg.max_retries or settings.DIFY_CONFIG.get('MAX_RETRIES', 3)
        self.verify_ssl = cfg.verify_ssl

    def _make_client(self, timeout=None):
        """创建httpx客户端（关闭SSL验证避免Windows间歇性SSL错误；跟随301/302避免http→https被截断）"""
        return httpx.Client(
            timeout=timeout or self.timeout,
            verify=self.verify_ssl,
            follow_redirects=True,
        )

    @property
    def _headers(self):
        return {
            'Authorization': f'Bearer {self.api_key}',
            'Content-Type': 'application/json',
        }

    def stream_chat_message(self, query, dify_user_id, conversation_id='',
                            inputs=None, files=None):
        """发送对话消息，返回SSE行迭代器"""
        payload = {
            'query': query,
            'inputs': inputs or {},
            'response_mode': 'streaming',
            'conversation_id': conversation_id or '',
            'user': dify_user_id,
            'auto_generate_name': True,
        }
        if files:
            payload['files'] = files

        logger.info(f'Dify API request: user={dify_user_id}, conv={conversation_id or "new"}')

        with self._make_client() as client:
            with client.stream(
                'POST',
                f'{self.base_url}/chat-messages',
                headers=self._headers,
                json=payload,
            ) as response:
                if response.status_code != 200:
                    try:
                        error_body = response.read().decode('utf-8', errors='replace')
                        error_data = json.loads(error_body)
                        error_msg = error_data.get('message', error_body)
                    except Exception:
                        error_msg = f'HTTP {response.status_code}'
                    raise DifyAPIError(error_msg, status_code=response.status_code)

                for line in response.iter_lines():
                    yield line

    def get_conversations(self, dify_user_id, limit=50, last_id=None):
        """获取用户会话列表"""
        params = {
            'user': dify_user_id,
            'limit': limit,
            'sort_by': '-updated_at',
        }
        if last_id:
            params['last_id'] = last_id

        with self._make_client(timeout=30) as client:
            resp = client.get(
                f'{self.base_url}/conversations',
                headers=self._headers,
                params=params,
            )
        data = resp.json()
        return data.get('data', []), data.get('has_more', False)

    def get_messages(self, dify_user_id, conversation_id, limit=100, first_id=None):
        """获取会话消息历史"""
        params = {
            'user': dify_user_id,
            'conversation_id': conversation_id,
            'limit': min(limit, 100),
        }
        if first_id:
            params['first_id'] = first_id

        with self._make_client(timeout=30) as client:
            resp = client.get(
                f'{self.base_url}/messages',
                headers=self._headers,
                params=params,
            )
        data = resp.json()
        return data.get('data', []), data.get('has_more', False)

    def delete_conversation(self, dify_user_id, conversation_id):
        """删除会话"""
        with self._make_client(timeout=30) as client:
            resp = client.request(
                'DELETE',
                f'{self.base_url}/conversations/{conversation_id}',
                headers=self._headers,
                json={'user': dify_user_id},
            )
        return resp.status_code == 200

    def upload_file(self, dify_user_id, file_obj):
        """上传文件到Dify"""
        with self._make_client(timeout=60) as client:
            resp = client.post(
                f'{self.base_url}/files/upload',
                headers={'Authorization': f'Bearer {self.api_key}'},
                files={'file': (file_obj.name, file_obj, file_obj.content_type)},
                data={'user': dify_user_id},
            )
        return resp.json()

    def stop_response(self, task_id, dify_user_id):
        """停止流式响应"""
        with self._make_client(timeout=10) as client:
            resp = client.post(
                f'{self.base_url}/chat-messages/{task_id}/stop',
                headers=self._headers,
                json={'user': dify_user_id},
            )
        return resp.status_code == 200


class DifyAPIError(Exception):
    def __init__(self, message, status_code=None):
        self.message = message
        self.status_code = status_code
        super().__init__(message)
