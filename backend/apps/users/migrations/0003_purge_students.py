"""清空所有存量学生及其级联数据。

按用户规划，重建用户层级前清空所有 role=student 用户。
通过 CASCADE 关联，ConversationSession / ChatLog / StudentScore /
ScoreDetail / DifyUserMapping 会一并删除。
"""
from django.db import migrations


def purge_students(apps, schema_editor):
    User = apps.get_model('users', 'User')
    User.objects.filter(role='student').delete()


def noop_reverse(apps, schema_editor):
    # 不可逆：已删除的学生数据无法恢复
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0002_major_user_gender_user_must_change_password_and_more'),
    ]

    operations = [
        migrations.RunPython(purge_students, noop_reverse),
    ]
