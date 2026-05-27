import json
import logging
from datetime import datetime
from django.utils import timezone

from .services.dify_client import DifyClient
from .models import DifyUserMapping
from apps.chat_logs.models import ConversationSession, ChatLog

logger = logging.getLogger('dify.sync')


class DifySyncService:
    """从Dify API同步对话数据到本地数据库"""

    def __init__(self):
        self.client = DifyClient()

    def sync_all_active_users(self):
        """同步所有活跃用户的对话数据"""
        mappings = DifyUserMapping.objects.filter(is_active=True)
        stats = {'total': 0, 'new_sessions': 0, 'new_messages': 0, 'errors': 0}

        for mapping in mappings:
            try:
                result = self.sync_user_conversations(mapping)
                stats['total'] += 1
                stats['new_sessions'] += result.get('new_sessions', 0)
                stats['new_messages'] += result.get('new_messages', 0)
            except Exception as e:
                logger.error(f'同步用户 {mapping.dify_user_id} 失败: {e}')
                stats['errors'] += 1

        logger.info(f'同步完成: {stats}')
        return stats

    def sync_user_conversations(self, mapping):
        """同步单个用户的所有会话和消息"""
        result = {'new_sessions': 0, 'new_messages': 0}

        # 获取Dify上的会话列表
        dify_convs, has_more = self.client.get_conversations(mapping.dify_user_id)
        # 简化处理：只拉取第一页（最近50条）
        # 生产环境需实现完整分页

        for dify_conv in dify_convs:
            session, created = ConversationSession.objects.get_or_create(
                dify_conversation_id=dify_conv['id'],
                defaults={
                    'user': mapping.user,
                    'title': dify_conv.get('name', ''),
                    'status': 'active',
                }
            )
            if created:
                result['new_sessions'] += 1

            # 同步消息
            msg_count = self._sync_session_messages(
                session, mapping.dify_user_id, dify_conv['id']
            )
            result['new_messages'] += msg_count

            # 更新会话状态
            self._update_session_state(session)

            # 触发自动评分（失败不影响同步）
            try:
                from apps.scoring.scoring_engine import score_session
                score_session(session)
            except Exception:
                logger.exception('auto-scoring after sync failed for session %s', session.id)

        return result

    def _sync_session_messages(self, session, dify_user_id, dify_conv_id):
        """同步会话消息，返回新增消息数"""
        last_local = ChatLog.objects.filter(
            session=session
        ).order_by('-created_at').first()

        messages, has_more = self.client.get_messages(
            dify_user_id, dify_conv_id, limit=50
        )

        new_count = 0
        for msg in reversed(messages):  # 正序处理
            if last_local and msg['id'] == last_local.dify_message_id:
                continue  # 已同步

            if ChatLog.objects.filter(dify_message_id=msg['id']).exists():
                continue

            # 提取阶段信息（先按 inputs.current_stage，再用 normalizer 兜底中文）
            stage_key = ''
            inputs = msg.get('inputs', {})
            if isinstance(inputs, dict):
                raw_stage = inputs.get('current_stage', '')
                from .services.chat_service import _normalize_stage
                stage_key = _normalize_stage(raw_stage)

            # 计算消息索引
            msg_index = ChatLog.objects.filter(session=session).count() + 1

            # 解析token用量
            usage = msg.get('usage', {})
            token_count = 0
            if isinstance(usage, dict):
                token_count = usage.get('total_tokens', 0)

            # 解析时间
            created_at = None
            ts = msg.get('created_at')
            if ts:
                try:
                    created_at = datetime.fromtimestamp(ts, tz=timezone.get_current_timezone())
                except (TypeError, ValueError):
                    created_at = timezone.now()

            ChatLog.objects.create(
                session=session,
                dify_message_id=msg['id'],
                query_text=msg.get('query', ''),
                answer_text=msg.get('answer', ''),
                stage_key=stage_key,
                message_index=msg_index,
                token_count=token_count,
                inputs_data=json.dumps(inputs, ensure_ascii=False),
                created_at=created_at or timezone.now(),
            )
            new_count += 1

        return new_count

    def _update_session_state(self, session):
        """更新会话统计信息"""
        logs = session.logs.all()
        session.total_messages = logs.count()
        session.total_tokens = sum(log.token_count for log in logs)

        # 更新阶段
        last_log = logs.order_by('-created_at').first()
        if last_log and last_log.stage_key:
            session.current_stage = last_log.stage_key

        # 收集已完成阶段
        stages_seen = set()
        for log in logs:
            if log.stage_key:
                stages_seen.add(log.stage_key)
        session.completed_stages = json.dumps(list(stages_seen), ensure_ascii=False)

        # 检查是否可标记为完成
        if session.total_messages > 0:
            last_msg_time = logs.order_by('-created_at').first().created_at
            now = timezone.now()
            inactive_seconds = (now - last_msg_time).total_seconds()
            if inactive_seconds > 3600:  # 1小时无活动视为完成
                session.status = 'completed'
                if not session.ended_at:
                    session.ended_at = last_msg_time

        session.save()


def sync_dify_logs_command():
    """供Django管理命令调用的入口"""
    service = DifySyncService()
    return service.sync_all_active_users()
