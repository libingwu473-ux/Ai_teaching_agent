from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from django.contrib.auth import get_user_model
from rest_framework_simplejwt.tokens import RefreshToken

from .serializers import RegisterSerializer, LoginSerializer, UserProfileSerializer

User = get_user_model()


@api_view(['POST'])
@permission_classes([AllowAny])
def register_view(request):
    serializer = RegisterSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    user = serializer.save()

    from apps.dify_integration.models import DifyUserMapping
    mapping = DifyUserMapping.objects.filter(user=user).first()

    refresh = RefreshToken.for_user(user)
    return Response({
        'id': user.id,
        'username': user.username,
        'email': user.email,
        'display_name': user.display_name,
        'role': user.role,
        'dify_user_id': mapping.dify_user_id if mapping else None,
        'access_token': str(refresh.access_token),
        'refresh_token': str(refresh),
    }, status=status.HTTP_201_CREATED)


@api_view(['POST'])
@permission_classes([AllowAny])
def login_view(request):
    serializer = LoginSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    from django.contrib.auth import authenticate
    user = authenticate(
        username=serializer.validated_data['username'],
        password=serializer.validated_data['password']
    )
    if not user:
        return Response({'error': '用户名或密码错误'}, status=status.HTTP_401_UNAUTHORIZED)

    refresh = RefreshToken.for_user(user)
    from apps.dify_integration.models import DifyUserMapping
    mapping = DifyUserMapping.objects.filter(user=user).first()

    return Response({
        'id': user.id,
        'username': user.username,
        'email': user.email,
        'display_name': user.display_name,
        'role': user.role,
        'dify_user_id': mapping.dify_user_id if mapping else None,
        'access_token': str(refresh.access_token),
        'refresh_token': str(refresh),
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def profile_view(request):
    serializer = UserProfileSerializer(request.user)
    return Response(serializer.data)
