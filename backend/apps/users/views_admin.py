"""管理员（admin 角色）端点：教师管理、Dify 配置。

权限要求：仅 role == 'admin' 的认证用户。
"""
from django.contrib.auth import get_user_model
from django.db import transaction
from django.http import JsonResponse
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated

from .models import SchoolClass

User = get_user_model()


def _is_admin(user):
    return user.is_authenticated and user.role == 'admin'


def _require_admin(request):
    if not _is_admin(request.user):
        return JsonResponse({'error': '权限不足，仅管理员可访问'}, status=403)
    return None


def _serialize_teacher(t):
    return {
        'id': t.id,
        'username': t.username,
        'email': t.email,
        'display_name': t.display_name,
        'is_active': t.is_active,
        'date_joined': t.date_joined.isoformat() if t.date_joined else None,
        'last_login': t.last_login.isoformat() if t.last_login else None,
        'managed_class_count': t.managed_classes.filter(is_active=True).count(),
    }


# --------- 教师 CRUD ---------

@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def admin_teachers_view(request):
    err = _require_admin(request)
    if err:
        return err

    if request.method == 'GET':
        qs = User.objects.filter(role='teacher').order_by('-date_joined')
        include_inactive = request.GET.get('include_inactive') == '1'
        if not include_inactive:
            qs = qs.filter(is_active=True)
        search = (request.GET.get('search') or '').strip()
        if search:
            qs = qs.filter(username__icontains=search) | qs.filter(display_name__icontains=search)
        data = [_serialize_teacher(t) for t in qs]
        return JsonResponse({'data': data, 'count': len(data)})

    # POST
    data = request.data
    username = (data.get('username') or '').strip()
    password = (data.get('password') or '').strip()
    display_name = (data.get('display_name') or '').strip()
    email = (data.get('email') or '').strip()

    if not username or not password or not display_name:
        return JsonResponse({'error': 'username / password / display_name 必填'}, status=400)
    if len(password) < 6:
        return JsonResponse({'error': '密码至少 6 位'}, status=400)
    if User.objects.filter(username=username).exists():
        return JsonResponse({'error': '用户名已存在'}, status=400)

    teacher = User(
        username=username,
        email=email,
        display_name=display_name,
        role='teacher',
        must_change_password=True,
    )
    teacher.set_password(password)
    teacher.save()
    return JsonResponse(_serialize_teacher(teacher), status=201)


@api_view(['PUT', 'DELETE'])
@permission_classes([IsAuthenticated])
def admin_teacher_detail_view(request, teacher_id):
    err = _require_admin(request)
    if err:
        return err

    teacher = User.objects.filter(id=teacher_id, role='teacher').first()
    if not teacher:
        return JsonResponse({'error': '教师不存在'}, status=404)

    if request.method == 'DELETE':
        if not teacher.is_active:
            return JsonResponse({'error': '该教师已停用'}, status=400)
        teacher.is_active = False
        teacher.save(update_fields=['is_active'])
        return JsonResponse({'success': True})

    # PUT
    data = request.data
    if 'display_name' in data:
        teacher.display_name = (data['display_name'] or '').strip()
    if 'email' in data:
        teacher.email = (data['email'] or '').strip()
    if 'is_active' in data:
        teacher.is_active = bool(data['is_active'])
    teacher.save()
    return JsonResponse(_serialize_teacher(teacher))


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def admin_teacher_reset_password_view(request, teacher_id):
    err = _require_admin(request)
    if err:
        return err

    teacher = User.objects.filter(id=teacher_id, role='teacher').first()
    if not teacher:
        return JsonResponse({'error': '教师不存在'}, status=404)

    new_password = (request.data.get('new_password') or '').strip()
    if not new_password or len(new_password) < 6:
        return JsonResponse({'error': '新密码至少 6 位'}, status=400)
    teacher.set_password(new_password)
    teacher.must_change_password = True
    teacher.save(update_fields=['password', 'must_change_password'])
    return JsonResponse({'success': True})
