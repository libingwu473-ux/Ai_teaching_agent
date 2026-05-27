import json
import time
import logging
from django.utils import timezone

from .dify_client import DifyClient, DifyAPIError
from apps.chat_logs.models import ConversationSession, ChatLog

logger = logging.getLogger('dify')


class DifyChatService:
    """Dify 对话代理服务 — 流式消息处理"""

    def __init__(self):
        self.client = DifyClient()

    def stream_chat_message(self, user, query, conversation_id='',
                            files=None, workflow_id=None):
        """
        发送消息并生成SSE事件流

        生成的事件:
        - text_chunk: 文本片段
        - stage_change: 阶段变化
        - message_end: 消息结束（含会话信息和统计）
        - error: 错误信息
        """
        dify_mapping = getattr(user, 'dify_mapping', None)
        if not dify_mapping:
            yield self._sse_event('error', {'message': '用户未绑定Dify账号'})
            return

        start_time = time.time()
        collected = {
            'conversation_id': conversation_id or '',
            'message_id': '',
            'answer': '',
            'current_stage': '',
            'token_usage': {},
            'task_id': '',
            'answer_chunks': [],
        }
        last_stage = ''

        try:
            for line in self.client.stream_chat_message(
                query=query,
                dify_user_id=dify_mapping.dify_user_id,
                conversation_id=conversation_id or '',
                files=files,
            ):
                if not line:
                    continue
                if isinstance(line, bytes):
                    line = line.decode('utf-8', errors='replace')

                if not line.startswith('data: '):
                    continue

                data_str = line[6:]
                if data_str.strip() == '[DONE]':
                    break

                try:
                    event_data = json.loads(data_str)
                except json.JSONDecodeError:
                    continue

                event_type = event_data.get('event', '')

                # 收集关键数据
                self._collect_event(event_type, event_data, collected)

                # 检测阶段变化
                current_stage = collected.get('current_stage', '')
                if current_stage and current_stage != last_stage:
                    last_stage = current_stage
                    yield self._sse_event('stage_change', {
                        'stage': current_stage,
                        'stage_name': current_stage,
                    })

                # 转发事件到前端
                yield f"event: {event_type}\ndata: {data_str}\n\n"

            # 流结束 — 持久化日志
            elapsed_ms = int((time.time() - start_time) * 1000)
            session_info = self._save_chat_log(
                user=user,
                query=query,
                collected=collected,
                response_time_ms=elapsed_ms,
                workflow_id=workflow_id,
            )

            # 发送最终消息
            yield self._sse_event('message_end', {
                'conversation_id': collected['conversation_id'],
                'message_id': collected['message_id'],
                'usage': collected['token_usage'],
                'session_info': session_info,
                'response_time_ms': elapsed_ms,
            })

        except DifyAPIError as e:
            logger.error(f'Dify API error: {e.message}')
            yield self._sse_event('error', {'message': f'Dify API错误: {e.message}'})
        except Exception as e:
            logger.exception('Stream chat error')
            yield self._sse_event('error', {'message': f'服务异常: {str(e)}'})

    def _collect_event(self, event_type, data, collected):
        """从SSE事件提取关键信息"""
        if event_type == 'message':
            collected['conversation_id'] = data.get('conversation_id', collected['conversation_id'])
            if data.get('message_id'):
                collected['message_id'] = data['message_id']
            elif data.get('id'):
                collected['message_id'] = data['id']
            # message 事件在 chatflow 中是分块发的：追加而非覆盖
            answer_chunk = data.get('answer', '')
            if answer_chunk:
                collected['answer_chunks'].append(answer_chunk)
            if data.get('usage'):
                collected['token_usage'] = data['usage']
        elif event_type == 'message_end':
            if data.get('conversation_id'):
                collected['conversation_id'] = data['conversation_id']
            if data.get('message_id'):
                collected['message_id'] = data['message_id']
            metadata = data.get('metadata', {})
            if isinstance(metadata, dict) and 'usage' in metadata:
                collected['token_usage'] = metadata['usage']
        elif event_type == 'agent_thought':
            if data.get('conversation_id'):
                collected['conversation_id'] = data['conversation_id']
            if data.get('message_id'):
                collected['message_id'] = data['message_id']
            if data.get('task_id'):
                collected['task_id'] = data['task_id']
            collected['token_usage'] = data.get('usage', collected.get('token_usage', {}))
        elif event_type == 'agent_message':
            if data.get('conversation_id'):
                collected['conversation_id'] = data['conversation_id']
            if data.get('message_id'):
                collected['message_id'] = data['message_id']
            answer_chunk = data.get('answer', '')
            if answer_chunk:
                collected['answer_chunks'].append(answer_chunk)
        elif event_type == 'workflow_started':
            collected['task_id'] = data.get('task_id', '')
        elif event_type == 'node_finished':
            stage = _extract_stage_from_outputs(data.get('data', {}).get('outputs'))
            if stage:
                collected['current_stage'] = stage
        elif event_type == 'workflow_finished':
            outputs = data.get('data', {}).get('outputs') or {}
            stage = _extract_stage_from_outputs(outputs)
            if stage:
                collected['current_stage'] = stage
            # 兜底：从 answer 文本中提取 "current_stage:stage_xxx"
            if not collected.get('current_stage') and isinstance(outputs, dict):
                ans = outputs.get('answer', '')
                if isinstance(ans, str):
                    import re
                    m = re.search(r'current_stage[:：]\s*(stage_\w+)', ans)
                    if m:
                        collected['current_stage'] = m.group(1)
        elif event_type == 'text_chunk':
            chunk = data.get('data', data.get('text', ''))
            if chunk:
                collected['answer_chunks'].append(chunk)

    def _save_chat_log(self, user, query, collected, response_time_ms, workflow_id=None):
        """保存对话日志并更新会话状态"""
        dify_conv_id = collected.get('conversation_id', '')
        if not dify_conv_id:
            return {}

        # 查找或创建会话
        session, created = ConversationSession.objects.get_or_create(
            dify_conversation_id=dify_conv_id,
            defaults={
                'user': user,
                'workflow_id': workflow_id,
                'status': 'active',
            }
        )

        # 统一维护 current_stage + completed_stages（新建/旧 session 同样处理）
        stage = collected.get('current_stage', '')
        if stage:
            session.current_stage = stage
            completed = json.loads(session.completed_stages or '[]')
            if stage not in completed:
                completed.append(stage)
                session.completed_stages = json.dumps(completed, ensure_ascii=False)

        # Always update counters
        session.total_messages = ChatLog.objects.filter(session=session).count() + 1
        token_data = collected.get('token_usage', {})
        if isinstance(token_data, dict):
            session.total_tokens += token_data.get('total_tokens', 0)
        session.save()

        # 计算消息索引
        msg_index = ChatLog.objects.filter(session=session).count() + 1

        # 获取答案文本
        answer_text = collected.get('answer', '')
        if not answer_text and collected.get('answer_chunks'):
            answer_text = ''.join(collected['answer_chunks'])

        # 提取token数
        token_data = collected.get('token_usage', {})
        token_count = 0
        if isinstance(token_data, dict):
            token_count = token_data.get('total_tokens', 0)

        # 使用message_id，没有则生成
        msg_id = collected.get('message_id', '')
        if not msg_id:
            import uuid
            msg_id = str(uuid.uuid4())

        # 创建日志（避免重复）
        if not ChatLog.objects.filter(dify_message_id=msg_id).exists():
            ChatLog.objects.create(
                session=session,
                dify_message_id=msg_id,
                query_text=query,
                answer_text=answer_text,
                stage_key=collected.get('current_stage', ''),
                message_index=msg_index,
                token_count=token_count,
                response_time_ms=response_time_ms,
            )

        # 自动评分 — 失败不能影响聊天流
        try:
            from apps.scoring.scoring_engine import score_session
            score_session(session)
        except Exception:
            logger.exception('auto-scoring after chat failed for session %s', session.id)

        return {
            'id': session.id,
            'dify_conversation_id': session.dify_conversation_id,
            'current_stage': session.current_stage,
            'completed_stages': json.loads(session.completed_stages or '[]'),
            'total_messages': session.total_messages,
        }

    def _sse_event(self, event_type, data):
        """生成SSE事件字符串"""
        return f"event: {event_type}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


# 中文阶段名 → stage_key（Dify 的 LLM 经常输出中文，我们落库时按 WorkflowStage.stage_key 标准化）
_STAGE_NAME_ALIASES = {
    '概念': 'stage_concept', '概念阶段': 'stage_concept', '概念讲解': 'stage_concept',
    '练习': 'stage_practice', '练习阶段': 'stage_practice', '练习测验': 'stage_practice',
    '总结': 'stage_summary', '总结阶段': 'stage_summary', '总结评估': 'stage_summary',
}


def _normalize_stage(value):
    """把 Dify 输出的阶段值标准化为 stage_key。识别：stage_xxx 直通；中文别名映射；动态匹配 WorkflowStage.name。"""
    if not value or not isinstance(value, str):
        return ''
    v = value.strip()
    if not v:
        return ''
    if v.startswith('stage_'):
        return v
    if v in _STAGE_NAME_ALIASES:
        return _STAGE_NAME_ALIASES[v]
    # 动态查 DB：按 name 找 stage_key
    try:
        from apps.dify_integration.models import WorkflowStage
        stage = WorkflowStage.objects.filter(name=v).first()
        if stage:
            return stage.stage_key
    except Exception:
        pass
    return ''


def _extract_stage_from_outputs(outputs):
    """从一个 node 的 outputs dict 里嗅探 current_stage / stage_key。返回标准化的 stage_key 或 ''。"""
    if not isinstance(outputs, dict):
        return ''
    # 优先级 1：stage_key 字段（最干净）
    if outputs.get('stage_key'):
        return _normalize_stage(outputs['stage_key'])
    # 优先级 2：current_stage 字段
    if outputs.get('current_stage'):
        return _normalize_stage(outputs['current_stage'])
    # 优先级 3：structured_output.current_stage（LLM JSON 输出）
    so = outputs.get('structured_output')
    if isinstance(so, dict) and so.get('current_stage'):
        return _normalize_stage(so['current_stage'])
    return ''
