"""教师端：班级管理、学生管理（含 CSV 严格事务导入）。

权限：teacher 仅可操作自己 managed_classes 名下的班级与学生。
admin 角色按规划不直接管学生，但可只读穿透查看。
"""
import csv
import io

from django.contrib.auth import get_user_model
from django.db import transaction
from django.http import JsonResponse
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated

from .models import Major, SchoolClass

User = get_user_model()


VALID_GENDERS = {
    '男': 'male', '女': 'female',
    'male': 'male', 'female': 'female',
    '': '', 'other': 'other', '其他': 'other',
}


def _is_teacher(user):
    return user.is_authenticated and user.role == 'teacher'


def _is_admin(user):
    return user.is_authenticated and user.role == 'admin'


def _require_teacher(request):
    if not _is_teacher(request.user):
        return JsonResponse({'error': '权限不足，仅教师可访问'}, status=403)
    return None


def _get_owned_class(user, class_id):
    """获取教师自己拥有的班级；admin 可访问任意班级。"""
    qs = SchoolClass.objects.filter(id=class_id)
    if _is_teacher(user):
        qs = qs.filter(teacher=user)
    return qs.first()


def _serialize_class(c):
    return {
        'id': c.id,
        'name': c.name,
        'major_id': c.major_id,
        'major_code': c.major.code,
        'major_name': c.major.name,
        'teacher_id': c.teacher_id,
        'teacher_name': c.teacher.display_name or c.teacher.username,
        'is_active': c.is_active,
        'student_count': c.students.filter(is_active=True).count(),
        'created_at': c.created_at.isoformat() if c.created_at else None,
    }


def _serialize_student(s):
    return {
        'id': s.id,
        'username': s.username,
        'display_name': s.display_name,
        'gender': s.gender,
        'email': s.email,
        'is_active': s.is_active,
        'school_class_id': s.school_class_id,
        'class_name': s.school_class.name if s.school_class_id else None,
        'major_name': s.school_class.major.name if s.school_class_id else None,
        'date_joined': s.date_joined.isoformat() if s.date_joined else None,
        'must_change_password': s.must_change_password,
    }


# --------- 班级 CRUD ---------

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def teacher_majors_view(request):
    """教师只读列出启用中的专业（用于建班）。"""
    if not (_is_teacher(request.user) or _is_admin(request.user)):
        return JsonResponse({'error': '权限不足'}, status=403)
    data = [
        {'id': m.id, 'code': m.code, 'name': m.name}
        for m in Major.objects.filter(is_active=True).order_by('code')
    ]
    return JsonResponse({'data': data})


@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def teacher_classes_view(request):
    if not (_is_teacher(request.user) or _is_admin(request.user)):
        return JsonResponse({'error': '权限不足'}, status=403)

    if request.method == 'GET':
        qs = SchoolClass.objects.select_related('major', 'teacher')
        if _is_teacher(request.user):
            qs = qs.filter(teacher=request.user)
        if request.GET.get('include_inactive') != '1':
            qs = qs.filter(is_active=True)
        return JsonResponse({'data': [_serialize_class(c) for c in qs]})

    # POST：仅教师可创建；admin 不直接建班级（规划：admin 只管教师）
    err = _require_teacher(request)
    if err:
        return err

    data = request.data
    major_id = data.get('major_id')
    name = (data.get('name') or '').strip()
    if not major_id or not name:
        return JsonResponse({'error': 'major_id 和 name 必填'}, status=400)
    major = Major.objects.filter(id=major_id, is_active=True).first()
    if not major:
        return JsonResponse({'error': '专业不存在或已停用'}, status=400)
    if SchoolClass.objects.filter(major=major, name=name).exists():
        return JsonResponse({'error': '该专业下班级名已存在'}, status=400)

    c = SchoolClass.objects.create(major=major, name=name, teacher=request.user)
    return JsonResponse(_serialize_class(c), status=201)


@api_view(['PUT', 'DELETE'])
@permission_classes([IsAuthenticated])
def teacher_class_detail_view(request, class_id):
    err = _require_teacher(request)
    if err:
        return err

    c = SchoolClass.objects.filter(id=class_id, teacher=request.user).first()
    if not c:
        return JsonResponse({'error': '班级不存在或不属于你'}, status=404)

    if request.method == 'DELETE':
        if c.students.filter(is_active=True).exists():
            return JsonResponse({'error': '班级下仍有启用学生，无法停用'}, status=400)
        c.is_active = False
        c.save(update_fields=['is_active'])
        return JsonResponse({'success': True})

    data = request.data
    if 'name' in data:
        new_name = (data['name'] or '').strip()
        if new_name and new_name != c.name:
            if SchoolClass.objects.filter(major=c.major, name=new_name).exclude(id=c.id).exists():
                return JsonResponse({'error': '该专业下班级名已存在'}, status=400)
            c.name = new_name
    if 'is_active' in data:
        c.is_active = bool(data['is_active'])
    c.save()
    return JsonResponse(_serialize_class(c))


# --------- 学生 CRUD ---------

@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def teacher_class_students_view(request, class_id):
    """列出/单个创建学生。"""
    if not (_is_teacher(request.user) or _is_admin(request.user)):
        return JsonResponse({'error': '权限不足'}, status=403)

    c = _get_owned_class(request.user, class_id)
    if not c:
        return JsonResponse({'error': '班级不存在或不属于你'}, status=404)

    if request.method == 'GET':
        qs = c.students.all().order_by('username')
        if request.GET.get('include_inactive') != '1':
            qs = qs.filter(is_active=True)
        return JsonResponse({'data': [_serialize_student(s) for s in qs], 'class': _serialize_class(c)})

    # POST：仅教师可创建学生
    err = _require_teacher(request)
    if err:
        return err

    data = request.data
    username = (data.get('username') or '').strip()
    display_name = (data.get('display_name') or '').strip()
    password = (data.get('password') or '').strip() or username  # 留空默认=学号
    gender_raw = (data.get('gender') or '').strip()
    gender = VALID_GENDERS.get(gender_raw, None)

    if not username or not display_name:
        return JsonResponse({'error': '学号（username）和姓名（display_name）必填'}, status=400)
    if gender is None:
        return JsonResponse({'error': '性别仅支持 男/女/其他/空'}, status=400)
    if User.objects.filter(username=username).exists():
        return JsonResponse({'error': '学号已存在'}, status=400)
    if len(password) < 6:
        return JsonResponse({'error': '密码至少 6 位（默认密码=学号，请保证学号长度 ≥ 6）'}, status=400)

    student = User(
        username=username,
        display_name=display_name,
        role='student',
        gender=gender,
        school_class=c,
        must_change_password=True,
    )
    student.set_password(password)
    student.save()
    return JsonResponse(_serialize_student(student), status=201)


@api_view(['PUT', 'DELETE'])
@permission_classes([IsAuthenticated])
def teacher_student_detail_view(request, student_id):
    err = _require_teacher(request)
    if err:
        return err

    student = User.objects.filter(id=student_id, role='student').first()
    if not student:
        return JsonResponse({'error': '学生不存在'}, status=404)
    if not student.school_class_id or student.school_class.teacher_id != request.user.id:
        return JsonResponse({'error': '该学生不在你管理的班级中'}, status=403)

    if request.method == 'DELETE':
        if not student.is_active:
            return JsonResponse({'error': '该学生已停用'}, status=400)
        student.is_active = False
        student.save(update_fields=['is_active'])
        return JsonResponse({'success': True})

    data = request.data
    if 'display_name' in data:
        student.display_name = (data['display_name'] or '').strip()
    if 'gender' in data:
        g = VALID_GENDERS.get((data['gender'] or '').strip(), None)
        if g is None:
            return JsonResponse({'error': '性别仅支持 男/女/其他/空'}, status=400)
        student.gender = g
    if 'is_active' in data:
        student.is_active = bool(data['is_active'])
    if 'school_class_id' in data:
        target = SchoolClass.objects.filter(
            id=data['school_class_id'], teacher=request.user
        ).first()
        if not target:
            return JsonResponse({'error': '目标班级不存在或不属于你'}, status=400)
        student.school_class = target
    student.save()
    return JsonResponse(_serialize_student(student))


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def teacher_student_reset_password_view(request, student_id):
    err = _require_teacher(request)
    if err:
        return err

    student = User.objects.filter(id=student_id, role='student').first()
    if not student:
        return JsonResponse({'error': '学生不存在'}, status=404)
    if not student.school_class_id or student.school_class.teacher_id != request.user.id:
        return JsonResponse({'error': '该学生不在你管理的班级中'}, status=403)

    new_password = (request.data.get('new_password') or '').strip() or student.username
    if len(new_password) < 6:
        return JsonResponse({'error': '新密码至少 6 位'}, status=400)
    student.set_password(new_password)
    student.must_change_password = True
    student.save(update_fields=['password', 'must_change_password'])
    return JsonResponse({'success': True})


# --------- CSV 严格事务导入 ---------

REQUIRED_HEADERS = ['学号', '密码', '专业', '班别', '姓名', '性别']
REQUIRED_FILL = {'学号', '姓名'}  # 密码留空默认=学号


def _read_csv_file(file_obj):
    """读取上传文件为 UTF-8 文本；兼容带 BOM。"""
    raw = file_obj.read()
    if isinstance(raw, str):
        text = raw
    else:
        for enc in ('utf-8-sig', 'utf-8', 'gbk'):
            try:
                text = raw.decode(enc)
                break
            except UnicodeDecodeError:
                continue
        else:
            raise ValueError('文件编码无法识别，请使用 UTF-8 保存')
    return text


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def teacher_class_students_import_view(request, class_id):
    """CSV 严格事务导入：任意一行报错则整批回滚。"""
    err = _require_teacher(request)
    if err:
        return err

    c = SchoolClass.objects.filter(id=class_id, teacher=request.user).first()
    if not c:
        return JsonResponse({'error': '班级不存在或不属于你'}, status=404)

    upload = request.FILES.get('file')
    if not upload:
        return JsonResponse({'error': '未上传文件（字段名 file）'}, status=400)

    try:
        text = _read_csv_file(upload)
    except ValueError as e:
        return JsonResponse({'error': str(e)}, status=400)

    reader = csv.DictReader(io.StringIO(text))
    headers = reader.fieldnames or []
    missing = [h for h in REQUIRED_HEADERS if h not in headers]
    if missing:
        return JsonResponse({
            'error': f'CSV 表头缺失列：{",".join(missing)}',
            'expected_headers': REQUIRED_HEADERS,
        }, status=400)

    rows = list(reader)
    if not rows:
        return JsonResponse({'error': 'CSV 文件没有数据行'}, status=400)

    errors = []
    parsed = []
    seen_usernames = set()

    for idx, row in enumerate(rows, start=2):  # 行号从 2 开始（1 是表头）
        username = (row.get('学号') or '').strip()
        password = (row.get('密码') or '').strip()
        display_name = (row.get('姓名') or '').strip()
        gender_raw = (row.get('性别') or '').strip()
        major_field = (row.get('专业') or '').strip()
        class_field = (row.get('班别') or '').strip()

        row_errors = []
        if not username:
            row_errors.append('学号为空')
        if not display_name:
            row_errors.append('姓名为空')
        if username and username in seen_usernames:
            row_errors.append('文件内学号重复')
        if username and User.objects.filter(username=username).exists():
            row_errors.append('学号已存在于系统')

        # 性别校验
        gender = VALID_GENDERS.get(gender_raw, None)
        if gender is None:
            row_errors.append(f'性别 "{gender_raw}" 非法（仅支持 男/女/其他/空）')

        # 专业/班别一致性校验（仅在用户填了的时候做核对）
        if major_field and major_field not in (c.major.code, c.major.name):
            row_errors.append(f'专业 "{major_field}" 与目标班级专业 "{c.major.name}" 不一致')
        if class_field and class_field != c.name:
            row_errors.append(f'班别 "{class_field}" 与目标班级 "{c.name}" 不一致')

        # 密码留空默认=学号
        final_password = password or username
        if len(final_password) < 6:
            row_errors.append('密码（默认=学号）不足 6 位')

        if row_errors:
            errors.append({'row': idx, 'username': username, 'reasons': row_errors})
        else:
            seen_usernames.add(username)
            parsed.append({
                'username': username,
                'password': final_password,
                'display_name': display_name,
                'gender': gender,
            })

    if errors:
        return JsonResponse({
            'success': False,
            'total': len(rows),
            'failed': len(errors),
            'errors': errors,
            'message': '严格事务：存在错误行，未导入任何数据',
        }, status=400)

    # 全量校验通过，事务内批量创建
    with transaction.atomic():
        created = []
        for r in parsed:
            u = User(
                username=r['username'],
                display_name=r['display_name'],
                role='student',
                gender=r['gender'],
                school_class=c,
                must_change_password=True,
            )
            u.set_password(r['password'])
            u.save()
            created.append(u.id)

    return JsonResponse({
        'success': True,
        'total': len(rows),
        'imported': len(parsed),
        'created_ids': created,
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def teacher_csv_template_view(request):
    """下载 CSV 模板（仅表头 + 1 行示例）。"""
    err = _require_teacher(request)
    if err:
        return err
    from django.http import HttpResponse
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(REQUIRED_HEADERS)
    writer.writerow(['2024001', '', '计算机科学与技术', '计科2401班', '张三', '男'])
    resp = HttpResponse(buf.getvalue().encode('utf-8-sig'), content_type='text/csv')
    resp['Content-Disposition'] = 'attachment; filename="students_template.csv"'
    return resp
