from django.db.models.signals import post_save
from django.dispatch import receiver
from django.conf import settings
import uuid


@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def create_dify_user_mapping(sender, instance, created, **kwargs):
    if created:
        from apps.dify_integration.models import DifyUserMapping
        dify_user_id = f'dify_edu_{uuid.uuid4().hex[:12]}'
        DifyUserMapping.objects.create(user=instance, dify_user_id=dify_user_id)
