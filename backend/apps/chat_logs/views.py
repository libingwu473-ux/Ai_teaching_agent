from django.http import JsonResponse
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated

from .models import ConversationSession
from .serializers import ConversationSessionSerializer, ChatLogSerializer


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def my_sessions_view(request):
    """获取当前用户的所有会话（支持状态筛选）"""
    status_filter = request.GET.get('status', '')
    sessions = ConversationSession.objects.filter(user=request.user)
    if status_filter:
        sessions = sessions.filter(status=status_filter)
    sessions = sessions.order_by('-updated_at')

    serializer = ConversationSessionSerializer(sessions, many=True)
    return JsonResponse({'data': serializer.data, 'count': sessions.count()})


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def session_logs_view(request, session_id):
    """获取指定会话的对话日志"""
    try:
        session = ConversationSession.objects.get(id=session_id)
    except ConversationSession.DoesNotExist:
        return JsonResponse({'error': '会话不存在'}, status=404)

    # 学生只能看自己的日志
    if request.user.role == 'student' and session.user_id != request.user.id:
        return JsonResponse({'error': '权限不足'}, status=403)

    logs = session.logs.all()
    serializer = ChatLogSerializer(logs, many=True)
    return JsonResponse({
        'session': ConversationSessionSerializer(session).data,
        'logs': serializer.data,
        'count': logs.count(),
    })
