"""Group views for CRUD and member management."""
from django.contrib.auth.models import User
from django.shortcuts import get_object_or_404
from rest_framework import generics, permissions, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from .models import Group, GroupMembership
from .serializers import (
    GroupSerializer, GroupCreateSerializer,
    AddMemberSerializer, UpdateMemberSerializer,
    GroupMembershipSerializer
)


class GroupListCreateView(generics.ListCreateAPIView):
    """List groups the user is a member of, or create a new group."""

    def get_serializer_class(self):
        if self.request.method == 'POST':
            return GroupCreateSerializer
        return GroupSerializer

    def get_queryset(self):
        return Group.objects.filter(
            memberships__user=self.request.user
        ).distinct().prefetch_related('memberships__user')

    def perform_create(self, serializer):
        from django.utils import timezone
        group = serializer.save(created_by=self.request.user)
        # Auto-add creator as member
        GroupMembership.objects.create(
            group=group,
            user=self.request.user,
            joined_at=timezone.now().date(),
            is_active=True
        )

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        # Return full group data
        group = Group.objects.prefetch_related('memberships__user').get(id=serializer.instance.id)
        return Response(GroupSerializer(group).data, status=status.HTTP_201_CREATED)


class GroupDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = GroupSerializer

    def get_queryset(self):
        return Group.objects.filter(
            memberships__user=self.request.user
        ).distinct().prefetch_related('memberships__user')


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def add_member(request, group_id):
    """Add a member to a group."""
    group = get_object_or_404(Group, id=group_id, memberships__user=request.user)
    serializer = AddMemberSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)

    user = User.objects.get(id=serializer.validated_data['user_id'])
    joined_at = serializer.validated_data['joined_at']

    # Check if already an active member
    existing = GroupMembership.objects.filter(
        group=group, user=user, is_active=True, left_at__isnull=True
    ).first()
    if existing:
        return Response(
            {'error': 'User is already an active member of this group.'},
            status=status.HTTP_400_BAD_REQUEST
        )

    membership = GroupMembership.objects.create(
        group=group, user=user, joined_at=joined_at, is_active=True
    )
    return Response(
        GroupMembershipSerializer(membership).data,
        status=status.HTTP_201_CREATED
    )


@api_view(['PATCH'])
@permission_classes([permissions.IsAuthenticated])
def update_member(request, group_id, user_id):
    """Update a member's status (e.g., mark as left)."""
    group = get_object_or_404(Group, id=group_id, memberships__user=request.user)
    membership = get_object_or_404(
        GroupMembership, group=group, user_id=user_id, is_active=True
    )

    serializer = UpdateMemberSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)

    if 'left_at' in serializer.validated_data:
        membership.left_at = serializer.validated_data['left_at']
        membership.is_active = False
    if 'is_active' in serializer.validated_data:
        membership.is_active = serializer.validated_data['is_active']

    membership.save()
    return Response(GroupMembershipSerializer(membership).data)


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def group_members(request, group_id):
    """List all members (active and past) of a group."""
    group = get_object_or_404(Group, id=group_id, memberships__user=request.user)
    memberships = group.memberships.select_related('user').all()
    return Response(GroupMembershipSerializer(memberships, many=True).data)
