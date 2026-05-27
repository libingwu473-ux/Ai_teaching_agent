"""/api/teacher/ 教师端 班级 / 学生 / CSV 路由。

与 apps/scoring/urls.py 同挂在 /api/teacher/ 前缀下。
为避免与 scoring 中已有的 `students/<int:student_id>/...` 冲突，
本模块使用 `class-students/` 子路径。
"""
from django.urls import path

from . import views_teacher

urlpatterns = [
    path('majors-readonly/', views_teacher.teacher_majors_view, name='teacher-majors-readonly'),
    path('classes/', views_teacher.teacher_classes_view, name='teacher-classes'),
    path('classes/<int:class_id>/', views_teacher.teacher_class_detail_view, name='teacher-class-detail'),
    path('classes/<int:class_id>/class-students/', views_teacher.teacher_class_students_view, name='teacher-class-students'),
    path('classes/<int:class_id>/class-students/import/', views_teacher.teacher_class_students_import_view, name='teacher-class-students-import'),
    path('class-students/<int:student_id>/', views_teacher.teacher_student_detail_view, name='teacher-class-student-detail'),
    path('class-students/<int:student_id>/reset-password/', views_teacher.teacher_student_reset_password_view, name='teacher-class-student-reset-password'),
    path('students-csv-template/', views_teacher.teacher_csv_template_view, name='teacher-csv-template'),
]
