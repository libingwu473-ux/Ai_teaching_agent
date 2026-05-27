from django.contrib.auth.models import AbstractUser
from django.db import models


class Major(models.Model):
    code = models.CharField(max_length=50, unique=True, verbose_name='专业代码')
    name = models.CharField(max_length=100, verbose_name='专业名称')
    description = models.TextField(blank=True, default='', verbose_name='描述')
    is_active = models.BooleanField(default=True, verbose_name='启用')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'majors'
        verbose_name = '专业'
        verbose_name_plural = verbose_name
        ordering = ['code']

    def __str__(self):
        return f'{self.code} {self.name}'


class SchoolClass(models.Model):
    major = models.ForeignKey(
        Major, on_delete=models.PROTECT,
        related_name='classes', verbose_name='所属专业'
    )
    name = models.CharField(max_length=100, verbose_name='班级名称')
    teacher = models.ForeignKey(
        'User', on_delete=models.PROTECT,
        related_name='managed_classes',
        limit_choices_to={'role': 'teacher'},
        verbose_name='管理教师',
    )
    is_active = models.BooleanField(default=True, verbose_name='启用')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'school_classes'
        verbose_name = '班级'
        verbose_name_plural = verbose_name
        unique_together = [('major', 'name')]
        ordering = ['major__code', 'name']

    def __str__(self):
        return f'{self.major.name}-{self.name}'


class User(AbstractUser):
    ROLE_CHOICES = [
        ('student', '学生'),
        ('teacher', '教师'),
        ('admin', '管理员'),
    ]
    GENDER_CHOICES = [
        ('male', '男'),
        ('female', '女'),
        ('other', '其他'),
    ]

    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='student')
    display_name = models.CharField(max_length=100, blank=True, verbose_name='显示名称')
    gender = models.CharField(
        max_length=10, blank=True, default='',
        choices=GENDER_CHOICES, verbose_name='性别'
    )
    school_class = models.ForeignKey(
        SchoolClass, on_delete=models.PROTECT,
        null=True, blank=True, related_name='students',
        verbose_name='所属班级'
    )
    must_change_password = models.BooleanField(
        default=False, verbose_name='首次登录必须改密'
    )

    class Meta:
        db_table = 'users'
        verbose_name = '用户'
        verbose_name_plural = verbose_name

    def __str__(self):
        return f'{self.display_name or self.username} ({self.get_role_display()})'
