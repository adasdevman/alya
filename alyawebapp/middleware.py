from django.shortcuts import redirect
from django.urls import reverse
from django.contrib.auth.models import User
from django.db.models import Q
from django.utils.log import logger
from django.contrib.auth.models import UserProfile

class OnboardingMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Log pour identifier si ce middleware est appelé
        logger.error(f"MIDDLEWARE DEBUG - Path: {request.path}")
        
        # Ne pas intercepter ces URLs
        excluded_paths = [
            '/onboarding/',
            '/logout/',
            '/login/',
            '/admin/',
            '/static/',
            '/media/',
        ]
        
        if any(request.path.startswith(path) for path in excluded_paths):
            return self.get_response(request)

        # Vérifier si l'utilisateur est connecté
        if request.user.is_authenticated:
            try:
                profile = UserProfile.objects.get(user=request.user)
                logger.error(f"MIDDLEWARE DEBUG - User: {request.user.username}, Path: {request.path}")
                return self.get_response(request)
            except UserProfile.DoesNotExist:
                logger.error("MIDDLEWARE DEBUG - No profile found")
                return self.get_response(request)

        return self.get_response(request) 