"""创建（或重置）超级管理员账号 admin / admin123。"""
from django.core.management.base import BaseCommand
from apps.users.models import User


class Command(BaseCommand):
    help = '创建超级管理员 admin（密码 admin123）。已存在则跳过。'

    def add_arguments(self, parser):
        parser.add_argument(
            '--reset-password', action='store_true',
            help='若 admin 已存在，则重置其密码为 admin123'
        )

    def handle(self, *args, **options):
        username = 'admin'
        password = 'admin123'
        user = User.objects.filter(username=username).first()
        if user is None:
            user = User.objects.create(
                username=username,
                email='admin@school.local',
                display_name='超级管理员',
                role='admin',
                is_staff=True,
                is_superuser=True,
                must_change_password=True,
            )
            user.set_password(password)
            user.save()
            self.stdout.write(self.style.SUCCESS(
                f'已创建超级管理员 {username} / {password}（首次登录请修改密码）'
            ))
            return

        changed = False
        if user.role != 'admin':
            user.role = 'admin'
            changed = True
        if not user.is_staff:
            user.is_staff = True
            changed = True
        if not user.is_superuser:
            user.is_superuser = True
            changed = True
        if options.get('reset_password'):
            user.set_password(password)
            user.must_change_password = True
            changed = True
            self.stdout.write(self.style.WARNING(f'密码已重置为 {password}'))
        if changed:
            user.save()
            self.stdout.write(self.style.SUCCESS(f'已更新 {username} 的角色/权限'))
        else:
            self.stdout.write(self.style.WARNING(f'{username} 已存在，未做改动'))
