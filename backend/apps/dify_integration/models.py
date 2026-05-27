from django.db import models
from django.conf import settings


class DifyConfig(models.Model):
    """Dify 平台连接配置（单例：始终只有 id=1 这一行）。教师/管理员可在前端修改。"""
    api_base_url = models.CharField(max_length=500, verbose_name='API 基础地址')
    api_key = models.CharField(max_length=200, verbose_name='API 密钥')
    app_id = models.CharField(max_length=100, blank=True, default='', verbose_name='应用 ID')
    chatflow_id = models.CharField(max_length=100, blank=True, default='', verbose_name='Chatflow ID')
    verify_ssl = models.BooleanField(default=False, verbose_name='校验 SSL 证书')
    timeout = models.IntegerField(default=60, verbose_name='请求超时(秒)')
    max_retries = models.IntegerField(default=3, verbose_name='最大重试次数')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='+', verbose_name='最后修改人'
    )

    class Meta:
        db_table = 'dify_config'
        verbose_name = 'Dify 平台配置'
        verbose_name_plural = verbose_name

    def __str__(self):
        return f'DifyConfig({self.api_base_url})'

    def save(self, *args, **kwargs):
        self.pk = 1
        super().save(*args, **kwargs)

    @classmethod
    def load(cls):
        """获取单例配置；若不存在则用 settings.DIFY_CONFIG 作为初值创建。"""
        from django.conf import settings as dj_settings
        obj = cls.objects.filter(pk=1).first()
        if obj is None:
            defaults = dj_settings.DIFY_CONFIG
            obj = cls.objects.create(
                pk=1,
                api_base_url=defaults.get('API_BASE_URL', ''),
                api_key=defaults.get('API_KEY', ''),
                app_id=defaults.get('APP_ID', ''),
                chatflow_id=defaults.get('CHATFLOW_ID', ''),
                verify_ssl=defaults.get('VERIFY_SSL', False),
                timeout=defaults.get('TIMEOUT', 60),
                max_retries=defaults.get('MAX_RETRIES', 3),
            )
        return obj


class DifyUserMapping(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='dify_mapping',
        verbose_name='系统用户'
    )
    dify_user_id = models.CharField(
        max_length=100, unique=True, db_index=True,
        verbose_name='Dify用户ID'
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    is_active = models.BooleanField(default=True, verbose_name='是否活跃')

    class Meta:
        db_table = 'dify_user_mappings'
        verbose_name = 'Dify用户映射'
        verbose_name_plural = verbose_name

    def __str__(self):
        return f'{self.user.username} → {self.dify_user_id}'


class LearningWorkflow(models.Model):
    name = models.CharField(max_length=200, verbose_name='流程名称')
    description = models.TextField(blank=True, verbose_name='描述')
    teacher = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT,
        related_name='workflows', verbose_name='所属教师'
    )
    dify_app_id = models.CharField(max_length=100, blank=True, verbose_name='Dify应用ID')
    is_published = models.BooleanField(default=False, verbose_name='已发布')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')

    class Meta:
        db_table = 'learning_workflows'
        verbose_name = '教学流程'
        verbose_name_plural = verbose_name

    def __str__(self):
        return self.name


class WorkflowStage(models.Model):
    workflow = models.ForeignKey(
        LearningWorkflow, on_delete=models.CASCADE,
        related_name='stages', verbose_name='所属流程'
    )
    name = models.CharField(max_length=200, verbose_name='阶段名称')
    stage_key = models.CharField(max_length=100, verbose_name='阶段标识')
    order_index = models.IntegerField(verbose_name='顺序索引')
    description = models.TextField(blank=True, verbose_name='描述')
    expected_min_messages = models.IntegerField(default=1, verbose_name='预期最少消息数')
    expected_min_minutes = models.IntegerField(default=2, verbose_name='预期最少耗时(分)')
    weight = models.DecimalField(max_digits=3, decimal_places=2, default=0.25, verbose_name='评分权重')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')

    class Meta:
        db_table = 'workflow_stages'
        verbose_name = '流程阶段'
        verbose_name_plural = verbose_name
        unique_together = [('workflow', 'stage_key'), ('workflow', 'order_index')]
        ordering = ['order_index']

    def __str__(self):
        return f'{self.workflow.name} - {self.name}'
