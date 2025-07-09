from django.middleware.csrf import CsrfViewMiddleware

class SkipCSRFMiddlewareForJWT(CsrfViewMiddleware):
    def process_view(self, request, callback, callback_args, callback_kwargs):
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            # Marcar como CSRF-exempt para que no falle, pero seguir procesando todo lo demás
            setattr(request, '_dont_enforce_csrf_checks', True)
        return super().process_view(request, callback, callback_args, callback_kwargs)