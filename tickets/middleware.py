import time
from django.http import JsonResponse
from django.core.cache import cache

class RateLimitMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if not request.user.is_authenticated:
            return self.get_response(request)

        user_key = f"rate_{request.user.id}"
        history = cache.get(user_key, [])

        now = time.time()
        # Remove requests older than 60 sec
        history = [t for t in history if now - t < 60]

        if len(history) >= 60:
            return JsonResponse({"error": {"code": "RATE_LIMIT", "message": "Too many requests"}}, status=429)

        history.append(now)
        cache.set(user_key, history, timeout=60)
        return self.get_response(request)
