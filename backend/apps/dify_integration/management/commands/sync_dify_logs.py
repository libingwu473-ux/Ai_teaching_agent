from django.core.management.base import BaseCommand
from apps.dify_integration.sync_service import DifySyncService


class Command(BaseCommand):
    help = '从Dify API同步对话日志到本地数据库'

    def add_arguments(self, parser):
        parser.add_argument(
            '--user-id',
            type=int,
            help='指定同步某个用户的ID，不指定则同步所有用户',
        )

    def handle(self, *args, **options):
        service = DifySyncService()
        user_id = options.get('user_id')

        if user_id:
            from apps.dify_integration.models import DifyUserMapping
            mapping = DifyUserMapping.objects.filter(user_id=user_id, is_active=True).first()
            if not mapping:
                self.stderr.write(self.style.ERROR(f'用户 {user_id} 未找到Dify映射'))
                return
            result = service.sync_user_conversations(mapping)
            self.stdout.write(self.style.SUCCESS(
                f'用户 {user_id} 同步完成: 新增{result["new_sessions"]}个会话, {result["new_messages"]}条消息'
            ))
        else:
            stats = service.sync_all_active_users()
            self.stdout.write(self.style.SUCCESS(
                f'同步完成: {stats["total"]}个用户, '
                f'新增{stats["new_sessions"]}个会话, '
                f'新增{stats["new_messages"]}条消息, '
                f'{stats["errors"]}个错误'
            ))
