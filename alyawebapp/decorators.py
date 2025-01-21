from functools import wraps
from django.shortcuts import redirect
from django.contrib import messages

def admin_moderator_required(view_func):
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if request.user.is_authenticated and (request.user.is_admin() or request.user.is_moderator()):
            return view_func(request, *args, **kwargs)
        messages.error(request, "Accès non autorisé")
        return redirect('compte')
    return _wrapped_view 