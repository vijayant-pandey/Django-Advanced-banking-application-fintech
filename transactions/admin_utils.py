from django.utils.timezone import now, localtime

# def expiry_badge(self, obj):
#     expires_at = localtime(obj.expires_at)
#     current_time = localtime(now())

#     if expires_at <= current_time:
#         return "❌ EXPIRED"
#     return "🟢 ACTIVE"

# def time_left(self, obj):
#     expires_at = localtime(obj.expires_at)
#     current_time = localtime(now())

#     remaining = expires_at - current_time

#     if remaining.total_seconds() <= 0:
#         return "Expired"

#     minutes, seconds = divmod(int(remaining.total_seconds()), 60)
#     return f"{minutes}m {seconds}s"


# transactions/admin_utils.py
from django.utils.timezone import now

def expiry_badge(expires_at):
    if not expires_at:
        return "-"
    if expires_at < now():
        return "❌ EXPIRED"
    return "🟢 ACTIVE"

def time_left(expires_at):
    if not expires_at:
        return "-"
    delta = expires_at - now()
    if delta.total_seconds() <= 0:
        return "Expired"
    m, s = divmod(int(delta.total_seconds()), 60)
    return f"{m}m {s}s"
