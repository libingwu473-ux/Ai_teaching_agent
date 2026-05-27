from django.urls import path
from . import views

urlpatterns = [
    path('students/', views.teacher_student_list_view, name='teacher-students'),
    path('students/<int:student_id>/sessions/', views.teacher_student_sessions_view, name='teacher-student-sessions'),
    path('students/<int:student_id>/scores/', views.teacher_student_scores_view, name='teacher-student-scores'),
    path('scores/<int:score_id>/', views.teacher_score_detail_view, name='teacher-score-detail'),
    path('stats/', views.teacher_stats_view, name='teacher-stats'),
    path('scoring/trigger/', views.trigger_scoring_view, name='teacher-scoring-trigger'),
    path('scoring/recalculate-all/', views.recalculate_all_scores_view, name='teacher-scoring-recalc-all'),
    path('scoring-config/', views.scoring_config_view, name='teacher-scoring-config'),
    path('workflow-stages/', views.workflow_stages_view, name='teacher-workflow-stages'),
]
