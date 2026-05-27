from django.db import migrations, models


def lower_threshold_if_default(apps, schema_editor):
    """对已经存在的单例 ScoringConfig，如果还在用旧默认值 5，自动降到 1。
    教师如果之前手动调过别的值，保留不动。"""
    ScoringConfig = apps.get_model('scoring', 'ScoringConfig')
    ScoringConfig.objects.filter(pk=1, min_session_minutes=5).update(min_session_minutes=1)


def reverse_noop(apps, schema_editor):
    # 不还原：降低后无法判断原值
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('scoring', '0003_scoringconfig'),
    ]

    operations = [
        migrations.AlterField(
            model_name='scoringconfig',
            name='min_session_minutes',
            field=models.IntegerField(default=1, verbose_name='最小会话分钟'),
        ),
        migrations.RunPython(lower_threshold_if_default, reverse_noop),
    ]
