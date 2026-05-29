import json
from django.http import JsonResponse
from django.db.models import Avg, Count, Q
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from django.contrib.auth import get_user_model

from .models import StudentScore, ScoreDetail, ScoringConfig
from .scoring_engine import ScoringEngine, score_session
from .serializers import StudentScoreSerializer, TeacherScoreUpdateSerializer
from apps.chat_logs.models import ConversationSession

User = get_user_model()


def _is_teacher(user):
    return user.role in ['teacher', 'admin']


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def teacher_student_list_view(request):
    """教师查看学生列表

    支持过滤：
      - search: 按 学号/姓名/邮箱 模糊匹配
      - class_id: 限定到具体班级
      - major_id: 限定到某专业下的所有班级
    teacher 角色仅能看到自己 managed_classes 名下的学生；admin 看全局。
    """
    if not _is_teacher(request.user):
        return JsonResponse({'error': '权限不足'}, status=403)

    students = User.objects.filter(role='student').select_related(
        'school_class', 'school_class__major',
    ).annotate(
        total_sessions=Count('sessions'),
        avg_score=Avg('scores__auto_total_score'),
    )

    # 仅教师本人 managed_classes 下的学生（admin 不限制）
    if request.user.role == 'teacher':
        students = students.filter(school_class__teacher=request.user)

    search = request.GET.get('search', '').strip()
    if search:
        students = students.filter(
            Q(username__icontains=search) |
            Q(display_name__icontains=search) |
            Q(email__icontains=search)
        )

    class_id = request.GET.get('class_id')
    if class_id:
        students = students.filter(school_class_id=class_id)

    major_id = request.GET.get('major_id')
    if major_id:
        students = students.filter(school_class__major_id=major_id)

    data = []
    for s in students:
        last_session = s.sessions.order_by('-updated_at').first()
        data.append({
            'id': s.id,
            'username': s.username,
            'email': s.email,
            'display_name': s.display_name,
            'class_id': s.school_class_id,
            'class_name': s.school_class.name if s.school_class_id else None,
            'major_id': s.school_class.major_id if s.school_class_id else None,
            'major_name': s.school_class.major.name if s.school_class_id else None,
            'total_sessions': s.total_sessions,
            'average_score': round(float(s.avg_score or 0), 1),
            'last_active': last_session.updated_at.isoformat() if last_session else None,
        })

    return JsonResponse({'data': data, 'count': len(data)})


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def teacher_student_sessions_view(request, student_id):
    """教师查看某个学生的所有会话"""
    if not _is_teacher(request.user):
        return JsonResponse({'error': '权限不足'}, status=403)

    sessions = ConversationSession.objects.filter(
        user_id=student_id
    ).order_by('-updated_at').prefetch_related('logs')

    data = []
    for session in sessions:
        logs = list(session.logs.all())
        data.append({
            'id': session.id,
            'title': session.title,
            'status': session.status,
            'current_stage': session.current_stage,
            'completed_stages': json.loads(session.completed_stages or '[]'),
            'total_messages': session.total_messages,
            'total_tokens': session.total_tokens,
            'started_at': session.started_at.isoformat() if session.started_at else None,
            'ended_at': session.ended_at.isoformat() if session.ended_at else None,
            'logs_count': len(logs),
        })

    return JsonResponse({'data': data, 'count': len(data)})


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def teacher_student_scores_view(request, student_id):
    """教师查看某个学生的评分列表"""
    if not _is_teacher(request.user):
        return JsonResponse({'error': '权限不足'}, status=403)

    scores = StudentScore.objects.filter(
        student_id=student_id
    ).order_by('-created_at').prefetch_related('details')

    serializer = StudentScoreSerializer(scores, many=True)
    return JsonResponse({'data': serializer.data, 'count': scores.count()})


@api_view(['GET', 'PUT'])
@permission_classes([IsAuthenticated])
def teacher_score_detail_view(request, score_id):
    """教师查看/修改评分详情"""
    if not _is_teacher(request.user):
        return JsonResponse({'error': '权限不足'}, status=403)

    try:
        score = StudentScore.objects.get(id=score_id)
    except StudentScore.DoesNotExist:
        return JsonResponse({'error': '评分记录不存在'}, status=404)

    if request.method == 'GET':
        serializer = StudentScoreSerializer(score)
        return JsonResponse(serializer.data)

    elif request.method == 'PUT':
        update_serializer = TeacherScoreUpdateSerializer(score, data=request.data, partial=True)
        if not update_serializer.is_valid():
            return JsonResponse(update_serializer.errors, status=400)

        updated = update_serializer.save()
        updated.reviewed_by = request.user
        from django.utils import timezone
        updated.reviewed_at = timezone.now()
        updated.save()

        return JsonResponse(StudentScoreSerializer(updated).data)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def teacher_stats_view(request):
    """教师仪表盘统计数据"""
    if not _is_teacher(request.user):
        return JsonResponse({'error': '权限不足'}, status=403)

    total_students = User.objects.filter(role='student').count()
    total_sessions = ConversationSession.objects.count()
    active_students = User.objects.filter(
        role='student',
        sessions__updated_at__isnull=False,
    ).distinct().count()

    avg_score = StudentScore.objects.aggregate(avg=Avg('auto_total_score'))['avg'] or 0

    # 各阶段完成率 —— 平均进度口径（per-session cap）：
    # rate = Σ_session min(该阶段 ChatLog 数, 门槛) / (门槛 × 总会话数)
    # 例：3 个会话该阶段各发 1 条、门槛 3 → 3 / (3*3) = 33.33%
    # 单个会话即便发了 5 条也只按 3 条计，避免被超额会话拉高。
    from apps.dify_integration.models import WorkflowStage
    from apps.chat_logs.models import ChatLog
    from django.db.models import Count

    stage_completion = {}            # 兼容旧调用方：{stage_key: rate}
    stage_completion_detail = []     # 含中文名、门槛、累计消息数等

    stages = WorkflowStage.objects.select_related('workflow').order_by('order_index')
    for stage in stages:
        threshold = max(int(stage.expected_min_messages), 1)
        if total_sessions == 0:
            rate = 0.0
            sum_capped = 0
            actual_total = 0
            completed = 0
        else:
            per_session_counts = list(
                ChatLog.objects.filter(stage_key=stage.stage_key)
                .values('session_id')
                .annotate(c=Count('id'))
            )
            actual_total = sum(row['c'] for row in per_session_counts)
            sum_capped = sum(min(row['c'], threshold) for row in per_session_counts)
            denominator = threshold * total_sessions
            rate = round(sum_capped / denominator, 4) if denominator else 0.0
            completed = sum(1 for row in per_session_counts if row['c'] >= threshold)
        stage_completion[stage.stage_key] = rate
        stage_completion_detail.append({
            'stage_key': stage.stage_key,
            'stage_name': stage.name,
            'order_index': stage.order_index,
            'expected_min_messages': threshold,
            'completed_sessions': completed,        # 仍然报告"达标会话数"作为参考
            'total_sessions': total_sessions,
            'messages_counted': sum_capped,         # 用于显示的"分子"
            'messages_needed': threshold * total_sessions,  # 用于显示的"分母"
            'messages_actual': actual_total,        # 实际消息总数（不 cap）
            'rate': rate,
        })

    # 每日活跃用户（近7天）
    from django.utils import timezone
    from datetime import timedelta
    daily_active = []
    for i in range(6, -1, -1):
        day = (timezone.now() - timedelta(days=i)).date()
        count = ConversationSession.objects.filter(
            updated_at__date=day,
        ).values('user').distinct().count()
        daily_active.append({'date': day.isoformat(), 'count': count})

    return JsonResponse({
        'total_students': total_students,
        'active_students': active_students,
        'total_sessions': total_sessions,
        'average_score': round(float(avg_score), 1),
        'stage_completion_rate': stage_completion,
        'stage_completion_detail': stage_completion_detail,
        'daily_active_users': daily_active,
    })


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def trigger_scoring_view(request):
    """触发指定会话的自动评分"""
    if not _is_teacher(request.user):
        return JsonResponse({'error': '权限不足'}, status=403)

    session_id = request.data.get('session_id')
    if not session_id:
        return JsonResponse({'error': '缺少session_id'}, status=400)

    try:
        session = ConversationSession.objects.get(id=session_id)
    except ConversationSession.DoesNotExist:
        return JsonResponse({'error': '会话不存在'}, status=404)

    result = score_session(session)
    if result is None:
        return JsonResponse({'error': '未找到教学流程定义'}, status=400)

    score, _ = result
    return JsonResponse(StudentScoreSerializer(score).data)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def recalculate_all_scores_view(request):
    """重算全部会话的自动评分（教师/管理员手动维护用）。"""
    if not _is_teacher(request.user):
        return JsonResponse({'error': '权限不足'}, status=403)

    processed = 0
    skipped = 0
    failed = 0
    for session in ConversationSession.objects.all():
        try:
            result = score_session(session)
            if result is None:
                skipped += 1
            else:
                processed += 1
        except Exception:
            failed += 1

    return JsonResponse({
        'success': True,
        'processed': processed,
        'skipped': skipped,
        'failed': failed,
    })


def _serialize_scoring_config(cfg):
    return {
        'stage_completion_weight': float(cfg.stage_completion_weight),
        'sequence_adherence_weight': float(cfg.sequence_adherence_weight),
        'time_investment_weight': float(cfg.time_investment_weight),
        'engagement_weight': float(cfg.engagement_weight),
        'min_session_minutes': cfg.min_session_minutes,
        'max_score': cfg.max_score,
        'updated_at': cfg.updated_at.isoformat() if cfg.updated_at else None,
        'updated_by': cfg.updated_by.username if cfg.updated_by_id else None,
    }


@api_view(['GET', 'PUT'])
@permission_classes([IsAuthenticated])
def scoring_config_view(request):
    """读/写评分参数。"""
    if not _is_teacher(request.user):
        return JsonResponse({'error': '权限不足'}, status=403)

    cfg = ScoringConfig.load()

    if request.method == 'GET':
        return JsonResponse(_serialize_scoring_config(cfg))

    data = request.data
    weight_fields = [
        'stage_completion_weight', 'sequence_adherence_weight',
        'time_investment_weight', 'engagement_weight',
    ]
    for f in weight_fields:
        if f in data:
            try:
                v = float(data[f])
                if v < 0 or v > 1:
                    return JsonResponse({'error': f'{f} 必须在 0..1 之间'}, status=400)
                setattr(cfg, f, v)
            except (TypeError, ValueError):
                return JsonResponse({'error': f'{f} 必须为数字'}, status=400)

    # 检查权重总和 ≈ 1.0（允许 ±0.05 容差，便于教师手填）
    total = sum(float(getattr(cfg, f)) for f in weight_fields)
    if not (0.95 <= total <= 1.05):
        return JsonResponse({
            'error': f'四项权重之和应当 ≈ 1.0，当前为 {total:.2f}'
        }, status=400)

    if 'min_session_minutes' in data:
        try:
            v = int(data['min_session_minutes'])
            if v < 0:
                return JsonResponse({'error': 'min_session_minutes 不能为负'}, status=400)
            cfg.min_session_minutes = v
        except (TypeError, ValueError):
            return JsonResponse({'error': 'min_session_minutes 必须为整数'}, status=400)

    if 'max_score' in data:
        try:
            v = int(data['max_score'])
            if v <= 0:
                return JsonResponse({'error': 'max_score 必须为正整数'}, status=400)
            cfg.max_score = v
        except (TypeError, ValueError):
            return JsonResponse({'error': 'max_score 必须为整数'}, status=400)

    cfg.updated_by = request.user
    cfg.save()
    return JsonResponse(_serialize_scoring_config(cfg))


@api_view(['GET', 'PUT'])
@permission_classes([IsAuthenticated])
def workflow_stages_view(request):
    """读/写默认（首个）教学流程下各阶段的 expected_min_messages 门槛。

    GET 返回当前 workflow 及其阶段列表；PUT 接受 {updates: [{id, expected_min_messages}, ...]}。
    其它字段（name/stage_key/order/weight/min_minutes）暂不开放编辑，避免误改影响 Dify workflow
    的契约（stage_key 必须和 Dify 输出的 current_stage 对应）。
    """
    if not _is_teacher(request.user):
        return JsonResponse({'error': '权限不足'}, status=403)

    from apps.dify_integration.models import LearningWorkflow

    workflow = LearningWorkflow.objects.first()
    if workflow is None:
        if request.method == 'GET':
            return JsonResponse({'workflow_id': None, 'workflow_name': None, 'stages': []})
        return JsonResponse({'error': '未找到教学流程，请先运行 seed_workflow'}, status=400)

    if request.method == 'GET':
        stages = workflow.stages.order_by('order_index')
        return JsonResponse({
            'workflow_id': workflow.id,
            'workflow_name': workflow.name,
            'stages': [
                {
                    'id': s.id,
                    'name': s.name,
                    'stage_key': s.stage_key,
                    'order_index': s.order_index,
                    'expected_min_messages': s.expected_min_messages,
                }
                for s in stages
            ],
        })

    updates = request.data.get('updates')
    if not isinstance(updates, list):
        return JsonResponse({'error': 'updates 必须是数组'}, status=400)

    valid_ids = set(workflow.stages.values_list('id', flat=True))
    for item in updates:
        if not isinstance(item, dict):
            return JsonResponse({'error': 'updates 元素必须是对象'}, status=400)
        sid = item.get('id')
        if sid not in valid_ids:
            return JsonResponse({'error': f'阶段 id={sid} 不属于当前流程'}, status=400)
        raw = item.get('expected_min_messages')
        try:
            v = int(raw)
        except (TypeError, ValueError):
            return JsonResponse({'error': f'阶段 id={sid} 的 expected_min_messages 必须是整数'}, status=400)
        if v < 0:
            return JsonResponse({'error': f'阶段 id={sid} 的 expected_min_messages 不能为负'}, status=400)
        workflow.stages.filter(id=sid).update(expected_min_messages=v)

    stages = workflow.stages.order_by('order_index')
    return JsonResponse({
        'workflow_id': workflow.id,
        'workflow_name': workflow.name,
        'stages': [
            {
                'id': s.id,
                'name': s.name,
                'stage_key': s.stage_key,
                'order_index': s.order_index,
                'expected_min_messages': s.expected_min_messages,
            }
            for s in stages
        ],
    })
