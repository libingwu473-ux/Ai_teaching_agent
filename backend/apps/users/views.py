from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from django.contrib.auth import get_user_model, authenticate
from rest_framework_simplejwt.tokens import RefreshToken

from .serializers import LoginSerializer, UserProfileSerializer

User = get_user_model()


@api_view(['POST'])
@permission_classes([AllowAny])
def login_view(request):
    serializer = LoginSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    user = authenticate(
        username=serializer.validated_data['username'],
        password=serializer.validated_data['password']
    )
    if not user:
        return Response({'error': '用户名或密码错误'}, status=status.HTTP_401_UNAUTHORIZED)
    if not user.is_active:
        return Response({'error': '账号已被禁用'}, status=status.HTTP_403_FORBIDDEN)

    refresh = RefreshToken.for_user(user)
    from apps.dify_integration.models import DifyUserMapping
    mapping = DifyUserMapping.objects.filter(user=user).first()

    return Response({
        'id': user.id,
        'username': user.username,
        'email': user.email,
        'display_name': user.display_name,
        'role': user.role,
        'must_change_password': user.must_change_password,
        'dify_user_id': mapping.dify_user_id if mapping else None,
        'access_token': str(refresh.access_token),
        'refresh_token': str(refresh),
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def profile_view(request):
    serializer = UserProfileSerializer(request.user)
    return Response(serializer.data)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def change_password_view(request):
    """用户修改自己的密码。"""
    old_password = request.data.get('old_password') or ''
    new_password = request.data.get('new_password') or ''
    if not new_password or len(new_password) < 6:
        return Response({'error': '新密码至少 6 位'}, status=400)
    if not request.user.check_password(old_password):
        return Response({'error': '原密码错误'}, status=400)
    request.user.set_password(new_password)
    request.user.must_change_password = False
    request.user.save(update_fields=['password', 'must_change_password'])
    return Response({'success': True})
