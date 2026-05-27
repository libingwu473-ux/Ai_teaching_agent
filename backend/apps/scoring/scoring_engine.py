import json
import logging
from django.conf import settings
from datetime import timedelta

logger = logging.getLogger('scoring')


class ScoringEngine:
    """教学评分引擎"""

    def __init__(self, config=None):
        if config is not None:
            self.config = config
        else:
            # 优先从 DB 读 ScoringConfig；DB 表还没建好或为空时 fallback 到 settings
            try:
                from apps.scoring.models import ScoringConfig
                self.config = ScoringConfig.load().to_engine_dict()
            except Exception:
                self.config = settings.SCORING_CONFIG

    def calculate_score(self, session, workflow, chat_logs):
        """计算会话的综合评分"""
        stages = list(workflow.stages.order_by('order_index')) if workflow else []
        if not stages:
            return self._default_score()

        # 1. 阶段完成度 (40%)
        stage_completion = self._calc_stage_completion(stages, chat_logs)
        # 2. 流程遵循度 (25%)
        sequence_adherence = self._calc_sequence_adherence(stages, chat_logs)
        # 3. 时间投入 (15%)
        time_investment = self._calc_time_investment(session, stages)
        # 4. 参与度 (20%)
        engagement = self._calc_engagement(session, stages, chat_logs)

        total = (
            stage_completion * self.config['STAGE_COMPLETION_WEIGHT'] +
            sequence_adherence * self.config['SEQUENCE_ADHERENCE_WEIGHT'] +
            time_investment * self.config['TIME_INVESTMENT_WEIGHT'] +
            engagement * self.config['ENGAGEMENT_WEIGHT']
        )

        return {
            'auto_stage_completion': round(stage_completion, 2),
            'auto_sequence_score': round(sequence_adherence, 2),
            'auto_time_score': round(time_investment, 2),
            'auto_engagement_score': round(engagement, 2),
            'auto_total_score': round(total, 2),
        }

    def _calc_stage_completion(self, stages, chat_logs):
        """阶段完成度评分。
        与 make_score_details 保持同一判定口径：某阶段要"完成"，必须达到
        WorkflowStage.expected_min_messages。否则前端会出现总分阶段完成度=100
        但阶段明细全部"未完成"的矛盾。
        """
        total_stages = len(stages)
        if total_stages == 0:
            return 100.0

        # 按 stage_key 聚合每个阶段的消息数
        per_stage_count = {s.stage_key: 0 for s in stages}
        for log in chat_logs:
            if log.stage_key in per_stage_count:
                per_stage_count[log.stage_key] += 1

        completed_keys = {
            s.stage_key for s in stages
            if per_stage_count[s.stage_key] >= s.expected_min_messages
        }

        # 基础完成分
        base_score = (len(completed_keys) / total_stages) * 100

        # 顺序加分：只统计"已完成"的阶段是否按顺序被首次触达
        first_touch_order = {}
        for log in chat_logs:
            if log.stage_key in completed_keys and log.stage_key not in first_touch_order:
                first_touch_order[log.stage_key] = log.created_at

        completed_in_order = 0
        last_order = 0
        for stage in sorted(stages, key=lambda s: s.order_index):
            if stage.stage_key in first_touch_order and stage.order_index >= last_order:
                completed_in_order += 1
                last_order = stage.order_index

        order_bonus = (completed_in_order / total_stages) * 10

        return min(base_score + order_bonus, 100.0)

    def _calc_sequence_adherence(self, stages, chat_logs):
        """流程遵循度评分"""
        expected_order = [s.stage_key for s in stages]

        visited_sequence = []
        for log in chat_logs:
            if log.stage_key and (not visited_sequence or visited_sequence[-1] != log.stage_key):
                visited_sequence.append(log.stage_key)

        if not visited_sequence:
            return 0.0

        # 最长公共子序列
        correct_positions = 0
        for stage_key in visited_sequence:
            if correct_positions < len(expected_order) and stage_key == expected_order[correct_positions]:
                correct_positions += 1

        return (correct_positions / len(expected_order)) * 100 if expected_order else 100.0

    def _calc_time_investment(self, session, stages):
        """时间投入评分。
        会话"耗时" = 第一条 log → 最后一条 log。
        不要用 session.updated_at，否则只要 session 被任何更新触动（包括评分自身写入 token），
        耗时会一直增长，导致已结束的会话被错误地评满分。
        """
        logs = list(session.logs.order_by('created_at'))
        if len(logs) < 1 or not session.started_at:
            return 0.0

        if session.ended_at:
            end_time = session.ended_at
        elif logs:
            end_time = logs[-1].created_at
        else:
            return 0.0

        duration_minutes = (end_time - session.started_at).total_seconds() / 60

        expected_total = sum(s.expected_min_minutes for s in stages)
        if expected_total == 0:
            expected_total = 10

        min_minutes = self.config.get('MIN_SESSION_MINUTES', 5)
        if duration_minutes < min_minutes:
            return 0.0

        ratio = min(duration_minutes / expected_total, 1.0)
        return ratio * 100

    def _calc_engagement(self, session, stages, chat_logs):
        """参与度评分"""
        total_messages = len(chat_logs)
        expected_total = sum(s.expected_min_messages for s in stages)
        if expected_total == 0:
            expected_total = max(3 * len(stages), 3)

        ratio = min(total_messages / expected_total, 1.0)
        return ratio * 100

    def _default_score(self):
        return {
            'auto_stage_completion': 0,
            'auto_sequence_score': 0,
            'auto_time_score': 0,
            'auto_engagement_score': 0,
            'auto_total_score': 0,
        }

    def make_score_details(self, session, workflow, chat_logs):
        """生成每个阶段的评分明细"""
        if not workflow:
            return []

        stages = list(workflow.stages.order_by('order_index'))
        details = []
        ordered_logs = sorted(chat_logs, key=lambda l: l.created_at)

        for stage in stages:
            stage_logs = [log for log in ordered_logs if log.stage_key == stage.stage_key]
            is_completed = len(stage_logs) >= stage.expected_min_messages

            # 阶段时长 = 该阶段第一条 log 之前的那条 log（或 session.started_at）
            # → 该阶段最后一条 log。这样单条消息的阶段也能反映"在这个阶段花了多久"。
            time_spent = 0
            if stage_logs:
                last_in_stage = stage_logs[-1]
                first_in_stage = stage_logs[0]
                # 找 first_in_stage 在 ordered_logs 里的前一条
                start_anchor = session.started_at
                for i, log in enumerate(ordered_logs):
                    if log.id == first_in_stage.id:
                        if i > 0:
                            start_anchor = ordered_logs[i - 1].created_at
                        break
                if start_anchor:
                    delta = (last_in_stage.created_at - start_anchor).total_seconds()
                    if delta > 0:
                        time_spent = int(delta)

            # 阶段得分
            completion_part = (1.0 if is_completed else 0.0) * 60
            msg_ratio = min(len(stage_logs) / max(stage.expected_min_messages, 1), 1.0) * 40
            stage_score = completion_part + msg_ratio

            details.append({
                'stage_id': stage.id,
                'is_completed': is_completed,
                'message_count': len(stage_logs),
                'time_spent_seconds': time_spent,
                'stage_score': round(stage_score, 2),
            })

        return details


def score_session(session, workflow=None):
    """对一个会话执行评分，写入或更新 StudentScore + ScoreDetail。返回 (score, created) 或 None（无法评分时）。

    供两处调用：聊天结束后的自动评分、教师手动触发。
    """
    from apps.scoring.models import StudentScore, ScoreDetail
    from apps.dify_integration.models import LearningWorkflow

    if workflow is None:
        workflow = session.workflow or LearningWorkflow.objects.first()
    if workflow is None:
        logger.info('score_session: no workflow available, skip')
        return None

    engine = ScoringEngine()
    chat_logs = list(session.logs.all().order_by('created_at'))
    score_data = engine.calculate_score(session, workflow, chat_logs)

    # 已有教师评分的话保留其状态，不要回退成 pending_review
    existing = StudentScore.objects.filter(session=session).first()
    defaults = {
        'student': session.user,
        'workflow': workflow,
        **score_data,
    }
    if existing is None or existing.teacher_score is None:
        defaults['status'] = 'pending_review'

    score, created = StudentScore.objects.update_or_create(
        session=session, defaults=defaults,
    )

    details_data = engine.make_score_details(session, workflow, chat_logs)
    ScoreDetail.objects.filter(score=score).delete()
    for detail in details_data:
        ScoreDetail.objects.create(score=score, **detail)

    return score, created
