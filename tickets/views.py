from django.shortcuts import render
from rest_framework import viewsets, permissions, status, filters
from rest_framework.response import Response
from rest_framework.decorators import action, api_view
from rest_framework.permissions import BasePermission
from django.utils import timezone
from django.db.models import Q
from django.contrib.auth import get_user_model
from .models import Ticket, Comment, TimelineLog
from .serializers import TicketSerializer, CommentSerializer, TimelineSerializer

from .models import IdempotencyKey

def perform_create(self, serializer):
    # Check Idempotency-Key header
    key = self.request.headers.get('Idempotency-Key')
    if key:
        existing = IdempotencyKey.objects.filter(user=self.request.user, key=key).first()
        if existing:
            return Response(existing.response_data, status=existing.status_code)

    ticket = serializer.save(created_by=self.request.user)
    TimelineLog.objects.create(
        ticket=ticket,
        action_type='created',
        metadata={'user': self.request.user.username}
    )

    # Store response for idempotency
    if key:
        data = self.get_serializer(ticket).data
        IdempotencyKey.objects.create(
            user=self.request.user,
            key=key,
            response_data=data,
            status_code=201
        )
    return ticket

# -----------------------------
# Custom Permission
# -----------------------------
class IsOwnerOrAgentOrAdmin(BasePermission):
    """
    Custom permission:
    - Users: only their own tickets
    - Agents: assigned tickets or their created tickets
    - Admin: all tickets
    """
    def has_object_permission(self, request, view, obj):
        if request.user.role == 'admin':
            return True
        elif request.user.role == 'agent':
            return obj.assignee == request.user or obj.created_by == request.user
        else:  # 'user'
            return obj.created_by == request.user


# -----------------------------
# Ticket ViewSet
# -----------------------------
class TicketViewSet(viewsets.ModelViewSet):
    serializer_class = TicketSerializer
    permission_classes = [permissions.IsAuthenticated, IsOwnerOrAgentOrAdmin]
    filter_backends = [filters.OrderingFilter, filters.SearchFilter]
    search_fields = ['title', 'description', 'comments__text']
    ordering_fields = ['created_at', 'priority', 'status', 'sla_deadline']

    def get_queryset(self):
        """Return tickets according to role with optional search."""
        qs = Ticket.objects.all().order_by('-created_at')
        user = self.request.user

        if user.role == 'user':
            qs = qs.filter(created_by=user)
        elif user.role == 'agent':
            qs = qs.filter(Q(assignee=user) | Q(created_by=user))
        elif user.role == 'admin':
            qs = qs
        else:
            qs = Ticket.objects.none()

        search = self.request.query_params.get('search')
        if search:
            qs = qs.filter(
                Q(title__icontains=search) |
                Q(description__icontains=search) |
                Q(comments__text__icontains=search)
            ).distinct()

        return qs

    # -----------------------------
    # Create ticket
    # -----------------------------
    def perform_create(self, serializer):
        ticket = serializer.save(created_by=self.request.user)
        TimelineLog.objects.create(
            ticket=ticket,
            action_type='created',
            metadata={'user': self.request.user.username}
        )

    # -----------------------------
    # Update ticket with optimistic locking
    # -----------------------------
    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        client_updated_at = request.data.get('updated_at')

        if client_updated_at and str(instance.updated_at) != client_updated_at:
            return Response(
                {"error": "STALE_UPDATE", "message": "This ticket has been modified by another user."},
                status=status.HTTP_409_CONFLICT
            )

        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        return Response(serializer.data)

    def perform_update(self, serializer):
        ticket = serializer.save()
        TimelineLog.objects.create(
            ticket=ticket,
            action_type='updated',
            metadata={'user': self.request.user.username}
        )

    # -----------------------------
    # Add comment
    # -----------------------------
    @action(detail=True, methods=['post'])
    def add_comment(self, request, pk=None):
        ticket = self.get_object()
        serializer = CommentSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(user=request.user, ticket=ticket)
            TimelineLog.objects.create(
                ticket=ticket,
                action_type='comment_added',
                metadata={'user': request.user.username, 'text': request.data.get('text', '')[:50]}
            )
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    # -----------------------------
    # Get comments
    # -----------------------------
    @action(detail=True, methods=['get'])
    def comments(self, request, pk=None):
        ticket = self.get_object()
        comments = ticket.comments.all().order_by('created_at')
        serializer = CommentSerializer(comments, many=True)
        return Response(serializer.data)

    # -----------------------------
    # Get timeline logs
    # -----------------------------
    @action(detail=True, methods=['get'])
    def timeline(self, request, pk=None):
        ticket = self.get_object()
        logs = ticket.timeline_logs.all().order_by('created_at')
        serializer = TimelineSerializer(logs, many=True)
        return Response(serializer.data)

    # -----------------------------
    # Get breached tickets
    # -----------------------------
    @action(detail=False, methods=['get'])
    def breached(self, request):
        now = timezone.now()
        tickets = self.get_queryset().filter(
            sla_deadline__lt=now,
            status__in=['open', 'in_progress']
        )
        serializer = self.get_serializer(tickets, many=True)
        return Response(serializer.data)

    # -----------------------------
    # Assign ticket to agent (admin only)
    # -----------------------------
    @action(detail=True, methods=['patch'])
    def assign_agent(self, request, pk=None):
        if request.user.role != 'admin':
            return Response({"error": "FORBIDDEN"}, status=status.HTTP_403_FORBIDDEN)

        ticket = self.get_object()
        agent_id = request.data.get('agent_id')
        if not agent_id:
            return Response({"error": "Missing agent_id"}, status=status.HTTP_400_BAD_REQUEST)

        User = get_user_model()
        try:
            agent = User.objects.get(id=agent_id, role='agent')
        except User.DoesNotExist:
            return Response({"error": "Agent not found"}, status=status.HTTP_404_NOT_FOUND)

        ticket.assignee = agent
        ticket.save()
        TimelineLog.objects.create(
            ticket=ticket,
            action_type='assigned',
            metadata={'user': request.user.username, 'assignee': agent.username}
        )

        serializer = self.get_serializer(ticket)
        return Response(serializer.data)


# -----------------------------
# API view to fetch all agents
# -----------------------------
@api_view(['GET'])
def list_agents(request):
    if request.user.role != 'admin':
        return Response({"error": "FORBIDDEN"}, status=403)
    User = get_user_model()
    agents = User.objects.filter(role='agent')
    data = [{"id": a.id, "username": a.username} for a in agents]
    return Response(data)
