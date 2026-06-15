"""Group and membership models with time-based membership tracking."""
from django.db import models
from django.contrib.auth.models import User


class Group(models.Model):
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True, default='')
    default_currency = models.CharField(max_length=3, default='INR')
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='created_groups')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.name

    @property
    def active_members(self):
        return self.memberships.filter(is_active=True, left_at__isnull=True)


class GroupMembership(models.Model):
    """Tracks who is in a group and when they joined/left.
    Enables time-based queries: Sam shouldn't see March expenses,
    Meera shouldn't be charged after leaving."""
    group = models.ForeignKey(Group, on_delete=models.CASCADE, related_name='memberships')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='group_memberships')
    joined_at = models.DateField()
    left_at = models.DateField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('group', 'user', 'joined_at')
        ordering = ['joined_at']

    def __str__(self):
        status = 'active' if self.is_active else f'left {self.left_at}'
        return f'{self.user.username} in {self.group.name} ({status})'

    def was_member_on(self, date):
        """Check if user was an active member on a specific date."""
        if date < self.joined_at:
            return False
        if self.left_at and date > self.left_at:
            return False
        return True
