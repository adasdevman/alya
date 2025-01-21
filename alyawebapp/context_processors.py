def user_context(request):
    if request.user.is_authenticated:
        return {
            'user_domains': request.user.userdomain_set.all(),
            'interactions': request.user.interaction_set.all()[:5]
        }
    return {} 