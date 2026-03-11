"""Waitlist forms."""

from django import forms
from django.utils.translation import gettext_lazy as _

from .models import WaitlistEntry, WaitlistSettings


class WaitlistEntryForm(forms.ModelForm):
    """Form for adding a new waitlist entry."""

    class Meta:
        model = WaitlistEntry
        fields = ['name', 'phone', 'party_size', 'service_type', 'priority', 'notes']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'input', 'placeholder': _('Guest name'), 'autofocus': True}),
            'phone': forms.TextInput(attrs={'class': 'input', 'placeholder': _('Phone (optional)'), 'type': 'tel'}),
            'party_size': forms.NumberInput(attrs={'class': 'input', 'min': 1, 'max': 50}),
            'service_type': forms.TextInput(attrs={'class': 'input', 'placeholder': _('Service type (optional)')}),
            'priority': forms.Select(attrs={'class': 'select'}),
            'notes': forms.Textarea(attrs={'class': 'textarea', 'rows': 2, 'placeholder': _('Notes (optional)')}),
        }


class WaitlistSettingsForm(forms.ModelForm):
    """Form for editing waitlist settings."""

    class Meta:
        model = WaitlistSettings
        fields = ['average_service_time', 'max_queue_size', 'display_mode']
        widgets = {
            'average_service_time': forms.NumberInput(attrs={'class': 'input', 'min': 1, 'max': 240}),
            'max_queue_size': forms.NumberInput(attrs={'class': 'input', 'min': 1, 'max': 200}),
            'display_mode': forms.CheckboxInput(attrs={'class': 'toggle'}),
        }
