from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils import timezone
from django.conf import settings

# Custom user with roles
class User(AbstractUser):
    ROLE_CHOICES = (
        ('user','User'),
        ('agent','Agent'),
        ('admin','Admin'),
    )
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default='user')

# Ticket Model
class Ticket(models.Model):
    PRIORITY_CHOICES = (
        ('low','Low'),
        ('medium','Medium'),
        ('high','High'),
    )
    STATUS_CHOICES = (
        ('open','Open'),
        ('in_progress','In Progress'),
        ('closed','Closed'),
    )

    title = models.CharField(max_length=255)
    description = models.TextField()
    priority = models.CharField(max_length=10, choices=PRIORITY_CHOICES, default='low')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='open')
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='tickets')
    assignee = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='assigned_tickets')
    sla_deadline = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        # Auto-calculate SLA based on priority if not set
        if not self.sla_deadline:
            if self.priority == 'high':
                self.sla_deadline = timezone.now() + timezone.timedelta(hours=24)
            elif self.priority == 'medium':
                self.sla_deadline = timezone.now() + timezone.timedelta(hours=48)
            else:
                self.sla_deadline = timezone.now() + timezone.timedelta(hours=72)
        super().save(*args, **kwargs)

# Comment Model
class Comment(models.Model):
    ticket = models.ForeignKey(Ticket, on_delete=models.CASCADE, related_name='comments')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    text = models.TextField()
    parent = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True, related_name='replies')
    created_at = models.DateTimeField(auto_now_add=True)

# Timeline Log
class TimelineLog(models.Model):
    ticket = models.ForeignKey(Ticket, on_delete=models.CASCADE, related_name='timeline_logs')  # updated related_name
    action_type = models.CharField(max_length=50)
    metadata = models.JSONField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
