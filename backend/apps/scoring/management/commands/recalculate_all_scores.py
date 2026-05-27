from django.core.management.base import BaseCommand

from apps.chat_logs.models import ConversationSession
from apps.dify_integration.models import LearningWorkflow
from apps.scoring.models import ScoreDetail, StudentScore
from apps.scoring.scoring_engine import ScoringEngine


class Command(BaseCommand):
    help = '为所有会话补算自动评分（即便 stage_key 缺失也会写入 0 分记录，让 dashboard 平均分有真实样本）'

    def add_arguments(self, parser):
        parser.add_argument(
            '--only-missing', action='store_true',
            help='只为还没有 StudentScore 的会话补算',
        )

    def handle(self, *args, **options):
        only_missing = options['only_missing']
        engine = ScoringEngine()
        default_workflow = LearningWorkflow.objects.first()

        sessions = ConversationSession.objects.all()
        if only_missing:
            scored_session_ids = set(
                StudentScore.objects.values_list('session_id', flat=True)
            )
            sessions = sessions.exclude(id__in=scored_session_ids)

        total = sessions.count()
        created = updated = skipped = 0
        self.stdout.write(f'扫描 {total} 个会话...')

        for session in sessions:
            workflow = session.workflow or default_workflow
            if not workflow:
                skipped += 1
                continue

            chat_logs = list(session.logs.all())
            score_data = engine.calculate_score(session, workflow, chat_logs)

            score, was_created = StudentScore.objects.update_or_create(
                session=session,
                defaults={
                    'student': session.user,
                    'workflow': workflow,
                    **score_data,
                    'status': 'pending_review',
                },
            )

            details_data = engine.make_score_details(session, workflow, chat_logs)
            ScoreDetail.objects.filter(score=score).delete()
            for detail in details_data:
                ScoreDetail.objects.create(score=score, **detail)

            if was_created:
                created += 1
            else:
                updated += 1

        self.stdout.write(self.style.SUCCESS(
            f'完成 — 新建 {created}，更新 {updated}，跳过 {skipped}（无 workflow）。'
        ))
