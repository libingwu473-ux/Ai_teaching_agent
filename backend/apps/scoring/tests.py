import json
from datetime import timedelta
from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase
from rest_framework_simplejwt.tokens import RefreshToken

from apps.chat_logs.models import ChatLog, ConversationSession
from apps.dify_integration.models import LearningWorkflow, WorkflowStage
from apps.scoring.models import ScoreDetail, StudentScore, ScoringConfig
from apps.scoring.scoring_engine import ScoringEngine

User = get_user_model()


def _user(username, role='student'):
    return User.objects.create_user(
        username=username,
        email=f'{username}@example.com',
        password='secret123',
        display_name=username,
        role=role,
    )


def _jwt(client, user):
    client.credentials(
        HTTP_AUTHORIZATION=f'Bearer {RefreshToken.for_user(user).access_token}'
    )


def _make_workflow(teacher):
    wf = LearningWorkflow.objects.create(
        name='测试流程', teacher=teacher, is_published=True
    )
    WorkflowStage.objects.create(
        workflow=wf, name='概念', stage_key='stage_concept',
        order_index=1, expected_min_messages=2, expected_min_minutes=5,
        weight=Decimal('0.35'),
    )
    WorkflowStage.objects.create(
        workflow=wf, name='练习', stage_key='stage_practice',
        order_index=2, expected_min_messages=3, expected_min_minutes=10,
        weight=Decimal('0.40'),
    )
    WorkflowStage.objects.create(
        workflow=wf, name='总结', stage_key='stage_summary',
        order_index=3, expected_min_messages=2, expected_min_minutes=5,
        weight=Decimal('0.25'),
    )
    return wf


def _make_log(session, idx, stage_key, created_offset_seconds=0):
    log = ChatLog.objects.create(
        session=session,
        dify_message_id=f'msg-{session.id}-{idx}',
        query_text=f'q{idx}',
        answer_text=f'a{idx}',
        stage_key=stage_key,
        message_index=idx,
    )
    if created_offset_seconds:
        # auto_now_add 已设置，需 update 强制改 created_at
        ChatLog.objects.filter(pk=log.pk).update(
            created_at=session.started_at + timedelta(seconds=created_offset_seconds)
        )
        log.refresh_from_db()
    return log


class ScoringEngineUnitTests(APITestCase):
    """D1-D6: ScoringEngine 纯单元测试"""

    def setUp(self):
        self.teacher = _user('teach', 'teacher')
        self.student = _user('stu', 'student')
        self.wf = _make_workflow(self.teacher)
        self.session = ConversationSession.objects.create(
            user=self.student,
            workflow=self.wf,
            dify_conversation_id='conv-D',
            status='active',
        )
        # 把 started_at 强制设为 30 分钟前（覆盖 auto_now_add）
        ConversationSession.objects.filter(pk=self.session.pk).update(
            started_at=timezone.now() - timedelta(minutes=30),
            ended_at=timezone.now(),
        )
        self.session.refresh_from_db()

    def test_D1_no_stage_key_yields_zero(self):
        # 7 条无 stage_key 的日志 — CLAUDE.md 警示的静默失败
        for i in range(1, 8):
            _make_log(self.session, i, stage_key='')

        engine = ScoringEngine()
        chat_logs = list(self.session.logs.all())
        result = engine.calculate_score(self.session, self.wf, chat_logs)

        self.assertEqual(float(result['auto_stage_completion']), 0.0)
        self.assertEqual(float(result['auto_sequence_score']), 0.0)
        # 总分 = stage(0)*0.4 + seq(0)*0.25 + time(~100)*0.15 + engagement(100)*0.20
        # 即便 stage/seq=0, total 也不会全是 0，所以这里断言两个核心维度是 0
        self.assertLess(float(result['auto_total_score']), 40)

    def test_D2_full_three_stages_high_score(self):
        # 完整顺序、足够消息：concept x2, practice x3, summary x2
        for i, key in enumerate(
            ['stage_concept'] * 2 + ['stage_practice'] * 3 + ['stage_summary'] * 2,
            start=1,
        ):
            _make_log(self.session, i, key, created_offset_seconds=i * 60)

        engine = ScoringEngine()
        chat_logs = list(self.session.logs.all())
        result = engine.calculate_score(self.session, self.wf, chat_logs)

        self.assertEqual(float(result['auto_stage_completion']), 100.0)
        self.assertEqual(float(result['auto_sequence_score']), 100.0)
        # session 持续 30 分钟，expected_total 20 分钟 → time_score=100
        self.assertEqual(float(result['auto_time_score']), 100.0)
        # 7 条消息，expected_total_msgs=7 → engagement=100
        self.assertEqual(float(result['auto_engagement_score']), 100.0)
        self.assertGreater(float(result['auto_total_score']), 95)

    def test_D3_wrong_order_reduces_sequence_score(self):
        # 倒序：summary → practice → concept
        seq = (
            ['stage_summary'] * 2 + ['stage_practice'] * 3 + ['stage_concept'] * 2
        )
        for i, key in enumerate(seq, start=1):
            _make_log(self.session, i, key, created_offset_seconds=i * 60)

        engine = ScoringEngine()
        result = engine.calculate_score(
            self.session, self.wf, list(self.session.logs.all())
        )

        # visited_sequence = [summary, practice, concept]; expected = [concept, practice, summary]
        # _calc_sequence_adherence 按 expected 顺序游标推进：
        # summary≠concept skip, practice≠concept skip, concept==concept ✓ → 1/3 = 33.33
        # 倒序情况下显著低于正确顺序的 100 分
        self.assertLess(float(result['auto_sequence_score']), 50.0)
        # 但 stage_completion 因为 3 个 stage 都到了 → 100
        self.assertEqual(float(result['auto_stage_completion']), 100.0)

    def test_D4_short_session_time_score_zero(self):
        # 强制 session 时长 < MIN_SESSION_MINUTES (5)
        ConversationSession.objects.filter(pk=self.session.pk).update(
            started_at=timezone.now() - timedelta(minutes=2),
            ended_at=timezone.now(),
        )
        self.session.refresh_from_db()

        for i, key in enumerate(['stage_concept', 'stage_practice'], start=1):
            _make_log(self.session, i, key)

        engine = ScoringEngine()
        result = engine.calculate_score(
            self.session, self.wf, list(self.session.logs.all())
        )
        self.assertEqual(float(result['auto_time_score']), 0.0)

    def test_D5_make_score_details_one_per_stage(self):
        for i, key in enumerate(
            ['stage_concept'] * 2 + ['stage_practice'] * 1, start=1
        ):
            _make_log(self.session, i, key, created_offset_seconds=i * 30)

        engine = ScoringEngine()
        details = engine.make_score_details(
            self.session, self.wf, list(self.session.logs.all())
        )

        self.assertEqual(len(details), 3)  # 一个流程 3 个阶段
        by_stage = {d['stage_id']: d for d in details}

        concept_stage = self.wf.stages.get(stage_key='stage_concept')
        self.assertTrue(by_stage[concept_stage.id]['is_completed'])
        self.assertEqual(by_stage[concept_stage.id]['message_count'], 2)

        practice_stage = self.wf.stages.get(stage_key='stage_practice')
        # practice 需要 3 条，只给了 1 条 → 未完成
        self.assertFalse(by_stage[practice_stage.id]['is_completed'])
        self.assertEqual(by_stage[practice_stage.id]['message_count'], 1)

        summary_stage = self.wf.stages.get(stage_key='stage_summary')
        # summary 没有日志
        self.assertFalse(by_stage[summary_stage.id]['is_completed'])
        self.assertEqual(by_stage[summary_stage.id]['message_count'], 0)

    def test_D6_total_is_weighted_sum(self):
        # 构造场景使各维度分数已知
        for i, key in enumerate(
            ['stage_concept'] * 2 + ['stage_practice'] * 3 + ['stage_summary'] * 2,
            start=1,
        ):
            _make_log(self.session, i, key, created_offset_seconds=i * 60)

        engine = ScoringEngine()
        result = engine.calculate_score(
            self.session, self.wf, list(self.session.logs.all())
        )

        expected_total = (
            float(result['auto_stage_completion']) * 0.40
            + float(result['auto_sequence_score']) * 0.25
            + float(result['auto_time_score']) * 0.15
            + float(result['auto_engagement_score']) * 0.20
        )
        self.assertAlmostEqual(
            float(result['auto_total_score']), round(expected_total, 2), places=1
        )


class ScoringAPITests(APITestCase):
    """D7-D10: /api/teacher/* endpoints"""

    def setUp(self):
        self.teacher = _user('t1', 'teacher')
        self.student = _user('s1', 'student')
        self.wf = _make_workflow(self.teacher)
        self.session = ConversationSession.objects.create(
            user=self.student,
            workflow=self.wf,
            dify_conversation_id='conv-api',
            status='active',
        )
        ConversationSession.objects.filter(pk=self.session.pk).update(
            started_at=timezone.now() - timedelta(minutes=30),
            ended_at=timezone.now(),
        )
        self.session.refresh_from_db()

        for i, key in enumerate(
            ['stage_concept'] * 2 + ['stage_practice'] * 3 + ['stage_summary'] * 2,
            start=1,
        ):
            _make_log(self.session, i, key, created_offset_seconds=i * 60)

    def test_D7_student_forbidden_on_teacher_list(self):
        _jwt(self.client, self.student)
        resp = self.client.get(reverse('teacher-students'))
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_D8_put_score_writes_reviewed_by_and_reviewed_at(self):
        # 先创建一条评分
        score = StudentScore.objects.create(
            session=self.session, student=self.student, workflow=self.wf,
            auto_total_score=Decimal('80.00'),
        )
        self.assertIsNone(score.reviewed_by)
        self.assertIsNone(score.reviewed_at)

        _jwt(self.client, self.teacher)
        resp = self.client.put(
            reverse('teacher-score-detail', args=[score.id]),
            {'teacher_score': '88.50', 'teacher_comment': '不错',
             'status': 'reviewed'},
            format='json',
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

        score.refresh_from_db()
        self.assertEqual(score.reviewed_by_id, self.teacher.id)
        self.assertIsNotNone(score.reviewed_at)
        self.assertEqual(float(score.teacher_score), 88.5)
        self.assertEqual(score.status, 'reviewed')

    def test_D9_trigger_scoring_creates_score_and_details(self):
        _jwt(self.client, self.teacher)
        resp = self.client.post(
            reverse('teacher-scoring-trigger'),
            {'session_id': self.session.id},
            format='json',
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

        body = resp.json()
        self.assertEqual(body['session_id'], self.session.id)
        self.assertEqual(body['student_id'], self.student.id)
        # 完整 3 阶段的高质量会话 → 总分应较高
        self.assertGreater(float(body['auto_total_score']), 95)

        score = StudentScore.objects.get(session=self.session)
        self.assertEqual(ScoreDetail.objects.filter(score=score).count(), 3)
        self.assertEqual(score.status, 'pending_review')

    def test_D10_teacher_stats_shape(self):
        _jwt(self.client, self.teacher)
        resp = self.client.get(reverse('teacher-stats'))
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

        body = resp.json()
        for k in (
            'total_students', 'active_students', 'total_sessions',
            'average_score', 'stage_completion_rate', 'daily_active_users',
        ):
            self.assertIn(k, body)
        self.assertEqual(body['total_students'], 1)
        self.assertEqual(body['total_sessions'], 1)
        self.assertEqual(len(body['daily_active_users']), 7)
        # stage_completion_rate 是按 WorkflowStage 全表统计的
        self.assertIsInstance(body['stage_completion_rate'], dict)


class ScoreSessionHelperTests(APITestCase):
    """D11-D13: score_session() helper — 自动评分和重算都依赖它"""

    def setUp(self):
        self.teacher = _user('helpertea', 'teacher')
        self.student = _user('helperstu', 'student')
        self.wf = _make_workflow(self.teacher)
        self.session = ConversationSession.objects.create(
            user=self.student, dify_conversation_id='conv-helper',
            workflow=self.wf, started_at=timezone.now() - timedelta(minutes=20),
        )
        for i, stage_key in enumerate(['stage_concept', 'stage_practice', 'stage_summary']):
            for j in range(3):
                ChatLog.objects.create(
                    session=self.session, dify_message_id=f'm-{i}-{j}',
                    query_text='q', answer_text='a',
                    stage_key=stage_key, message_index=i * 3 + j + 1,
                )

    def test_D11_score_session_creates_score_and_details(self):
        from apps.scoring.scoring_engine import score_session
        result = score_session(self.session)
        self.assertIsNotNone(result)
        score, created = result
        self.assertTrue(created)
        self.assertGreater(float(score.auto_total_score), 0)
        self.assertEqual(ScoreDetail.objects.filter(score=score).count(), 3)

    def test_D12_score_session_idempotent(self):
        from apps.scoring.scoring_engine import score_session
        s1, c1 = score_session(self.session)
        s2, c2 = score_session(self.session)
        self.assertTrue(c1)
        self.assertFalse(c2)
        self.assertEqual(s1.pk, s2.pk)
        # 重算不应该重复堆积明细
        self.assertEqual(ScoreDetail.objects.filter(score=s1).count(), 3)

    def test_D13_score_session_preserves_teacher_score(self):
        from apps.scoring.scoring_engine import score_session
        score, _ = score_session(self.session)
        score.teacher_score = Decimal('95.00')
        score.status = 'reviewed'
        score.save()

        # 再次自动评分，教师评分和状态不能被清掉
        score2, _ = score_session(self.session)
        self.assertEqual(float(score2.teacher_score), 95.0)
        self.assertEqual(score2.status, 'reviewed')


class RecalculateAllScoresEndpointTests(APITestCase):
    """D14-D15: /api/teacher/scoring/recalculate-all/ 权限 + 覆盖所有会话"""

    def setUp(self):
        self.url = reverse('teacher-scoring-recalc-all')
        self.teacher = _user('recalctea', 'teacher')
        self.student = _user('recalcstu', 'student')
        self.wf = _make_workflow(self.teacher)
        # 3 个会话，全都没有 score
        for i in range(3):
            sess = ConversationSession.objects.create(
                user=self.student, dify_conversation_id=f'conv-recalc-{i}',
                workflow=self.wf,
                started_at=timezone.now() - timedelta(minutes=10),
            )
            ChatLog.objects.create(
                session=sess, dify_message_id=f'msg-recalc-{i}',
                query_text='q', answer_text='a',
                stage_key='stage_concept', message_index=1,
            )

    def test_D14_student_forbidden(self):
        student = _user('recalcstu2', 'student')
        _jwt(self.client, student)
        resp = self.client.post(self.url)
        self.assertEqual(resp.status_code, 403)

    def test_D15_recalculates_creates_scores_for_all_sessions(self):
        self.assertEqual(StudentScore.objects.count(), 0)
        _jwt(self.client, self.teacher)
        resp = self.client.post(self.url)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()['processed'], 3)
        self.assertEqual(StudentScore.objects.count(), 3)


class AutoScoringOnChatEndTests(APITestCase):
    """D16: 聊天流结束后 _save_chat_log 应当自动触发评分"""

    def test_D16_save_chat_log_auto_scores_session(self):
        from apps.dify_integration.services.chat_service import DifyChatService

        teacher = _user('autotea', 'teacher')
        student = _user('autostu', 'student')
        wf = _make_workflow(teacher)
        # 评分依赖 LearningWorkflow.objects.first() 兜底，确保只有这一个
        self.assertEqual(LearningWorkflow.objects.count(), 1)

        svc = DifyChatService()
        collected = {
            'conversation_id': 'dify-conv-auto-score',
            'message_id': 'msg-auto-1',
            'answer': '回答内容',
            'current_stage': 'stage_concept',
            'token_usage': {'total_tokens': 10},
            'task_id': '',
            'answer_chunks': [],
        }
        result = svc._save_chat_log(
            user=student, query='问题', collected=collected, response_time_ms=100,
        )

        # session 应该被建出来
        session = ConversationSession.objects.get(dify_conversation_id='dify-conv-auto-score')
        self.assertEqual(session.user_id, student.id)
        # 自动评分应当已生成
        self.assertTrue(
            StudentScore.objects.filter(session=session).exists(),
            '聊天结束后未自动生成 StudentScore',
        )
        score = StudentScore.objects.get(session=session)
        self.assertEqual(score.student_id, student.id)
        self.assertGreaterEqual(float(score.auto_total_score), 0)


class TimeAndStageTrackingTests(APITestCase):
    """E1-E4: 时长和阶段状态的回归 — 修复前 updated_at 漂移、单消息阶段耗时为 0、首消息 stage 未入 completed"""

    def setUp(self):
        self.teacher = _user('timetea', 'teacher')
        self.student = _user('timestu', 'student')
        self.wf = _make_workflow(self.teacher)

    @staticmethod
    def _force_time(obj, field, value):
        """绕过 auto_now/auto_now_add，强制写入指定时间。"""
        type(obj).objects.filter(pk=obj.pk).update(**{field: value})
        obj.refresh_from_db()

    def test_E1_time_score_uses_last_log_not_updated_at(self):
        from apps.scoring.scoring_engine import ScoringEngine
        now = timezone.now()
        sess = ConversationSession.objects.create(
            user=self.student, dify_conversation_id='conv-time', workflow=self.wf,
        )
        self._force_time(sess, 'started_at', now - timedelta(hours=1))
        log = ChatLog.objects.create(
            session=sess, dify_message_id='t-1', query_text='q', answer_text='a',
            stage_key='stage_concept', message_index=1,
        )
        self._force_time(log, 'created_at', now - timedelta(minutes=30))

        engine = ScoringEngine()
        stages = list(self.wf.stages.order_by('order_index'))
        time_score = engine._calc_time_investment(sess, stages)
        # duration = 30min, expected_total = 20min → ratio=1.0 → 100
        self.assertGreater(time_score, 0)
        self.assertEqual(time_score, 100.0)

    def test_E2_time_score_ignores_updated_at_drift(self):
        """log 时间不变、session.save() 多次（刷新 updated_at），评分应当不变"""
        from apps.scoring.scoring_engine import ScoringEngine
        now = timezone.now()
        sess = ConversationSession.objects.create(
            user=self.student, dify_conversation_id='conv-drift', workflow=self.wf,
        )
        self._force_time(sess, 'started_at', now - timedelta(minutes=8))
        log = ChatLog.objects.create(
            session=sess, dify_message_id='d-1', query_text='q', answer_text='a',
            stage_key='stage_concept', message_index=1,
        )
        # log 时间在 6 分钟前 → duration = 2 分钟 < MIN_SESSION_MINUTES(5) → 0 分
        # 我们要的是 "log 时间在 7 分钟前 → duration = 1 分钟 但 started_at=8 min ago - log=1 min ago = 7 minutes"
        # 实际：duration = log_time - started = (now-1min) - (now-8min) = 7 分钟 → 35% → 35 分
        self._force_time(log, 'created_at', now - timedelta(minutes=1))

        engine = ScoringEngine()
        stages = list(self.wf.stages.order_by('order_index'))

        score_before = engine._calc_time_investment(sess, stages)
        self.assertGreater(score_before, 0)
        # 模拟 session 后续被反复 save（比如评分写回）—— updated_at 漂到现在
        for _ in range(3):
            sess.total_tokens += 1
            sess.save()
        score_after = engine._calc_time_investment(sess, stages)
        self.assertEqual(score_before, score_after,
                         '时长评分被 session.updated_at 影响了 — 应当只看 log 时间')

    def test_E3_stage_time_spent_works_for_single_message_stage(self):
        """单条消息的阶段也应该有非 0 耗时（从前一条 log/start 开始算）"""
        from apps.scoring.scoring_engine import ScoringEngine
        now = timezone.now()
        sess = ConversationSession.objects.create(
            user=self.student, dify_conversation_id='conv-single', workflow=self.wf,
        )
        self._force_time(sess, 'started_at', now - timedelta(minutes=10))

        l1 = ChatLog.objects.create(
            session=sess, dify_message_id='s1-1', query_text='q', answer_text='a',
            stage_key='stage_concept', message_index=1,
        )
        self._force_time(l1, 'created_at', now - timedelta(minutes=10))
        l2 = ChatLog.objects.create(
            session=sess, dify_message_id='s1-2', query_text='q', answer_text='a',
            stage_key='stage_concept', message_index=2,
        )
        self._force_time(l2, 'created_at', now - timedelta(minutes=8))
        l3 = ChatLog.objects.create(
            session=sess, dify_message_id='s2-1', query_text='q', answer_text='a',
            stage_key='stage_practice', message_index=3,
        )
        self._force_time(l3, 'created_at', now - timedelta(minutes=5))

        engine = ScoringEngine()
        chat_logs = list(sess.logs.order_by('created_at'))
        details = engine.make_score_details(sess, self.wf, chat_logs)

        by_stage = {d['stage_id']: d for d in details}
        concept = self.wf.stages.get(stage_key='stage_concept')
        practice = self.wf.stages.get(stage_key='stage_practice')

        # stage_concept 跨度：l1→l2 = 2 分钟 = 120s
        self.assertGreater(by_stage[concept.id]['time_spent_seconds'], 100)
        # stage_practice 只有 1 条 (l3) → 前一条是 l2 → 跨度 = 3 分钟 = 180s
        self.assertGreater(by_stage[practice.id]['time_spent_seconds'], 100,
                          '单消息阶段耗时仍是 0 — 应该用 [前一条 log → 本条 log] 区间')


class StageTrackingOnChatEndTests(APITestCase):
    """E5: 聊天结束后 session.current_stage / completed_stages 应当被正确写入（包括首条消息）"""

    def test_E5_first_message_populates_completed_stages(self):
        from apps.dify_integration.services.chat_service import DifyChatService

        teacher = _user('stagetea', 'teacher')
        student = _user('stagestu', 'student')
        _make_workflow(teacher)

        svc = DifyChatService()
        # 首条消息（session 不存在）
        collected = {
            'conversation_id': 'dify-conv-new', 'message_id': 'new-1',
            'answer': '', 'current_stage': 'stage_concept',
            'token_usage': {}, 'task_id': '', 'answer_chunks': ['答案'],
        }
        svc._save_chat_log(user=student, query='q', collected=collected, response_time_ms=10)

        sess = ConversationSession.objects.get(dify_conversation_id='dify-conv-new')
        self.assertEqual(sess.current_stage, 'stage_concept')
        completed = json.loads(sess.completed_stages or '[]')
        self.assertIn('stage_concept', completed,
                     '首条消息的 stage 没进入 completed_stages — 旧 bug')

        # 第二条消息（同 session，新 stage）
        collected2 = {
            'conversation_id': 'dify-conv-new', 'message_id': 'new-2',
            'answer': '', 'current_stage': 'stage_practice',
            'token_usage': {}, 'task_id': '', 'answer_chunks': ['答案2'],
        }
        svc._save_chat_log(user=student, query='q2', collected=collected2, response_time_ms=10)

        sess.refresh_from_db()
        self.assertEqual(sess.current_stage, 'stage_practice')
        completed2 = json.loads(sess.completed_stages or '[]')
        self.assertIn('stage_concept', completed2)
        self.assertIn('stage_practice', completed2)


class ScoringConfigEndpointTests(APITestCase):
    """F1-F7: /api/teacher/scoring-config/ 权限 + 读写 + 校验 + 实际生效"""

    def setUp(self):
        self.url = reverse('teacher-scoring-config')
        self.student = _user('cfgsstu', 'student')
        self.teacher = _user('cfgstea', 'teacher')

    def test_F1_student_forbidden(self):
        _jwt(self.client, self.student)
        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, 403)

    def test_F2_get_returns_defaults(self):
        _jwt(self.client, self.teacher)
        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        self.assertEqual(body['min_session_minutes'], 5)
        self.assertAlmostEqual(
            body['stage_completion_weight']
            + body['sequence_adherence_weight']
            + body['time_investment_weight']
            + body['engagement_weight'],
            1.0, places=2,
        )

    def test_F3_put_updates_min_session_minutes(self):
        _jwt(self.client, self.teacher)
        resp = self.client.put(self.url, {'min_session_minutes': 0}, format='json')
        self.assertEqual(resp.status_code, 200)
        cfg = ScoringConfig.load()
        self.assertEqual(cfg.min_session_minutes, 0)

    def test_F4_put_rejects_weight_sum_far_from_one(self):
        _jwt(self.client, self.teacher)
        resp = self.client.put(self.url, {
            'stage_completion_weight': 0.5,
            'sequence_adherence_weight': 0.5,
            'time_investment_weight': 0.5,
            'engagement_weight': 0.5,
        }, format='json')
        self.assertEqual(resp.status_code, 400)
        self.assertIn('权重之和', resp.json()['error'])

    def test_F5_put_rejects_weight_out_of_range(self):
        _jwt(self.client, self.teacher)
        resp = self.client.put(self.url, {'stage_completion_weight': 1.5}, format='json')
        self.assertEqual(resp.status_code, 400)

    def test_F6_engine_reads_from_db(self):
        """新建 engine 实例应当从 DB 拿 config —— 修改 DB 后立即生效"""
        cfg = ScoringConfig.load()
        cfg.min_session_minutes = 0
        cfg.save()

        engine = ScoringEngine()
        self.assertEqual(engine.config['MIN_SESSION_MINUTES'], 0)

    def test_F7_min_session_minutes_zero_unblocks_short_session(self):
        """关键场景：教师把 min_session_minutes 调成 0 后，2 分钟的会话应当有时间投入分"""
        student = _user('shortstu', 'student')
        wf = _make_workflow(self.teacher)
        now = timezone.now()
        sess = ConversationSession.objects.create(
            user=student, dify_conversation_id='conv-short', workflow=wf,
        )
        ConversationSession.objects.filter(pk=sess.pk).update(
            started_at=now - timedelta(minutes=2)
        )
        sess.refresh_from_db()
        log = ChatLog.objects.create(
            session=sess, dify_message_id='short-1', query_text='q', answer_text='a',
            stage_key='stage_concept', message_index=1,
        )
        ChatLog.objects.filter(pk=log.pk).update(created_at=now - timedelta(seconds=10))

        # 默认 5 分钟门槛 → 0 分
        engine_strict = ScoringEngine()
        stages = list(wf.stages.order_by('order_index'))
        self.assertEqual(engine_strict._calc_time_investment(sess, stages), 0.0)

        # 教师调成 0 → 有分
        cfg = ScoringConfig.load()
        cfg.min_session_minutes = 0
        cfg.save()
        engine_lax = ScoringEngine()
        self.assertGreater(engine_lax._calc_time_investment(sess, stages), 0)
