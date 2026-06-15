"""Import session and issue models for CSV import pipeline."""
from django.db import models
from django.contrib.auth.models import User
from groups.models import Group


class ImportSession(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('analyzing', 'Analyzing'),
        ('reviewing', 'Reviewing'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
    ]

    group = models.ForeignKey(Group, on_delete=models.CASCADE, related_name='imports')
    uploaded_by = models.ForeignKey(User, on_delete=models.CASCADE)
    file_name = models.CharField(max_length=255)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    total_rows = models.IntegerField(default=0)
    valid_rows = models.IntegerField(default=0)
    error_count = models.IntegerField(default=0)
    warning_count = models.IntegerField(default=0)
    raw_data = models.JSONField(default=list, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'Import {self.file_name} - {self.status}'


class ImportIssue(models.Model):
    SEVERITY_CHOICES = [
        ('error', 'Error'),
        ('warning', 'Warning'),
        ('info', 'Info'),
        ('auto_fixed', 'Auto-fixed'),
    ]
    RESOLUTION_CHOICES = [
        ('pending', 'Pending'),
        ('accepted', 'Accepted'),
        ('rejected', 'Rejected'),
        ('modified', 'Modified'),
    ]

    session = models.ForeignKey(ImportSession, on_delete=models.CASCADE, related_name='issues')
    row_number = models.IntegerField()
    column = models.CharField(max_length=50, blank=True, default='')
    issue_type = models.CharField(max_length=50)
    severity = models.CharField(max_length=20, choices=SEVERITY_CHOICES)
    description = models.TextField()
    original_value = models.TextField(blank=True, default='')
    suggested_value = models.TextField(blank=True, default='')
    original_row_data = models.JSONField(default=dict, blank=True)
    resolution = models.CharField(max_length=20, choices=RESOLUTION_CHOICES, default='pending')
    user_value = models.TextField(blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['row_number', 'id']

    def __str__(self):
        return f'Row {self.row_number}: {self.issue_type} ({self.severity})'
