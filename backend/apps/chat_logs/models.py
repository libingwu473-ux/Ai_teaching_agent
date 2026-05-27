from django.db import models
from django.conf import settings


class ConversationSession(models.Model):
    STATUS_CHOICES = [
        ('active', '进行中'),
        ('completed', '已完成'),
        ('abandoned', '已放弃'),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name='sessions', verbose_name='用户'
    )
    workflow = models.ForeignKey(
        'dify_integration.LearningWorkflow', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='sessions', verbose_name='教学流程'
    )
    dify_conversation_id = models.CharField(
        max_length=100, unique=True, db_index=True,
        verbose_name='Dify会话ID'
    )
    title = models.CharField(max_length=500, blank=True, default='', verbose_name='会话标题')
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default='active',
        verbose_name='状态'
    )
    current_stage = models.CharField(max_length=100, blank=True, default='', verbose_name='当前阶段')
    completed_stages = models.TextField(default='[]', verbose_name='已完成阶段(JSON)')
    total_messages = models.IntegerField(default=0, verbose_name='总消息数')
    total_tokens = models.IntegerField(default=0, verbose_name='总Token数')
    started_at = models.DateTimeField(auto_now_add=True, verbose_name='开始时间')
    ended_at = models.DateTimeField(null=True, blank=True, verbose_name='结束时间')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')

    class Meta:
        db_table = 'conversation_sessions'
        verbose_name = '会话记录'
        verbose_name_plural = verbose_name
        ordering = ['-updated_at']

    def __str__(self):
        return f'{self.user.username} - {self.title or self.dify_conversation_id[:12]}'


class ChatLog(models.Model):
    session = models.ForeignKey(
        ConversationSession, on_delete=models.CASCADE,
        related_name='logs', verbose_name='所属会话'
    )
    dify_message_id = models.CharField(
        max_length=100, unique=True, verbose_name='Dify消息ID'
    )
    query_text = models.TextField(verbose_name='用户提问')
    answer_text = models.TextField(verbose_name='AI回答')
    stage_key = models.CharField(max_length=100, blank=True, default='', verbose_name='所处阶段')
    message_index = models.IntegerField(default=0, verbose_name='消息序号')
    token_count = models.IntegerField(default=0, verbose_name='Token消耗')
    response_time_ms = models.IntegerField(default=0, verbose_name='响应耗时(ms)')
    inputs_data = models.TextField(default='{}', verbose_name='输入变量(JSON)')
    files_data = models.TextField(default='[]', verbose_name='附件信息(JSON)')
    feedback = models.CharField(max_length=20, blank=True, default='', verbose_name='用户反馈')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')

    class Meta:
        db_table = 'chat_logs'
        verbose_name = '对话日志'
        verbose_name_plural = verbose_name
        ordering = ['created_at']
        indexes = [
            models.Index(fields=['session']),
            models.Index(fields=['stage_key']),
            models.Index(fields=['created_at']),
        ]

    def __str__(self):
        return f'[{self.stage_key or "?"}] {self.query_text[:50]}'
