from django.urls import path
from . import views
from django.contrib.auth.views import LogoutView

urlpatterns = [
    path('', views.home, name='home'),
    path('login/', views.login_view, name='login'),
    path('register/', views.register, name='register'),
    path('compte/', views.compte, name='compte'),
    path('logout/', LogoutView.as_view(next_page='home'), name='logout'),
    path('chat/', views.chat_view, name='chat'),
    path('chat-history/', views.chat_history, name='chat_history'),
    path('get-conversation/<int:chat_id>/', views.get_conversation, name='get_conversation'),
    path('update-profile/', views.update_profile, name='update_profile'),
    path('update-domains/', views.update_domains, name='update_domains'),
    path('update-company-size/', views.update_company_size, name='update_company_size'),
    path('update-objectifs/', views.update_objectifs, name='update_objectifs'),
    path('update-integrations/', views.update_integrations, name='update_integrations'),
    path('get-user-integrations/<str:domain_name>/', views.get_user_integrations, name='get_user_integrations'),
    path('get-integrations/<str:domain_name>/', views.get_integrations, name='get_integrations'),
    path('update-integration-config/', views.update_integration_config, name='update_integration_config'),
    path('api/integration/<int:integration_id>/config/', views.get_integration_config, name='get_integration_config'),
    path('get-integrations-state/', views.get_integrations_state, name='get_integrations_state'),
    path('toggle-integration/', views.toggle_integration, name='toggle_integration'),
    path('get-integration-config/<int:integration_id>/', views.get_integration_config, name='get_integration_config'),
    path('save-integration-config/', views.save_integration_config, name='save_integration_config'),
    path('test-integration/<int:integration_id>/', views.test_integration, name='test_integration'),
] 