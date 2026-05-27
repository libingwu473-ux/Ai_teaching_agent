import json
from rest_framework import serializers
from .models import ConversationSession, ChatLog


class ChatLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = ChatLog
        fields = ['id', 'session_id', 'dify_message_id', 'query_text', 'answer_text',
                  'stage_key', 'message_index', 'token_count', 'response_time_ms',
                  'feedback', 'created_at']


class ConversationSessionSerializer(serializers.ModelSerializer):
    logs_count = serializers.SerializerMethodField()
    student_name = serializers.SerializerMethodField()
    completed_stages_list = serializers.SerializerMethodField()

    class Meta:
        model = ConversationSession
        fields = ['id', 'user_id', 'workflow_id', 'dify_conversation_id', 'title',
                  'status', 'current_stage', 'completed_stages', 'completed_stages_list',
                  'total_messages', 'total_tokens', 'started_at', 'ended_at',
                  'created_at', 'updated_at', 'logs_count', 'student_name']

    def get_logs_count(self, obj):
        return obj.logs.count()

    def get_student_name(self, obj):
        return obj.user.display_name or obj.user.username

    def get_completed_stages_list(self, obj):
        try:
            return json.loads(obj.completed_stages or '[]')
        except json.JSONDecodeError:
            return []
