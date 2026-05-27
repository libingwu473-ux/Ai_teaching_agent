from django.conf import settings
from django.db import migrations, models


def seed_default_scoring_config(apps, schema_editor):
    ScoringConfig = apps.get_model('scoring', 'ScoringConfig')
    if ScoringConfig.objects.filter(pk=1).exists():
        return
    d = settings.SCORING_CONFIG
    ScoringConfig.objects.create(
        pk=1,
        stage_completion_weight=d.get('STAGE_COMPLETION_WEIGHT', 0.40),
        sequence_adherence_weight=d.get('SEQUENCE_ADHERENCE_WEIGHT', 0.25),
        time_investment_weight=d.get('TIME_INVESTMENT_WEIGHT', 0.15),
        engagement_weight=d.get('ENGAGEMENT_WEIGHT', 0.20),
        min_session_minutes=d.get('MIN_SESSION_MINUTES', 5),
        max_score=d.get('MAX_SCORE', 100),
    )


def unseed(apps, schema_editor):
    ScoringConfig = apps.get_model('scoring', 'ScoringConfig')
    ScoringConfig.objects.filter(pk=1).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('scoring', '0002_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='ScoringConfig',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('stage_completion_weight', models.DecimalField(decimal_places=2, default=0.40, max_digits=3, verbose_name='阶段完成度权重')),
                ('sequence_adherence_weight', models.DecimalField(decimal_places=2, default=0.25, max_digits=3, verbose_name='流程遵循度权重')),
                ('time_investment_weight', models.DecimalField(decimal_places=2, default=0.15, max_digits=3, verbose_name='时间投入权重')),
                ('engagement_weight', models.DecimalField(decimal_places=2, default=0.20, max_digits=3, verbose_name='参与度权重')),
                ('min_session_minutes', models.IntegerField(default=5, verbose_name='最小会话分钟')),
                ('max_score', models.IntegerField(default=100, verbose_name='满分')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='更新时间')),
                ('updated_by', models.ForeignKey(
                    blank=True, null=True,
                    on_delete=models.deletion.SET_NULL,
                    related_name='+',
                    to=settings.AUTH_USER_MODEL,
                    verbose_name='最后修改人',
                )),
            ],
            options={
                'verbose_name': '评分参数配置',
                'verbose_name_plural': '评分参数配置',
                'db_table': 'scoring_config',
            },
        ),
        migrations.RunPython(seed_default_scoring_config, unseed),
    ]
