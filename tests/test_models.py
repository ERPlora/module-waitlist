"""
Tests for Waitlist module models.
"""

import pytest
from django.utils import timezone

from waitlist.models import WaitlistSettings, WaitlistEntry


# ==============================================================================
# WAITLIST SETTINGS TESTS
# ==============================================================================

@pytest.mark.django_db
class TestWaitlistSettings:
    """Tests for WaitlistSettings model."""

    def test_create_settings(self, waitlist_settings):
        """Test settings creation with defaults."""
        assert waitlist_settings is not None
        assert waitlist_settings.average_service_time == 30
        assert waitlist_settings.max_queue_size == 20
        assert waitlist_settings.display_mode is False

    def test_str(self, waitlist_settings):
        """Test string representation."""
        assert str(waitlist_settings) == f'Waitlist Settings (hub {waitlist_settings.hub_id})'

    def test_get_settings_creates_if_missing(self):
        """Test get_settings creates new settings if none exist."""
        settings = WaitlistSettings.get_settings('test-hub-id')
        assert settings is not None
        assert settings.hub_id == 'test-hub-id'
        assert settings.average_service_time == 30

    def test_get_settings_returns_existing(self):
        """Test get_settings returns existing settings."""
        WaitlistSettings.objects.create(hub_id='test-hub-2', average_service_time=45)
        settings = WaitlistSettings.get_settings('test-hub-2')
        assert settings.average_service_time == 45


# ==============================================================================
# WAITLIST ENTRY TESTS
# ==============================================================================

@pytest.mark.django_db
class TestWaitlistEntry:
    """Tests for WaitlistEntry model."""

    def test_create_entry(self, waiting_entry):
        """Test entry creation."""
        assert waiting_entry.name == 'John Doe'
        assert waiting_entry.phone == '+1234567890'
        assert waiting_entry.party_size == 2
        assert waiting_entry.service_type == 'Haircut'
        assert waiting_entry.priority == 'normal'
        assert waiting_entry.status == 'waiting'
        assert waiting_entry.position == 1

    def test_str(self, waiting_entry):
        """Test string representation."""
        assert '#1' in str(waiting_entry)
        assert 'John Doe' in str(waiting_entry)

    def test_wait_minutes(self, waiting_entry):
        """Test wait_minutes property."""
        assert waiting_entry.wait_minutes >= 0

    def test_status_class(self, waiting_entry, called_entry, in_service_entry):
        """Test status_class property."""
        assert waiting_entry.status_class == 'warning'
        assert called_entry.status_class == 'primary'
        assert in_service_entry.status_class == 'success'

    def test_is_active(self, waiting_entry, called_entry, in_service_entry):
        """Test is_active property."""
        assert waiting_entry.is_active is True
        assert called_entry.is_active is True
        assert in_service_entry.is_active is False

    # ── call action ──────────────────────────────────────────────────────

    def test_call_waiting(self, waiting_entry):
        """Test calling a waiting entry."""
        assert waiting_entry.call() is True
        waiting_entry.refresh_from_db()
        assert waiting_entry.status == 'called'
        assert waiting_entry.called_at is not None

    def test_call_non_waiting(self, called_entry):
        """Test calling a non-waiting entry fails."""
        assert called_entry.call() is False

    # ── seat action ──────────────────────────────────────────────────────

    def test_seat_waiting(self, waiting_entry):
        """Test seating a waiting entry."""
        assert waiting_entry.seat() is True
        waiting_entry.refresh_from_db()
        assert waiting_entry.status == 'in_service'
        assert waiting_entry.called_at is not None

    def test_seat_called(self, called_entry):
        """Test seating a called entry."""
        assert called_entry.seat() is True
        called_entry.refresh_from_db()
        assert called_entry.status == 'in_service'

    def test_seat_in_service_fails(self, in_service_entry):
        """Test seating an already in-service entry fails."""
        assert in_service_entry.seat() is False

    # ── complete action ──────────────────────────────────────────────────

    def test_complete_in_service(self, in_service_entry):
        """Test completing an in-service entry."""
        assert in_service_entry.complete() is True
        in_service_entry.refresh_from_db()
        assert in_service_entry.status == 'completed'
        assert in_service_entry.completed_at is not None

    def test_complete_called(self, called_entry):
        """Test completing a called entry."""
        assert called_entry.complete() is True
        called_entry.refresh_from_db()
        assert called_entry.status == 'completed'

    def test_complete_waiting_fails(self, waiting_entry):
        """Test completing a waiting entry fails."""
        assert waiting_entry.complete() is False

    # ── no-show action ───────────────────────────────────────────────────

    def test_no_show_waiting(self, waiting_entry):
        """Test marking waiting entry as no-show."""
        assert waiting_entry.mark_no_show() is True
        waiting_entry.refresh_from_db()
        assert waiting_entry.status == 'no_show'

    def test_no_show_called(self, called_entry):
        """Test marking called entry as no-show."""
        assert called_entry.mark_no_show() is True
        called_entry.refresh_from_db()
        assert called_entry.status == 'no_show'

    def test_no_show_in_service_fails(self, in_service_entry):
        """Test no-show on in-service entry fails."""
        assert in_service_entry.mark_no_show() is False

    # ── cancel action ────────────────────────────────────────────────────

    def test_cancel_waiting(self, waiting_entry):
        """Test cancelling a waiting entry."""
        assert waiting_entry.cancel() is True
        waiting_entry.refresh_from_db()
        assert waiting_entry.status == 'cancelled'

    def test_cancel_called(self, called_entry):
        """Test cancelling a called entry."""
        assert called_entry.cancel() is True
        called_entry.refresh_from_db()
        assert called_entry.status == 'cancelled'

    def test_cancel_in_service_fails(self, in_service_entry):
        """Test cancelling an in-service entry fails."""
        assert in_service_entry.cancel() is False

    # ── class methods ────────────────────────────────────────────────────

    def test_next_position_empty(self):
        """Test next_position with no entries."""
        assert WaitlistEntry.next_position('new-hub') == 1

    def test_next_position_with_entries(self, waiting_entry):
        """Test next_position with existing entries."""
        hub = waiting_entry.hub_id
        pos = WaitlistEntry.next_position(hub)
        assert pos == waiting_entry.position + 1

    def test_get_active_queue(self, waiting_entry, called_entry, in_service_entry):
        """Test get_active_queue returns only waiting and called."""
        hub = waiting_entry.hub_id
        # Make all entries same hub
        called_entry.hub_id = hub
        called_entry.save(update_fields=['hub_id'])
        in_service_entry.hub_id = hub
        in_service_entry.save(update_fields=['hub_id'])

        active = WaitlistEntry.get_active_queue(hub)
        statuses = set(active.values_list('status', flat=True))
        assert 'in_service' not in statuses
        assert 'waiting' in statuses or 'called' in statuses

    def test_get_today_entries(self, waiting_entry):
        """Test get_today_entries returns today's entries."""
        hub = waiting_entry.hub_id
        entries = WaitlistEntry.get_today_entries(hub)
        assert waiting_entry in entries
