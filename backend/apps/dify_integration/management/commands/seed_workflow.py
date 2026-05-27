from django.core.management.base import BaseCommand
from apps.dify_integration.models import LearningWorkflow, WorkflowStage
from apps.users.models import User


class Command(BaseCommand):
    help = '创建默认教学流程和阶段'

    def handle(self, *args, **options):
        teacher = User.objects.filter(role='teacher').first()
        if not teacher:
            teacher = User.objects.create_user(
                username='default_teacher',
                email='admin@school.edu.cn',
                password='admin123',
                display_name='默认教师',
                role='teacher',
            )

        workflow, created = LearningWorkflow.objects.get_or_create(
            name='AI教学标准流程',
            defaults={
                'teacher': teacher,
                'description': '概念讲解 → 练习测验 → 总结评估',
                'dify_app_id': 'cXonhxTDBXW6BoPi',
                'is_published': True,
            }
        )

        if created:
            stages = [
                {'name': '概念讲解', 'stage_key': 'stage_concept', 'order': 1,
                 'desc': '教师讲解核心概念，学生理解并提问', 'msgs': 2, 'mins': 5, 'w': 0.35},
                {'name': '练习测验', 'stage_key': 'stage_practice', 'order': 2,
                 'desc': '学生完成练习，教师答疑', 'msgs': 3, 'mins': 10, 'w': 0.40},
                {'name': '总结评估', 'stage_key': 'stage_summary', 'order': 3,
                 'desc': '总结知识点，评估学习效果', 'msgs': 2, 'mins': 5, 'w': 0.25},
            ]
            for s in stages:
                WorkflowStage.objects.create(
                    workflow=workflow,
                    name=s['name'],
                    stage_key=s['stage_key'],
                    order_index=s['order'],
                    description=s['desc'],
                    expected_min_messages=s['msgs'],
                    expected_min_minutes=s['mins'],
                    weight=s['w'],
                )

            self.stdout.write(self.style.SUCCESS(f'流程 "{workflow.name}" 已创建，包含 {len(stages)} 个阶段'))
        else:
            self.stdout.write(self.style.WARNING(f'流程 "{workflow.name}" 已存在'))
            # Ensure stages exist
            if not workflow.stages.exists():
                stages = [
                    {'name': '概念讲解', 'stage_key': 'stage_concept', 'order': 1,
                     'desc': '教师讲解核心概念，学生理解并提问', 'msgs': 2, 'mins': 5, 'w': 0.35},
                    {'name': '练习测验', 'stage_key': 'stage_practice', 'order': 2,
                     'desc': '学生完成练习，教师答疑', 'msgs': 3, 'mins': 10, 'w': 0.40},
                    {'name': '总结评估', 'stage_key': 'stage_summary', 'order': 3,
                     'desc': '总结知识点，评估学习效果', 'msgs': 2, 'mins': 5, 'w': 0.25},
                ]
                for s in stages:
                    WorkflowStage.objects.create(
                        workflow=workflow,
                        name=s['name'],
                        stage_key=s['stage_key'],
                        order_index=s['order'],
                        description=s['desc'],
                        expected_min_messages=s['msgs'],
                        expected_min_minutes=s['mins'],
                        weight=s['w'],
                    )
                self.stdout.write(self.style.SUCCESS('补充创建了阶段数据'))
