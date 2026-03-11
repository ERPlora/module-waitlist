"""Waitlist views.

Sections: Queue, Add Entry, Display, Settings, Status Actions.
"""

import json

from django.db.models import Avg, Q
from django.http import JsonResponse, HttpResponse
from django.shortcuts import get_object_or_404
from django.views.decorators.http import require_POST
from django.utils.translation import gettext as _
from django.utils import timezone

from apps.accounts.decorators import login_required, permission_required
from apps.core.htmx import htmx_view
from apps.modules_runtime.navigation import with_module_nav

from .models import WaitlistEntry, WaitlistSettings
from .forms import WaitlistEntryForm, WaitlistSettingsForm


# ── helpers ──────────────────────────────────────────────────────────────────

def _hub(request):
    return request.session.get('hub_id')


def _recalculate_wait_times(hub_id):
    """Recalculate estimated wait times for all waiting entries."""
    settings = WaitlistSettings.get_settings(hub_id)
    avg_time = settings.average_service_time
    waiting = WaitlistEntry.objects.filter(
        hub_id=hub_id, is_deleted=False, status='waiting',
    ).order_by('priority', 'position')
    for i, entry in enumerate(waiting):
        entry.estimated_wait = (i + 1) * avg_time
        entry.save(update_fields=['estimated_wait', 'updated_at'])


# ==============================================================================
# QUEUE (INDEX)
# ==============================================================================

@login_required
@with_module_nav('waitlist', 'queue')
@htmx_view('waitlist/pages/index.html', 'waitlist/partials/queue.html')
def index(request):
    """Live queue list."""
    hub = _hub(request)
    entries = WaitlistEntry.get_today_entries(hub)
    active = entries.filter(status__in=['waiting', 'called', 'in_service'])
    waiting = entries.filter(status='waiting')
    completed_today = entries.filter(status='completed')

    # Stats
    waiting_count = waiting.count()
    settings = WaitlistSettings.get_settings(hub)
    avg_wait = waiting_count * settings.average_service_time if waiting_count else 0

    return {
        'entries': active,
        'waiting_count': waiting_count,
        'in_service_count': entries.filter(status='in_service').count(),
        'completed_count': completed_today.count(),
        'avg_wait': avg_wait,
        'settings': settings,
    }


# ==============================================================================
# ADD ENTRY
# ==============================================================================

@login_required
@with_module_nav('waitlist', 'queue')
@htmx_view('waitlist/pages/add_entry.html', 'waitlist/partials/add_entry.html')
def add_entry(request):
    """Add a new entry to the waitlist."""
    hub = _hub(request)
    settings = WaitlistSettings.get_settings(hub)

    # Check queue capacity
    current_waiting = WaitlistEntry.objects.filter(
        hub_id=hub, is_deleted=False, status='waiting',
    ).count()

    if request.method == 'POST':
        if current_waiting >= settings.max_queue_size:
            form = WaitlistEntryForm(request.POST)
            return {
                'form': form,
                'settings': settings,
                'queue_full': True,
                'current_count': current_waiting,
            }

        form = WaitlistEntryForm(request.POST)
        if form.is_valid():
            entry = form.save(commit=False)
            entry.hub_id = hub
            entry.position = WaitlistEntry.next_position(hub)
            entry.estimated_wait = entry.position * settings.average_service_time
            entry.save()

            response = HttpResponse(status=204)
            response['HX-Trigger'] = json.dumps({
                'showToast': {'message': str(_('Added to waitlist')), 'color': 'success'},
                'refreshQueue': True,
            })
            response['HX-Redirect'] = '/waitlist/'
            return response

        return {'form': form, 'settings': settings, 'current_count': current_waiting}

    form = WaitlistEntryForm(initial={'party_size': 1, 'priority': 'normal'})
    return {
        'form': form,
        'settings': settings,
        'current_count': current_waiting,
        'queue_full': current_waiting >= settings.max_queue_size,
    }


# ==============================================================================
# STATUS ACTIONS
# ==============================================================================

@login_required
@require_POST
def call_entry(request, pk):
    """Mark entry as called."""
    hub = _hub(request)
    entry = get_object_or_404(WaitlistEntry, pk=pk, hub_id=hub, is_deleted=False)
    if entry.call():
        response = HttpResponse(status=204)
        response['HX-Trigger'] = json.dumps({
            'showToast': {'message': str(_('Guest called')), 'color': 'primary'},
            'refreshQueue': True,
        })
        return response
    return JsonResponse({'success': False, 'error': _('Cannot call this entry')}, status=400)


@login_required
@require_POST
def seat_entry(request, pk):
    """Mark entry as in service."""
    hub = _hub(request)
    entry = get_object_or_404(WaitlistEntry, pk=pk, hub_id=hub, is_deleted=False)
    if entry.seat():
        _recalculate_wait_times(hub)
        response = HttpResponse(status=204)
        response['HX-Trigger'] = json.dumps({
            'showToast': {'message': str(_('Guest seated')), 'color': 'success'},
            'refreshQueue': True,
        })
        return response
    return JsonResponse({'success': False, 'error': _('Cannot seat this entry')}, status=400)


@login_required
@require_POST
def complete_entry(request, pk):
    """Mark entry as completed."""
    hub = _hub(request)
    entry = get_object_or_404(WaitlistEntry, pk=pk, hub_id=hub, is_deleted=False)
    if entry.complete():
        _recalculate_wait_times(hub)
        response = HttpResponse(status=204)
        response['HX-Trigger'] = json.dumps({
            'showToast': {'message': str(_('Service completed')), 'color': 'success'},
            'refreshQueue': True,
        })
        return response
    return JsonResponse({'success': False, 'error': _('Cannot complete this entry')}, status=400)


@login_required
@require_POST
def no_show_entry(request, pk):
    """Mark entry as no-show."""
    hub = _hub(request)
    entry = get_object_or_404(WaitlistEntry, pk=pk, hub_id=hub, is_deleted=False)
    if entry.mark_no_show():
        _recalculate_wait_times(hub)
        response = HttpResponse(status=204)
        response['HX-Trigger'] = json.dumps({
            'showToast': {'message': str(_('Marked as no-show')), 'color': 'warning'},
            'refreshQueue': True,
        })
        return response
    return JsonResponse({'success': False, 'error': _('Cannot mark as no-show')}, status=400)


@login_required
@require_POST
def cancel_entry(request, pk):
    """Cancel entry."""
    hub = _hub(request)
    entry = get_object_or_404(WaitlistEntry, pk=pk, hub_id=hub, is_deleted=False)
    if entry.cancel():
        _recalculate_wait_times(hub)
        response = HttpResponse(status=204)
        response['HX-Trigger'] = json.dumps({
            'showToast': {'message': str(_('Entry cancelled')), 'color': 'error'},
            'refreshQueue': True,
        })
        return response
    return JsonResponse({'success': False, 'error': _('Cannot cancel this entry')}, status=400)


# ==============================================================================
# DISPLAY
# ==============================================================================

@login_required
@with_module_nav('waitlist', 'display')
@htmx_view('waitlist/pages/display.html', 'waitlist/partials/display.html')
def display(request):
    """Public-facing display screen."""
    hub = _hub(request)
    entries = WaitlistEntry.get_active_queue(hub)
    now_serving = entries.filter(status__in=['called', 'in_service']).first()
    upcoming = entries.filter(status='waiting')[:5]

    return {
        'now_serving': now_serving,
        'upcoming': upcoming,
        'total_waiting': entries.filter(status='waiting').count(),
    }


# ==============================================================================
# SETTINGS
# ==============================================================================

@login_required
@permission_required('waitlist.view_settings')
@with_module_nav('waitlist', 'settings')
@htmx_view('waitlist/pages/settings.html', 'waitlist/partials/settings.html')
def settings(request):
    """Waitlist settings page."""
    hub = _hub(request)
    config = WaitlistSettings.get_settings(hub)
    return {'config': config, 'form': WaitlistSettingsForm(instance=config)}


@login_required
@permission_required('waitlist.change_settings')
@require_POST
def settings_save(request):
    """Save all settings."""
    hub = _hub(request)
    config = WaitlistSettings.get_settings(hub)
    form = WaitlistSettingsForm(request.POST, instance=config)
    if form.is_valid():
        form.save()
        response = HttpResponse(status=204)
        response['HX-Trigger'] = json.dumps({
            'showToast': {'message': str(_('Settings saved')), 'color': 'success'},
        })
        return response
    return JsonResponse({'success': False, 'errors': form.errors}, status=400)


@login_required
@permission_required('waitlist.change_settings')
@require_POST
def settings_toggle(request):
    """Toggle a boolean setting."""
    hub = _hub(request)
    name = request.POST.get('name') or request.POST.get('setting_name')
    value = request.POST.get('value', request.POST.get('setting_value', 'false'))
    setting_value = value == 'true' or value is True

    config = WaitlistSettings.get_settings(hub)
    boolean_fields = ['display_mode']
    if name in boolean_fields:
        setattr(config, name, setting_value)
        config.save()

    response = HttpResponse(status=204)
    response['HX-Trigger'] = json.dumps({
        'showToast': {'message': str(_('Setting updated')), 'color': 'success'},
    })
    return response


@login_required
@permission_required('waitlist.change_settings')
@require_POST
def settings_input(request):
    """Update a numeric setting."""
    hub = _hub(request)
    name = request.POST.get('name') or request.POST.get('setting_name')
    value = request.POST.get('value') or request.POST.get('setting_value')

    config = WaitlistSettings.get_settings(hub)
    numeric_fields = ['average_service_time', 'max_queue_size']
    if name in numeric_fields:
        try:
            setattr(config, name, int(value))
            config.save()
        except (ValueError, TypeError):
            pass

    response = HttpResponse(status=204)
    response['HX-Trigger'] = json.dumps({
        'showToast': {'message': str(_('Setting updated')), 'color': 'success'},
    })
    return response
