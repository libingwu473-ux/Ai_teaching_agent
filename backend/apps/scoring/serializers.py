from rest_framework import serializers
from .models import StudentScore, ScoreDetail


class ScoreDetailSerializer(serializers.ModelSerializer):
    stage_name = serializers.CharField(source='stage.name', read_only=True)
    stage_key = serializers.CharField(source='stage.stage_key', read_only=True)
    order_index = serializers.IntegerField(source='stage.order_index', read_only=True)

    class Meta:
        model = ScoreDetail
        fields = ['id', 'stage_id', 'stage_name', 'stage_key', 'order_index',
                  'is_completed', 'message_count', 'time_spent_seconds',
                  'stage_score', 'created_at']


class StudentScoreSerializer(serializers.ModelSerializer):
    student_name = serializers.SerializerMethodField()
    details = ScoreDetailSerializer(many=True, read_only=True)
    session_title = serializers.SerializerMethodField()

    class Meta:
        model = StudentScore
        fields = ['id', 'session_id', 'student_id', 'student_name', 'session_title',
                  'workflow_id', 'auto_stage_completion', 'auto_sequence_score',
                  'auto_time_score', 'auto_engagement_score', 'auto_total_score',
                  'teacher_score', 'teacher_comment', 'status',
                  'reviewed_at', 'created_at', 'details']

    def get_student_name(self, obj):
        return obj.student.display_name or obj.student.username

    def get_session_title(self, obj):
        return obj.session.title or f'会话#{obj.session.id}'


class TeacherScoreUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = StudentScore
        fields = ['teacher_score', 'teacher_comment', 'status']
