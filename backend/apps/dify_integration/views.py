import json
import logging
from django.http import StreamingHttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework import status
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework.exceptions import AuthenticationFailed

from .services.chat_service import DifyChatService
from .services.dify_client import DifyClient
from .sync_service import DifySyncService
from apps.chat_logs.models import ConversationSession
from apps.chat_logs.serializers import ConversationSessionSerializer, ChatLogSerializer

logger = logging.getLogger('dify')


@csrf_exempt
def chat_send_view(request):
    """发送消息 — 流式SSE响应（绕过DRF内容协商，避免Accept: text/event-stream导致406）"""
    # 手动JWT认证
    jwt_auth = JWTAuthentication()
    try:
        result = jwt_auth.authenticate(request)
        if result is None:
            return JsonResponse({'error': '认证失败'}, status=401)
        request.user, _ = result
    except AuthenticationFailed as e:
        return JsonResponse({'error': str(e)}, status=401)

    try:
        body = json.loads(request.body.decode('utf-8'))
    except (json.JSONDecodeError, UnicodeDecodeError):
        return JsonResponse({'error': '请求格式错误'}, status=400)

    query = body.get('query', '').strip()
    if not query:
        return JsonResponse({'error': '消息内容不能为空'}, status=400)

    conversation_id = body.get('conversation_id', '') or ''
    files = body.get('files', None)
    workflow_id = body.get('workflow_id', None)

    service = DifyChatService()

    def event_stream():
        for event in service.stream_chat_message(
            user=request.user,
            query=query,
            conversation_id=conversation_id,
            files=files,
            workflow_id=workflow_id,
        ):
            yield event

    response = StreamingHttpResponse(
        event_stream(),
        content_type='text/event-stream',
    )
    response['Cache-Control'] = 'no-cache'
    response['X-Accel-Buffering'] = 'no'
    return response


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def chat_stop_view(request):
    """停止流式响应"""
    task_id = request.data.get('task_id', '')
    if not task_id:
        return JsonResponse({'error': '缺少task_id'}, status=400)

    mapping = getattr(request.user, 'dify_mapping', None)
    if not mapping:
        return JsonResponse({'error': '用户未绑定Dify'}, status=400)

    client = DifyClient()
    ok = client.stop_response(task_id, mapping.dify_user_id)
    return JsonResponse({'success': ok})


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def conversation_list_view(request):
    """获取当前用户的会话列表"""
    sessions = ConversationSession.objects.filter(
        user=request.user
    ).order_by('-updated_at')

    serializer = ConversationSessionSerializer(sessions, many=True)
    return JsonResponse({'data': serializer.data, 'count': sessions.count()})


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def conversation_detail_view(request, conv_id):
    """获取单个会话详情"""
    try:
        session = ConversationSession.objects.get(
            id=conv_id, user=request.user
        )
    except ConversationSession.DoesNotExist:
        return JsonResponse({'error': '会话不存在'}, status=404)

    serializer = ConversationSessionSerializer(session)
    return JsonResponse(serializer.data)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def conversation_messages_view(request, conv_id):
    """获取会话的消息列表"""
    try:
        session = ConversationSession.objects.get(
            id=conv_id, user=request.user
        )
    except ConversationSession.DoesNotExist:
        return JsonResponse({'error': '会话不存在'}, status=404)

    logs = session.logs.all()
    serializer = ChatLogSerializer(logs, many=True)
    return JsonResponse({'data': serializer.data, 'count': logs.count()})


@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def conversation_delete_view(request, conv_id):
    """删除会话（同时删除Dify端的会话）"""
    try:
        session = ConversationSession.objects.get(
            id=conv_id, user=request.user
        )
    except ConversationSession.DoesNotExist:
        return JsonResponse({'error': '会话不存在'}, status=404)

    # 删除Dify端会话
    mapping = getattr(request.user, 'dify_mapping', None)
    if mapping:
        client = DifyClient()
        client.delete_conversation(mapping.dify_user_id, session.dify_conversation_id)

    session.delete()
    return JsonResponse({'success': True})


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def file_upload_view(request):
    """上传文件到Dify"""
    uploaded_file = request.FILES.get('file')
    if not uploaded_file:
        return JsonResponse({'error': '请选择文件'}, status=400)

    mapping = getattr(request.user, 'dify_mapping', None)
    if not mapping:
        return JsonResponse({'error': '用户未绑定Dify'}, status=400)

    client = DifyClient()
    result = client.upload_file(mapping.dify_user_id, uploaded_file)
    return JsonResponse(result)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def sync_trigger_view(request):
    """手动触发同步"""
    # 仅教师和管理员可触发
    if request.user.role not in ['teacher', 'admin']:
        return JsonResponse({'error': '权限不足'}, status=403)

    service = DifySyncService()
    stats = service.sync_all_active_users()
    return JsonResponse({'success': True, 'stats': stats})
