# tickets/views.py

from django.shortcuts import render
from rest_framework import viewsets, permissions, status
from rest_framework.response import Response
from rest_framework.decorators import action
from django.utils import timezone
from .models import Ticket, Comment, TimelineLog
from .serializers import TicketSerializer, CommentSerializer, TimelineSerializer

class TicketViewSet(viewsets.ModelViewSet):
    queryset = Ticket.objects.all().order_by('-created_at')
    serializer_class = TicketSerializer

    def get_permissions(self):
        return [permissions.IsAuthenticated()]

    def perform_create(self, serializer):
        ticket = serializer.save(created_by=self.request.user)
        TimelineLog.objects.create(ticket=ticket, action_type='created', metadata={'user': self.request.user.username})

    def perform_update(self, serializer):
        old_updated = serializer.instance.updated_at
        new_updated = self.request.data.get('updated_at')
        if new_updated and str(old_updated) != new_updated:
            return Response({"error": {"code": "STALE_UPDATE"}}, status=status.HTTP_409_CONFLICT)
        ticket = serializer.save()
        TimelineLog.objects.create(ticket=ticket, action_type='updated', metadata={'user': self.request.user.username})

    @action(detail=True, methods=['post'])
    def add_comment(self, request, pk=None):
        ticket = self.get_object()
        serializer = CommentSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(user=request.user, ticket=ticket)
            TimelineLog.objects.create(ticket=ticket, action_type='comment_added', metadata={'user': request.user.username})
            return Response(serializer.data)
        return Response(serializer.errors, status=400)

    # ✅ New GET endpoint to fetch comments
    @action(detail=True, methods=['get'])
    def comments(self, request, pk=None):
        ticket = self.get_object()
        comments = ticket.comments.all().order_by('created_at')
        serializer = CommentSerializer(comments, many=True)
        return Response(serializer.data)

    # Timeline endpoint
    @action(detail=True, methods=['get'])
    def timeline(self, request, pk=None):
        ticket = self.get_object()
        logs = ticket.timeline.all().order_by('created_at')  # updated related_name
        serializer = TimelineSerializer(logs, many=True)
        return Response(serializer.data)
