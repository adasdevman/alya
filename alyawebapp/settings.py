LOGIN_REDIRECT_URL = 'compte'
LOGOUT_REDIRECT_URL = 'home'
OPENAI_API_KEY = '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'  # Remplacez par votre vraie clé API 

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    # Vérifiez si ce middleware est présent et retirez-le
    # 'alyawebapp.middleware.OnboardingMiddleware',
] 