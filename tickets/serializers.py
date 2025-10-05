from rest_framework import serializers
from django.utils import timezone
from .models import Ticket, Comment, TimelineLog

# -----------------------------
# Timeline Serializer
# -----------------------------
class TimelineSerializer(serializers.ModelSerializer):
    class Meta:
        model = TimelineLog
        fields = ['id', 'action_type', 'metadata', 'created_at']
        read_only_fields = ['ticket', 'created_at']


# -----------------------------
# Comment Serializer
# -----------------------------
class CommentSerializer(serializers.ModelSerializer):
    user = serializers.StringRelatedField(read_only=True)
    replies = serializers.SerializerMethodField()

    class Meta:
        model = Comment
        fields = ['id', 'ticket', 'user', 'text', 'parent', 'replies', 'created_at']
        read_only_fields = ['user', 'ticket', 'created_at', 'replies']

    def get_replies(self, obj):
        """Return nested replies recursively."""
        replies = obj.replies.all().order_by('created_at')
        return CommentSerializer(replies, many=True).data


# -----------------------------
# Ticket Serializer
# -----------------------------
class TicketSerializer(serializers.ModelSerializer):
    created_by = serializers.StringRelatedField(read_only=True)
    assignee = serializers.StringRelatedField(read_only=True)
    comments = serializers.SerializerMethodField()
    timeline_logs = serializers.SerializerMethodField()
    sla_remaining = serializers.SerializerMethodField()

    class Meta:
        model = Ticket
        fields = [
            'id', 'title', 'description', 'priority', 'status', 'created_by',
            'assignee', 'sla_deadline', 'sla_remaining', 'version', 'created_at',
            'updated_at', 'comments', 'timeline_logs'
        ]
        read_only_fields = ['created_by', 'sla_deadline', 'version', 'created_at', 'updated_at']

    def get_comments(self, obj):
        top_level_comments = obj.comments.filter(parent__isnull=True).order_by('created_at')
        return CommentSerializer(top_level_comments, many=True).data

    def get_timeline_logs(self, obj):
        logs = obj.timeline_logs.all().order_by('-created_at')
        return TimelineSerializer(logs, many=True).data

    def get_sla_remaining(self, obj):
        """Return SLA remaining as human-readable string."""
        if obj.sla_deadline:
            remaining = obj.sla_deadline - timezone.now()
            total_seconds = int(remaining.total_seconds())
            if total_seconds < 0:
                return "Breached"
            hours, remainder = divmod(total_seconds, 3600)
            minutes, _ = divmod(remainder, 60)
            return f"{hours}h {minutes}m"
        return None
