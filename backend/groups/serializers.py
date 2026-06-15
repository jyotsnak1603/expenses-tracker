"""Group serializers."""
from django.contrib.auth.models import User
from rest_framework import serializers
from accounts.serializers import UserMinimalSerializer
from .models import Group, GroupMembership


class GroupMembershipSerializer(serializers.ModelSerializer):
    user = UserMinimalSerializer(read_only=True)
    user_id = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.all(), source='user', write_only=True
    )

    class Meta:
        model = GroupMembership
        fields = ('id', 'user', 'user_id', 'joined_at', 'left_at', 'is_active')


class GroupSerializer(serializers.ModelSerializer):
    members = serializers.SerializerMethodField()
    created_by = UserMinimalSerializer(read_only=True)
    member_count = serializers.SerializerMethodField()

    class Meta:
        model = Group
        fields = ('id', 'name', 'description', 'default_currency',
                  'created_by', 'members', 'member_count', 'created_at', 'updated_at')
        read_only_fields = ('id', 'created_by', 'created_at', 'updated_at')

    def get_members(self, obj):
        memberships = obj.memberships.select_related('user').all()
        return GroupMembershipSerializer(memberships, many=True).data

    def get_member_count(self, obj):
        return obj.memberships.filter(is_active=True, left_at__isnull=True).count()


class GroupCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Group
        fields = ('id', 'name', 'description', 'default_currency')


class AddMemberSerializer(serializers.Serializer):
    user_id = serializers.IntegerField()
    joined_at = serializers.DateField()

    def validate_user_id(self, value):
        if not User.objects.filter(id=value).exists():
            raise serializers.ValidationError('User not found.')
        return value


class UpdateMemberSerializer(serializers.Serializer):
    left_at = serializers.DateField(required=False)
    is_active = serializers.BooleanField(required=False)
