AUTHENTICATION_BACKENDS = [
    'django.contrib.auth.backends.ModelBackend',  # Backend par défaut
    # Ajoutez d'autres backends si nécessaire
]

# Utilisez le modèle d'utilisateur personnalisé
AUTH_USER_MODEL = 'alyawebapp.CustomUser' 