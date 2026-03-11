"""Waitlist models.

Models:
- WaitlistSettings — per-hub configuration
- WaitlistEntry — individual queue entry
"""

from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from apps.core.models import HubBaseModel


# ==============================================================================
# SETTINGS
# ==============================================================================

class WaitlistSettings(HubBaseModel):
    """Per-hub waitlist settings."""

    average_service_time = models.PositiveIntegerField(
        default=30, help_text=_('Average service time in minutes'),
    )
    max_queue_size = models.PositiveIntegerField(
        default=20, help_text=_('Maximum number of entries in the queue'),
    )
    display_mode = models.BooleanField(
        default=False, help_text=_('Enable public display mode'),
    )

    class Meta(HubBaseModel.Meta):
        db_table = 'waitlist_settings'
        verbose_name = _('Waitlist Settings')
        verbose_name_plural = _('Waitlist Settings')
        constraints = [
            models.UniqueConstraint(fields=['hub_id'], name='unique_waitlist_settings_per_hub'),
        ]

    def __str__(self):
        return f'Waitlist Settings (hub {self.hub_id})'

    @classmethod
    def get_settings(cls, hub_id):
        """Get or create settings for a hub."""
        try:
            return cls.all_objects.get(hub_id=hub_id)
        except cls.DoesNotExist:
            from django.db import IntegrityError
            try:
                return cls.all_objects.create(hub_id=hub_id)
            except IntegrityError:
                return cls.all_objects.get(hub_id=hub_id)


# ==============================================================================
# ENTRY
# ==============================================================================

class WaitlistEntry(HubBaseModel):
    """Individual queue entry."""

    STATUS_CHOICES = [
        ('waiting', _('Waiting')),
        ('called', _('Called')),
        ('in_service', _('In Service')),
        ('no_show', _('No Show')),
        ('completed', _('Completed')),
        ('cancelled', _('Cancelled')),
    ]
    PRIORITY_CHOICES = [
        ('normal', _('Normal')),
        ('vip', _('VIP')),
    ]

    name = models.CharField(max_length=150)
    phone = models.CharField(max_length=30, blank=True, default='')
    party_size = models.PositiveIntegerField(default=1)
    service_type = models.CharField(max_length=100, blank=True, default='')
    priority = models.CharField(max_length=10, choices=PRIORITY_CHOICES, default='normal')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='waiting', db_index=True)
    position = models.PositiveIntegerField(default=0)
    estimated_wait = models.PositiveIntegerField(null=True, blank=True, help_text=_('Estimated wait in minutes'))
    joined_at = models.DateTimeField(auto_now_add=True)
    called_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    notes = models.TextField(blank=True, default='')

    class Meta(HubBaseModel.Meta):
        db_table = 'waitlist_entry'
        verbose_name = _('Waitlist Entry')
        verbose_name_plural = _('Waitlist Entries')
        ordering = ['priority', 'position']
        indexes = [
            models.Index(fields=['hub_id', 'status']),
        ]

    def __str__(self):
        return f'#{self.position} {self.name} ({self.get_status_display()})'

    # ── properties ───────────────────────────────────────────────────────

    @property
    def wait_minutes(self):
        """Minutes since joined_at."""
        if not self.joined_at:
            return 0
        delta = timezone.now() - self.joined_at
        return int(delta.total_seconds() / 60)

    @property
    def status_class(self):
        """CSS color class for badge."""
        return {
            'waiting': 'warning',
            'called': 'primary',
            'in_service': 'success',
            'no_show': 'dark',
            'completed': 'medium',
            'cancelled': 'error',
        }.get(self.status, 'medium')

    @property
    def is_active(self):
        """True if waiting or called."""
        return self.status in ('waiting', 'called')

    # ── actions ──────────────────────────────────────────────────────────

    def call(self):
        """Mark entry as called."""
        if self.status != 'waiting':
            return False
        self.status = 'called'
        self.called_at = timezone.now()
        self.save(update_fields=['status', 'called_at', 'updated_at'])
        return True

    def seat(self):
        """Mark entry as in service."""
        if self.status not in ('waiting', 'called'):
            return False
        self.status = 'in_service'
        if not self.called_at:
            self.called_at = timezone.now()
        self.save(update_fields=['status', 'called_at', 'updated_at'])
        return True

    def complete(self):
        """Mark entry as completed."""
        if self.status not in ('called', 'in_service'):
            return False
        self.status = 'completed'
        self.completed_at = timezone.now()
        self.save(update_fields=['status', 'completed_at', 'updated_at'])
        return True

    def mark_no_show(self):
        """Mark entry as no-show."""
        if self.status not in ('waiting', 'called'):
            return False
        self.status = 'no_show'
        self.save(update_fields=['status', 'updated_at'])
        return True

    def cancel(self):
        """Cancel entry."""
        if self.status not in ('waiting', 'called'):
            return False
        self.status = 'cancelled'
        self.save(update_fields=['status', 'updated_at'])
        return True

    # ── queries ──────────────────────────────────────────────────────────

    @classmethod
    def get_active_queue(cls, hub_id):
        """Get active queue entries (waiting + called)."""
        return cls.objects.filter(
            hub_id=hub_id, is_deleted=False,
            status__in=['waiting', 'called'],
        ).order_by('priority', 'position')

    @classmethod
    def get_today_entries(cls, hub_id):
        """Get all entries for today."""
        today = timezone.now().date()
        return cls.objects.filter(
            hub_id=hub_id, is_deleted=False,
            joined_at__date=today,
        ).order_by('priority', 'position')

    @classmethod
    def next_position(cls, hub_id):
        """Get the next position number for a new entry."""
        last = cls.objects.filter(
            hub_id=hub_id, is_deleted=False,
            status='waiting',
        ).order_by('-position').first()
        return (last.position + 1) if last else 1
