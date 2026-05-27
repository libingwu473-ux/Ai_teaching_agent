from rest_framework import serializers
from django.contrib.auth import get_user_model

User = get_user_model()


class LoginSerializer(serializers.Serializer):
    username = serializers.CharField()
    password = serializers.CharField(write_only=True)


class UserProfileSerializer(serializers.ModelSerializer):
    dify_user_id = serializers.SerializerMethodField()
    school_class_name = serializers.SerializerMethodField()
    major_name = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = (
            'id', 'username', 'email', 'display_name', 'role', 'gender',
            'date_joined', 'last_login', 'dify_user_id',
            'school_class', 'school_class_name', 'major_name',
            'must_change_password',
        )
        read_only_fields = fields

    def get_dify_user_id(self, obj):
        mapping = getattr(obj, 'dify_mapping', None)
        return mapping.dify_user_id if mapping else None

    def get_school_class_name(self, obj):
        return obj.school_class.name if obj.school_class_id else None

    def get_major_name(self, obj):
        return obj.school_class.major.name if obj.school_class_id else None
