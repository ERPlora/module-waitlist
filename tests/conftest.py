"""
Pytest fixtures for Waitlist module tests.
"""

import pytest
from django.utils import timezone

from apps.accounts.models import LocalUser
from apps.configuration.models import StoreConfig

from waitlist.models import WaitlistEntry, WaitlistSettings


@pytest.fixture
def local_user(db):
    """Create a test user."""
    from django.contrib.auth.hashers import make_password
    return LocalUser.objects.create(
        name='Test User',
        email='test@example.com',
        role='admin',
        pin_hash=make_password('1234'),
        is_active=True,
    )


@pytest.fixture
def user(local_user):
    """Alias for local_user fixture."""
    return local_user


@pytest.fixture
def store_config(db):
    """Create store config for tests."""
    config = StoreConfig.get_config()
    config.is_configured = True
    config.name = 'Test Store'
    config.save()
    return config


@pytest.fixture
def auth_client(client, local_user, store_config):
    """Return an authenticated client."""
    session = client.session
    session['local_user_id'] = str(local_user.id)
    session['user_name'] = local_user.name
    session['user_email'] = local_user.email
    session['user_role'] = local_user.role
    session['store_config_checked'] = True
    session.save()
    return client


@pytest.fixture
def waitlist_settings(db):
    """Create waitlist settings."""
    return WaitlistSettings.objects.create()


@pytest.fixture
def waiting_entry(db):
    """Create a waiting entry."""
    return WaitlistEntry.objects.create(
        name='John Doe',
        phone='+1234567890',
        party_size=2,
        service_type='Haircut',
        priority='normal',
        status='waiting',
        position=1,
        estimated_wait=30,
    )


@pytest.fixture
def vip_entry(db):
    """Create a VIP waiting entry."""
    return WaitlistEntry.objects.create(
        name='VIP Guest',
        phone='+0987654321',
        party_size=4,
        priority='vip',
        status='waiting',
        position=2,
        estimated_wait=60,
    )


@pytest.fixture
def called_entry(db):
    """Create a called entry."""
    return WaitlistEntry.objects.create(
        name='Jane Smith',
        phone='+1111111111',
        party_size=1,
        status='called',
        position=3,
        called_at=timezone.now(),
    )


@pytest.fixture
def in_service_entry(db):
    """Create an in-service entry."""
    return WaitlistEntry.objects.create(
        name='Bob Wilson',
        phone='+2222222222',
        party_size=3,
        status='in_service',
        position=4,
        called_at=timezone.now(),
    )
