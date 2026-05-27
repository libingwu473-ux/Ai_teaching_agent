from django.db import models
from django.conf import settings


class ScoringConfig(models.Model):
    """评分引擎参数（单例：始终只有 id=1 这一行）。教师/管理员可在前端修改。"""
    stage_completion_weight = models.DecimalField(max_digits=3, decimal_places=2, default=0.40, verbose_name='阶段完成度权重')
    sequence_adherence_weight = models.DecimalField(max_digits=3, decimal_places=2, default=0.25, verbose_name='流程遵循度权重')
    time_investment_weight = models.DecimalField(max_digits=3, decimal_places=2, default=0.15, verbose_name='时间投入权重')
    engagement_weight = models.DecimalField(max_digits=3, decimal_places=2, default=0.20, verbose_name='参与度权重')
    min_session_minutes = models.IntegerField(default=1, verbose_name='最小会话分钟')
    max_score = models.IntegerField(default=100, verbose_name='满分')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='+', verbose_name='最后修改人'
    )

    class Meta:
        db_table = 'scoring_config'
        verbose_name = '评分参数配置'
        verbose_name_plural = verbose_name

    def __str__(self):
        return f'ScoringConfig(min_min={self.min_session_minutes})'

    def save(self, *args, **kwargs):
        self.pk = 1
        super().save(*args, **kwargs)

    def to_engine_dict(self):
        """转换为 ScoringEngine 期望的 SCORING_CONFIG 字典格式。"""
        return {
            'STAGE_COMPLETION_WEIGHT': float(self.stage_completion_weight),
            'SEQUENCE_ADHERENCE_WEIGHT': float(self.sequence_adherence_weight),
            'TIME_INVESTMENT_WEIGHT': float(self.time_investment_weight),
            'ENGAGEMENT_WEIGHT': float(self.engagement_weight),
            'MIN_SESSION_MINUTES': self.min_session_minutes,
            'MAX_SCORE': self.max_score,
        }

    @classmethod
    def load(cls):
        """获取单例配置；若不存在则用 settings.SCORING_CONFIG 创建。"""
        from django.conf import settings as dj_settings
        obj = cls.objects.filter(pk=1).first()
        if obj is None:
            d = dj_settings.SCORING_CONFIG
            obj = cls.objects.create(
                pk=1,
                stage_completion_weight=d.get('STAGE_COMPLETION_WEIGHT', 0.40),
                sequence_adherence_weight=d.get('SEQUENCE_ADHERENCE_WEIGHT', 0.25),
                time_investment_weight=d.get('TIME_INVESTMENT_WEIGHT', 0.15),
                engagement_weight=d.get('ENGAGEMENT_WEIGHT', 0.20),
                min_session_minutes=d.get('MIN_SESSION_MINUTES', 5),
                max_score=d.get('MAX_SCORE', 100),
            )
        return obj


class StudentScore(models.Model):
    STATUS_CHOICES = [
        ('pending_review', '待复核'),
        ('reviewed', '已复核'),
        ('finalized', '已确认'),
    ]

    session = models.OneToOneField(
        'chat_logs.ConversationSession', on_delete=models.CASCADE,
        related_name='score', verbose_name='关联会话'
    )
    student = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name='scores', verbose_name='学生'
    )
    workflow = models.ForeignKey(
        'dify_integration.LearningWorkflow', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='scores', verbose_name='教学流程'
    )
    # 自动评分维度
    auto_stage_completion = models.DecimalField(max_digits=5, decimal_places=2, default=0, verbose_name='阶段完成度')
    auto_sequence_score = models.DecimalField(max_digits=5, decimal_places=2, default=0, verbose_name='流程遵循度')
    auto_time_score = models.DecimalField(max_digits=5, decimal_places=2, default=0, verbose_name='时间投入')
    auto_engagement_score = models.DecimalField(max_digits=5, decimal_places=2, default=0, verbose_name='参与度')
    auto_total_score = models.DecimalField(max_digits=5, decimal_places=2, default=0, verbose_name='自动总分')
    # 教师评分
    teacher_score = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True, verbose_name='教师评分')
    teacher_comment = models.TextField(blank=True, default='', verbose_name='教师评语')
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='reviewed_scores', verbose_name='复核教师'
    )
    reviewed_at = models.DateTimeField(null=True, blank=True, verbose_name='复核时间')
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default='pending_review',
        verbose_name='状态'
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')

    class Meta:
        db_table = 'student_scores'
        verbose_name = '学生评分'
        verbose_name_plural = verbose_name
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.student.display_name} - {self.auto_total_score}分'


class ScoreDetail(models.Model):
    score = models.ForeignKey(
        StudentScore, on_delete=models.CASCADE,
        related_name='details', verbose_name='评分记录'
    )
    stage = models.ForeignKey(
        'dify_integration.WorkflowStage', on_delete=models.CASCADE,
        verbose_name='流程阶段'
    )
    is_completed = models.BooleanField(default=False, verbose_name='是否完成')
    message_count = models.IntegerField(default=0, verbose_name='消息数')
    time_spent_seconds = models.IntegerField(default=0, verbose_name='耗时(秒)')
    stage_score = models.DecimalField(max_digits=5, decimal_places=2, default=0, verbose_name='阶段得分')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')

    class Meta:
        db_table = 'score_details'
        verbose_name = '评分明细'
        verbose_name_plural = verbose_name

    def __str__(self):
        return f'{self.stage.name}: {self.stage_score}分'
