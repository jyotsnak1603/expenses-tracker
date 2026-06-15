"""Account views for registration and profile."""
from django.contrib.auth.models import User
from rest_framework import generics, permissions, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from .serializers import RegisterSerializer, UserSerializer


class RegisterView(generics.CreateAPIView):
    queryset = User.objects.all()
    permission_classes = (permissions.AllowAny,)
    serializer_class = RegisterSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        return Response({
            'user': UserSerializer(user).data,
            'message': 'Registration successful.'
        }, status=status.HTTP_201_CREATED)


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def me(request):
    """Get current authenticated user's profile."""
    return Response(UserSerializer(request.user).data)


@api_view(['PUT'])
@permission_classes([permissions.IsAuthenticated])
def update_profile(request):
    """Update current user's profile."""
    serializer = UserSerializer(request.user, data=request.data, partial=True)
    serializer.is_valid(raise_exception=True)
    serializer.save()
    return Response(serializer.data)


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def search_users(request):
    """Search users by username or email for adding to groups."""
    query = request.query_params.get('q', '').strip()
    if len(query) < 2:
        return Response([])
    users = User.objects.filter(
        username__icontains=query
    ).exclude(id=request.user.id)[:10]
    return Response(UserSerializer(users, many=True).data)
