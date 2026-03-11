"""
AI context for the Waitlist module.
Loaded into the assistant system prompt when this module's tools are active.
"""

CONTEXT = """
## Module Knowledge: Waitlist

### Models

**WaitlistSettings** — singleton per hub.
- `average_service_time` (int, default 30): minutes per customer, used to estimate wait times
- `max_queue_size` (int, default 20): maximum entries allowed in the active queue
- `display_mode` (bool, default False): enables a public-facing display screen
- Accessed via: `WaitlistSettings.get_settings(hub_id)`

**WaitlistEntry** — one customer or party in the queue.
- `name` (str, max 150): customer name
- `phone` (str): contact number for notifications
- `party_size` (int, default 1): number of people in the group
- `service_type` (str): requested service (e.g. "Haircut", "Table for 2")
- `priority` (choice): normal (default), vip
- `status` (choice): waiting → called → in_service → completed / no_show / cancelled
- `position` (int): queue position number
- `estimated_wait` (int, nullable): estimated wait in minutes
- `joined_at` (datetime, auto): when entry was created
- `called_at` (datetime, nullable): when customer was called
- `completed_at` (datetime, nullable): when service finished
- `notes` (text)

### Key flows

1. **Add to queue**: create WaitlistEntry with name, party_size, service_type. Use `WaitlistEntry.next_position(hub_id)` for position. Status starts as "waiting".
2. **Call customer**: call entry.call() — sets status="called", called_at=now.
3. **Seat / begin service**: call entry.seat() — sets status="in_service".
4. **Complete service**: call entry.complete() — sets status="completed", completed_at=now.
5. **No-show**: call entry.mark_no_show() — sets status="no_show".
6. **Cancel**: call entry.cancel() — sets status="cancelled".
7. **View active queue**: use WaitlistEntry.get_active_queue(hub_id) — returns waiting + called entries ordered by priority then position.
8. **Today's history**: use WaitlistEntry.get_today_entries(hub_id).

### Status flow
waiting → called → in_service → completed
waiting / called → no_show
waiting / called → cancelled

### Notes
- VIP entries should be inserted at the front — assign a lower position number.
- estimated_wait = position * average_service_time (from settings).
- is_active property returns True for status in ('waiting', 'called').
"""
