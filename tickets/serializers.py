from rest_framework import serializers
from .models import Ticket, Comment, TimelineLog

class TicketSerializer(serializers.ModelSerializer):
    class Meta:
        model = Ticket
        fields = '__all__'
        read_only_fields = ['created_by', 'sla_deadline', 'created_at', 'updated_at']

class CommentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Comment
        fields = '__all__'
        read_only_fields = ['user', 'ticket', 'created_at']
        
class TimelineSerializer(serializers.ModelSerializer):
    class Meta:
        model = TimelineLog
        fields = '__all__'
