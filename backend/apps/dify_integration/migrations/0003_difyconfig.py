from django.conf import settings
from django.db import migrations, models


def seed_default_config(apps, schema_editor):
    DifyConfig = apps.get_model('dify_integration', 'DifyConfig')
    if DifyConfig.objects.filter(pk=1).exists():
        return
    defaults = settings.DIFY_CONFIG
    DifyConfig.objects.create(
        pk=1,
        api_base_url=defaults.get('API_BASE_URL', ''),
        api_key=defaults.get('API_KEY', ''),
        app_id=defaults.get('APP_ID', ''),
        chatflow_id=defaults.get('CHATFLOW_ID', ''),
        verify_ssl=defaults.get('VERIFY_SSL', False),
        timeout=defaults.get('TIMEOUT', 60),
        max_retries=defaults.get('MAX_RETRIES', 3),
    )


def unseed_default_config(apps, schema_editor):
    DifyConfig = apps.get_model('dify_integration', 'DifyConfig')
    DifyConfig.objects.filter(pk=1).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('dify_integration', '0002_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='DifyConfig',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('api_base_url', models.CharField(max_length=500, verbose_name='API 基础地址')),
                ('api_key', models.CharField(max_length=200, verbose_name='API 密钥')),
                ('app_id', models.CharField(blank=True, default='', max_length=100, verbose_name='应用 ID')),
                ('chatflow_id', models.CharField(blank=True, default='', max_length=100, verbose_name='Chatflow ID')),
                ('verify_ssl', models.BooleanField(default=False, verbose_name='校验 SSL 证书')),
                ('timeout', models.IntegerField(default=60, verbose_name='请求超时(秒)')),
                ('max_retries', models.IntegerField(default=3, verbose_name='最大重试次数')),
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
                'verbose_name': 'Dify 平台配置',
                'verbose_name_plural': 'Dify 平台配置',
                'db_table': 'dify_config',
            },
        ),
        migrations.RunPython(seed_default_config, unseed_default_config),
    ]
