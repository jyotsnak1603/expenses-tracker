"""Import serializers."""
from rest_framework import serializers
from .models import ImportSession, ImportIssue


class ImportIssueSerializer(serializers.ModelSerializer):
    class Meta:
        model = ImportIssue
        fields = '__all__'
        read_only_fields = ('id', 'session', 'row_number', 'column', 'issue_type',
                            'severity', 'description', 'original_value',
                            'suggested_value', 'original_row_data', 'created_at')


class ImportSessionSerializer(serializers.ModelSerializer):
    issues = ImportIssueSerializer(many=True, read_only=True)
    issue_summary = serializers.SerializerMethodField()

    class Meta:
        model = ImportSession
        fields = ('id', 'group', 'uploaded_by', 'file_name', 'status',
                  'total_rows', 'valid_rows', 'error_count', 'warning_count',
                  'issues', 'issue_summary', 'raw_data', 'created_at')
        read_only_fields = ('id', 'uploaded_by', 'file_name', 'status',
                            'total_rows', 'valid_rows', 'error_count',
                            'warning_count', 'created_at')

    def get_issue_summary(self, obj):
        issues = obj.issues.all()
        return {
            'total': issues.count(),
            'errors': issues.filter(severity='error').count(),
            'warnings': issues.filter(severity='warning').count(),
            'auto_fixed': issues.filter(severity='auto_fixed').count(),
            'info': issues.filter(severity='info').count(),
            'pending': issues.filter(resolution='pending').count(),
            'resolved': issues.exclude(resolution='pending').count(),
        }
