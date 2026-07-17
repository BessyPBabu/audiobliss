import logging
from functools import wraps
from django.contrib import messages
from django.shortcuts import redirect

logger = logging.getLogger(__name__)


def admin_required(view_func):
    
    @wraps(view_func)
    def _wrapped(request, *args, **kwargs):
        if not request.user.is_authenticated or not request.user.is_admin:
            logger.warning(
                "Unauthorized admin access attempt: user=%s path=%s",
                getattr(request.user, 'id', 'anonymous'), request.path,
            )
            messages.error(request, "You must be logged in as an admin to view this page.")
            return redirect('adminlog:admin_login')
        return view_func(request, *args, **kwargs)
    return _wrapped