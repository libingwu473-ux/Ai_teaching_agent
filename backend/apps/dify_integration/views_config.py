"""教师端 Dify 平台配置读写接口。"""
from django.http import JsonResponse
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated

from .models import DifyConfig


def _is_admin(user):
    return user.is_authenticated and user.role in ('teacher', 'admin')


def _mask_key(key):
    if not key:
        return ''
    if len(key) <= 10:
        return '*' * len(key)
    return f'{key[:6]}...{key[-4:]}'


def _serialize(cfg, reveal_key=False):
    return {
        'api_base_url': cfg.api_base_url,
        'api_key': cfg.api_key if reveal_key else _mask_key(cfg.api_key),
        'api_key_masked': _mask_key(cfg.api_key),
        'app_id': cfg.app_id,
        'chatflow_id': cfg.chatflow_id,
        'verify_ssl': cfg.verify_ssl,
        'timeout': cfg.timeout,
        'max_retries': cfg.max_retries,
        'updated_at': cfg.updated_at.isoformat() if cfg.updated_at else None,
        'updated_by': cfg.updated_by.username if cfg.updated_by_id else None,
    }


@api_view(['GET', 'PUT'])
@permission_classes([IsAuthenticated])
def dify_config_view(request):
    if not _is_admin(request.user):
        return JsonResponse({'error': '权限不足'}, status=403)

    cfg = DifyConfig.load()

    if request.method == 'GET':
        reveal = request.GET.get('reveal') == '1' and request.user.role == 'admin'
        return JsonResponse(_serialize(cfg, reveal_key=reveal))

    data = request.data
    if 'api_base_url' in data:
        cfg.api_base_url = (data['api_base_url'] or '').strip().rstrip('/')
    if 'api_key' in data:
        new_key = (data['api_key'] or '').strip()
        if new_key:
            cfg.api_key = new_key
    if 'app_id' in data:
        cfg.app_id = (data['app_id'] or '').strip()
    if 'chatflow_id' in data:
        cfg.chatflow_id = (data['chatflow_id'] or '').strip()
    if 'verify_ssl' in data:
        cfg.verify_ssl = bool(data['verify_ssl'])
    if 'timeout' in data:
        try:
            cfg.timeout = max(1, int(data['timeout']))
        except (TypeError, ValueError):
            return JsonResponse({'error': 'timeout 必须为整数'}, status=400)
    if 'max_retries' in data:
        try:
            cfg.max_retries = max(0, int(data['max_retries']))
        except (TypeError, ValueError):
            return JsonResponse({'error': 'max_retries 必须为整数'}, status=400)

    if not cfg.api_base_url or not cfg.api_key:
        return JsonResponse({'error': 'api_base_url 和 api_key 不能为空'}, status=400)

    cfg.updated_by = request.user
    cfg.save()
    return JsonResponse(_serialize(cfg))
