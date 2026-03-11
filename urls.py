"""Waitlist URL Configuration."""

from django.urls import path
from . import views

app_name = 'waitlist'

urlpatterns = [
    # Main views
    path('', views.index, name='index'),
    path('add/', views.add_entry, name='add_entry'),
    path('display/', views.display, name='display'),
    path('settings/', views.settings, name='settings'),

    # Status actions
    path('<uuid:pk>/call/', views.call_entry, name='call_entry'),
    path('<uuid:pk>/seat/', views.seat_entry, name='seat_entry'),
    path('<uuid:pk>/complete/', views.complete_entry, name='complete_entry'),
    path('<uuid:pk>/no-show/', views.no_show_entry, name='no_show_entry'),
    path('<uuid:pk>/cancel/', views.cancel_entry, name='cancel_entry'),

    # Settings actions
    path('settings/save/', views.settings_save, name='settings_save'),
    path('settings/toggle/', views.settings_toggle, name='settings_toggle'),
    path('settings/input/', views.settings_input, name='settings_input'),
]
