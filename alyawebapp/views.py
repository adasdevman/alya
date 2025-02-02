from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth import authenticate
from django.contrib.auth import login as auth_login
from django.contrib.auth import logout as auth_logout
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_protect, csrf_exempt
from datetime import timedelta
import json
from openai import OpenAI
import logging
import os
from dotenv import load_dotenv
from django.db import transaction
from django.views.decorators.http import require_http_methods
# Importer les modèles après avoir chargé les variables d'environnement
from .models import (
    CustomUser,
    Domain,
    UserDomain,
    UserProfile,
    Chat,
    Prompt,
    Interaction,
    ChatHistory,
    BusinessObjective,
    CompanySize,
    Integration,
    UserIntegration
)
from alyawebapp.services.ai_orchestrator import AIOrchestrator
import traceback
from .integrations.manager import IntegrationManager
from .integrations.config import INTEGRATION_CONFIGS
from django.core.exceptions import ValidationError
from .utils.openai_utils import call_openai_api, get_system_prompt, get_function_definitions
from .utils.hubspot_utils import execute_hubspot_action
from .integrations.hubspot.handler import HubSpotHandler
from django.conf import settings
import uuid
from django.utils import timezone
from django.urls import reverse
from django.core.serializers.json import DjangoJSONEncoder
from django.utils.safestring import mark_safe

# Charger les variables d'environnement
load_dotenv()

# Configurez le logging
logger = logging.getLogger(__name__)

# Créer le client OpenAI avec la clé depuis .env
api_key = os.getenv('OPENAI_API_KEY')
client = OpenAI(api_key=api_key)

# Log pour déboguer
print(f"API Key trouvée: {'Oui' if api_key else 'Non'}")  # Pour vérifier si la clé est bien chargée

def home(request):
    return render(request, 'alyawebapp/home.html')

def login_view(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)
        
        if user is not None:
            auth_login(request, user, backend='django.contrib.auth.backends.ModelBackend')
            messages.success(request, 'Connexion réussie!')
            return redirect('compte')
        else:
            messages.error(request, 'Nom d\'utilisateur ou mot de passe incorrect.')
    
    return render(request, 'alyawebapp/login.html')

@csrf_protect
def register(request):
    if request.method == 'POST':
        try:
            # Récupérer les données du formulaire
            username = request.POST['username']
            email = request.POST['email']
            password = request.POST['password']
            confirm_password = request.POST['confirm_password']
            
            # Vérifier que les mots de passe correspondent
            if password != confirm_password:
                messages.error(request, 'Les mots de passe ne correspondent pas.')
                return redirect('register')
            
            # Vérifier si l'utilisateur existe déjà
            if CustomUser.objects.filter(username=username).exists():
                messages.error(request, 'Ce nom d\'utilisateur est déjà pris.')
                return redirect('register')
            
            if CustomUser.objects.filter(email=email).exists():
                messages.error(request, 'Cette adresse email est déjà utilisée.')
                return redirect('register')
            
            # Créer l'utilisateur
            user = CustomUser.objects.create_user(
                username=username,
                email=email,
                password=password
            )
            
            # Connecter l'utilisateur
            auth_login(request, user)
            
            messages.success(request, 'Compte créé avec succès !')
            return redirect('compte')  # Rediriger vers compte au lieu de onboarding
            
        except Exception as e:
            logger.error(f"Erreur lors de la création de l'utilisateur : {str(e)}")
            messages.error(request, 'Une erreur est survenue lors de la création du compte.')
            return redirect('register')
    
    return render(request, 'alyawebapp/register.html')

@login_required
def compte(request):
    try:
        # Récupérer ou créer le profil utilisateur
        profile, created = UserProfile.objects.get_or_create(user=request.user)
        
        # Récupérer les données
        user_domains = profile.domains.all()
        all_domains = Domain.objects.all()
        user_objectifs = profile.business_objectives.all()
        all_objectifs = BusinessObjective.objects.all()
        company_sizes = CompanySize.objects.all()
        integrations = Integration.objects.all()
        
        # Sérialiser les configurations
        integration_configs_json = json.dumps(
            INTEGRATION_CONFIGS,
            cls=DjangoJSONEncoder,
            ensure_ascii=False
        )
        
        context = {
            'user_domains': user_domains,
            'all_domains': all_domains,
            'user_objectifs': user_objectifs,
            'all_objectifs': all_objectifs,
            'company_sizes': company_sizes,
            'integrations': integrations,
            'integration_configs_data': integration_configs_json
        }
        
        return render(request, 'alyawebapp/compte.html', context)
    except Exception as e:
        logger.error(f"FATAL COMPTE ERROR: {str(e)}")
        messages.error(request, 'Une erreur est survenue lors du chargement de votre compte.')
        return redirect('home')

@login_required
def update_profile(request):
    if request.method == 'POST':
        user = request.user
        user.first_name = request.POST.get('first_name', '')
        user.last_name = request.POST.get('last_name', '')
        user.email = request.POST.get('email', '')
        user.save()
        messages.success(request, 'Profil mis à jour avec succès!')
        return redirect('compte')
    return redirect('compte')

@require_http_methods(["GET", "POST"])
def logout_view(request):
    auth_logout(request)
    return redirect('home')

@login_required
def onboarding(request):
    try:
        # Logs détaillés pour identifier la source de la redirection
        logger.error("="*50)
        logger.error("ONBOARDING DEBUG - Détails complets")
        logger.error(f"User: {request.user.username}")
        logger.error(f"Session ID: {request.session.session_key}")
        logger.error(f"Headers: {dict(request.headers)}")
        logger.error(f"GET params: {dict(request.GET)}")
        logger.error("="*50)
        
        profile, created = UserProfile.objects.get_or_create(user=request.user)
        
        # Force le rendu de la page sans redirection
        domains = Domain.objects.all()
        response = render(request, 'alyawebapp/onboarding.html', {
            'domains': domains,
            'user_domains': profile.domains.all()
        })
        
        # Log la réponse
        logger.error(f"Response status: {response.status_code}")
        return response

    except Exception as e:
        logger.error(f"FATAL ONBOARDING ERROR: {str(e)}")
        messages.error(request, 'Une erreur critique est survenue.')
        return redirect('home')

# Nouvelle vue de réinitialisation forcée
@login_required
def force_onboarding(request):
    try:
        profile = UserProfile.objects.get(user=request.user)
        profile.domains.clear()
        profile.onboarding_complete = False
        profile.save()
        
        messages.warning(request, 'Votre parcours d\'onboarding a été réinitialisé.')
        return redirect('onboarding')
    
    except Exception as e:
        logger.error(f"FORCE ONBOARDING ERROR: {str(e)}")
        messages.error(request, 'Impossible de réinitialiser l\'onboarding.')
        return redirect('home')

# Ajoutez une vue pour réinitialiser les domaines
@login_required
def reset_domains(request):
    try:
        profile = UserProfile.objects.get(user=request.user)
        profile.domains.clear()
        profile.onboarding_complete = False
        profile.save()
        
        messages.warning(request, 'Vos domaines ont été réinitialisés.')
        return redirect('onboarding')
    
    except UserProfile.DoesNotExist:
        messages.error(request, 'Profil utilisateur non trouvé.')
        return redirect('home')
    except Exception as e:
        logger.error(f"ERREUR lors de la réinitialisation des domaines : {str(e)}")
        messages.error(request, 'Une erreur est survenue lors de la réinitialisation.')
        return redirect('home')

@login_required
def chat(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            message = data.get('message', '')
            chat_id = data.get('chat_id')
            
            # Utiliser l'orchestrator pour traiter le message
            orchestrator = AIOrchestrator(request.user)
            response = orchestrator.process_message(message, chat_id)
            
            return JsonResponse(response)
            
        except Exception as e:
            logger.error(f"Erreur lors du traitement du chat: {str(e)}")
            return JsonResponse({
                "error": str(e)
            }, status=500)
    
    return render(request, 'alyawebapp/chat.html')

@login_required
def get_chat_history(request):
    try:
        # Récupérer tous les chats de l'utilisateur avec leur dernier message
        chats = Chat.objects.filter(user=request.user).order_by('-created_at')
        chat_list = []
        
        for chat in chats:
            # Récupérer le premier message utilisateur de ce chat
            first_message = ChatHistory.objects.filter(
                chat=chat,
                is_user=True
            ).first()
            
            if first_message:
                chat_list.append({
                    'id': chat.id,
                    'preview': first_message.content[:100] + '...' if len(first_message.content) > 100 else first_message.content,
                    'created_at': chat.created_at.isoformat()
                })
        
        return JsonResponse({
            'status': 'success',
            'chats': chat_list
        })
    except Exception as e:
        logger.error(f"Erreur lors de la récupération de l'historique: {str(e)}")
        return JsonResponse({
            'status': 'error',
            'message': str(e)
        }, status=500)

@login_required
def get_conversation(request, chat_id):
    try:
        chat = Chat.objects.get(id=chat_id, user=request.user)
        messages = ChatHistory.objects.filter(chat=chat).order_by('created_at')
        
        return JsonResponse({
            'status': 'success',
            'messages': [{
                'content': msg.content,
                'is_user': msg.is_user,
                'created_at': msg.created_at.strftime('%Y-%m-%d %H:%M:%S')
            } for msg in messages]
        })
    except Chat.DoesNotExist:
        return JsonResponse({
            'status': 'error',
            'message': 'Conversation non trouvée'
        }, status=404)
    except Exception as e:
        logger.error(f"Erreur lors de la récupération de la conversation: {str(e)}")
        return JsonResponse({
            'status': 'error',
            'message': str(e)
        }, status=500)

@login_required
def update_company_size(request):
    if request.method == 'POST':
        try:
            company_size = request.POST.get('company_size')
            if company_size:
                # Mettre à jour directement la valeur de company_size
                request.user.company_size = company_size
                request.user.save()
                
                messages.success(request, 'Taille de l\'entreprise mise à jour avec succès!')
                return JsonResponse({'status': 'success'})
            
            return JsonResponse({
                'status': 'error',
                'message': 'Veuillez sélectionner une taille d\'entreprise.'
            })
            
        except Exception as e:
            logger.error(f"ERREUR DE MISE À JOUR DE LA TAILLE: {str(e)}")
            return JsonResponse({
                'status': 'error',
                'message': 'Une erreur est survenue lors de la mise à jour.'
            })
    return JsonResponse({'status': 'error', 'message': 'Méthode non autorisée'})

@login_required
def update_objectifs(request):
    if request.method == 'POST':
        try:
            profile = UserProfile.objects.get(user=request.user)
            selected_objectifs = request.POST.getlist('objectifs')
            
            # Nettoyer les objectifs existants
            profile.business_objectives.clear()
            
            if selected_objectifs:
                objectives = BusinessObjective.objects.filter(id__in=selected_objectifs)
                profile.business_objectives.add(*objectives)
                return JsonResponse({
                    'status': 'success',
                    'message': 'Objectifs mis à jour avec succès!'
                })
            
            return JsonResponse({
                'status': 'error',
                'message': 'Veuillez sélectionner au moins un objectif.'
            })
            
        except Exception as e:
            logger.error(f"ERREUR DE MISE À JOUR DES OBJECTIFS: {str(e)}")
            return JsonResponse({
                'status': 'error',
                'message': 'Une erreur est survenue lors de la mise à jour.'
            })
    return JsonResponse({'status': 'error', 'message': 'Méthode non autorisée'})

@login_required
def update_domains(request):
    if request.method == 'POST':
        try:
            selected_domains = request.POST.getlist('domains')
            
            # Récupérer ou créer le profil utilisateur
            profile, created = UserProfile.objects.get_or_create(user=request.user)
            
            # Mettre à jour les domaines
            profile.domains.clear()
            if selected_domains:
                domains = Domain.objects.filter(id__in=selected_domains)
                profile.domains.add(*domains)
            
            messages.success(request, 'Domaines mis à jour avec succès!')
            return JsonResponse({'status': 'success'})
            
        except Exception as e:
            logger.error(f"Erreur lors de la mise à jour des domaines: {str(e)}")
            return JsonResponse({
                'status': 'error',
                'message': str(e)
            }, status=400)
    
    return JsonResponse({'status': 'error', 'message': 'Méthode non autorisée'}, status=405)

@login_required
@require_http_methods(["POST"])
def update_integrations(request):
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': 'Méthode non autorisée'})
    
    try:
        # Lire les données POST une seule fois
        post_data = request.POST.copy()
        domain_name = post_data.get('domain_name')
        
        if not domain_name:
            return JsonResponse({'status': 'error', 'message': 'Nom de domaine manquant'})

        domain = Domain.objects.get(name=domain_name)
        selected_integrations = post_data.getlist('integrations')
        
        logger.info(f"Mise à jour des intégrations pour le domaine {domain_name}")
        logger.info(f"Intégrations sélectionnées: {selected_integrations}")

        # Supprimer les intégrations non sélectionnées
        UserIntegration.objects.filter(
            user=request.user,
            integration__domain=domain
        ).exclude(
            integration_id__in=selected_integrations
        ).delete()

        # Créer les nouvelles intégrations sélectionnées
        for integration_id in selected_integrations:
            UserIntegration.objects.get_or_create(
                user=request.user,
                integration_id=integration_id
            )

        logger.info("Mise à jour des intégrations terminée avec succès")
        return JsonResponse({'status': 'success'})

    except Domain.DoesNotExist:
        logger.error(f"Domaine non trouvé: {domain_name}")
        return JsonResponse({'status': 'error', 'message': 'Domaine non trouvé'})
    except Exception as e:
        logger.error(f"Erreur lors de la mise à jour des intégrations: {str(e)}", exc_info=True)
        return JsonResponse({'status': 'error', 'message': str(e)})

@login_required
def get_user_integrations(request, domain_name):
    try:
        domain = Domain.objects.get(name=domain_name)
        user_integrations = UserIntegration.objects.filter(
            user=request.user,
            integration__domain=domain,
            is_active=True
        ).select_related('integration')
        
        integrations_data = {
            str(ui.integration.id): {
                'name': ui.integration.name,
                'config': ui.config,
                'icon': ui.integration.icon,
                'description': ui.integration.description
            } for ui in user_integrations
        }
        
        return JsonResponse({
            'status': 'success',
            'integrations': integrations_data
        })
    except Domain.DoesNotExist:
        return JsonResponse({
            'status': 'error',
            'message': 'Domaine non trouvé'
        }, status=404)
    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'message': str(e)
        }, status=400)

def compte_view(request):
    if not request.user.is_authenticated:
        return redirect('login')
    
    company_sizes = [
        {'value': '1-10', 'label': '1-10 employés'},
        {'value': '11-50', 'label': '11-50 employés'},
        {'value': '51-200', 'label': '51-200 employés'},
        {'value': '201-500', 'label': '201-500 employés'},
        {'value': '501+', 'label': '501+ employés'}
    ]
    
    context = {
        'user_domains': request.user.domains.all(),
        'all_domains': Domain.objects.all(),
        'user_objectifs': request.user.objectifs.all(),
        'all_objectifs': BusinessObjective.objects.all(),
        'company_sizes': company_sizes,
        'user': request.user
    }
    
    return render(request, 'alyawebapp/compte.html', context)

@login_required
def get_integrations(request, domain_name):
    logger.info(f"Appel de get_integrations pour le domaine: {domain_name}")
    try:
        domain = Domain.objects.get(name=domain_name)
        logger.info(f"Domaine trouvé: {domain.id}")
        
        integrations = Integration.objects.filter(domain=domain)
        logger.info(f"Nombre d'intégrations trouvées: {integrations.count()}")
        
        user_integrations = UserIntegration.objects.filter(
            user=request.user,
            integration__domain=domain
        )
        logger.info(f"Nombre d'intégrations utilisateur trouvées: {user_integrations.count()}")
        
        integrations_data = {}
        for integration in integrations:
            user_integration = user_integrations.filter(integration=integration).first()
            integrations_data[str(integration.id)] = {
                'name': integration.name,
                'icon': integration.icon_class,
                'description': integration.description,
                'config': user_integration.config if user_integration else None
            }
        
        logger.info(f"Données préparées: {len(integrations_data)} intégrations")
        logger.debug(f"Données envoyées: {integrations_data}")
        
        return JsonResponse({
            'status': 'success',
            'integrations': integrations_data
        })
        
    except Exception as e:
        logger.error(f"Erreur dans get_integrations: {str(e)}", exc_info=True)
        return JsonResponse({
            'status': 'error',
            'message': str(e)
        }, status=500)

@login_required
def update_integration_config(request):
    if request.method == 'POST':
        try:
            # Charger les données JSON
            data = json.loads(request.body)
            integration_id = data.get('integration_id')
            
            if not integration_id:
                return JsonResponse({
                    'status': 'error',
                    'message': 'ID de l\'intégration manquant'
                }, status=400)

            integration = Integration.objects.get(id=integration_id)
            
            # Récupérer la configuration des champs pour cette intégration
            config_template = INTEGRATION_CONFIGS.get(integration.name)
            if not config_template:
                return JsonResponse({
                    'status': 'error',
                    'message': f"Configuration non trouvée pour {integration.name}"
                }, status=400)

            # Construire la configuration à partir des données JSON
            config = {}
            for field in config_template['fields']:
                value = data.get(field['name'])
                if field['required'] and not value:
                    return JsonResponse({
                        'status': 'error',
                        'message': f"Champ requis manquant: {field['label']}"
                    }, status=400)
                config[field['name']] = value

            # Met à jour ou crée l'intégration utilisateur
            user_integration, created = UserIntegration.objects.update_or_create(
                user=request.user,
                integration=integration,
                defaults={'config': config}
            )

            return JsonResponse({'status': 'success'})

        except json.JSONDecodeError:
            return JsonResponse({
                'status': 'error',
                'message': 'Format JSON invalide'
            }, status=400)
        except Integration.DoesNotExist:
            return JsonResponse({
                'status': 'error',
                'message': 'Intégration non trouvée'
            }, status=404)
        except Exception as e:
            logger.error(f"Erreur lors de la mise à jour de la configuration: {str(e)}")
            return JsonResponse({
                'status': 'error',
                'message': str(e)
            }, status=500)

    return JsonResponse({
        'status': 'error',
        'message': 'Méthode non autorisée'
    }, status=405)

@login_required
def test_integration(request, integration_id):
    try:
        user_integration = UserIntegration.objects.get(
            id=integration_id,
            user=request.user
        )
        
        success = IntegrationManager.test_integration(
            user_integration.integration.name,
            user_integration.config
        )
        
        return JsonResponse({
            'status': 'success' if success else 'error',
            'message': 'Connexion réussie' if success else 'Échec de la connexion'
        })
    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'message': str(e)
        })

@login_required
def get_integration_config(request, integration_id):
    """Endpoint pour récupérer la configuration d'une intégration"""
    try:
        integration = Integration.objects.get(id=integration_id)
        config_template = INTEGRATION_CONFIGS.get(integration.name, {
            'fields': [],
            'documentation_url': '',
            'auth_type': 'api_key'
        })
        
        # Récupérer la configuration actuelle si elle existe
        current_config = {}
        user_integration = UserIntegration.objects.filter(
            user=request.user,
            integration=integration
        ).first()
        
        if user_integration and user_integration.config:
            current_config = user_integration.config

        return JsonResponse({
            'status': 'success',
            'fields': config_template.get('fields', []),
            'documentation_url': config_template.get('documentation_url', ''),
            'auth_type': config_template.get('auth_type', 'api_key'),
            'current_config': current_config
        })
    except Integration.DoesNotExist:
        return JsonResponse({
            'status': 'error',
            'message': 'Intégration non trouvée'
        }, status=404)
    except Exception as e:
        logger.error(f"Error getting integration config: {str(e)}")
        return JsonResponse({
            'status': 'error',
            'message': 'Erreur lors de la récupération de la configuration'
        }, status=500)

@login_required
def get_user_integrations_state(request):
    try:
        # Récupérer toutes les intégrations activées de l'utilisateur
        user_integrations = UserIntegration.objects.filter(
            user=request.user,
            enabled=True
        ).values_list('integration_id', flat=True)

        # Convertir en liste pour la sérialisation JSON
        enabled_integrations = list(user_integrations)

        logger.info(f"Intégrations activées trouvées: {enabled_integrations}")
        
        return JsonResponse({
            'status': 'success',
            'enabled_integrations': enabled_integrations
        })
    except Exception as e:
        logger.error(f"Erreur lors de la récupération des intégrations: {str(e)}")
        return JsonResponse({
            'status': 'error',
            'message': 'Erreur lors de la récupération des intégrations'
        }, status=500)

@login_required
@require_http_methods(["POST"])
def toggle_integration(request):
    try:
        data = json.loads(request.body)
        integration_id = data.get('integration_id')
        enabled = data.get('enabled', False)
        
        integration = Integration.objects.get(id=integration_id)
        user_integration, created = UserIntegration.objects.get_or_create(
            user=request.user,
            integration=integration,
            defaults={
                'enabled': enabled,
                'config': {}
            }
        )
        
        if not created:
            user_integration.enabled = enabled
            user_integration.save()
        
        return JsonResponse({
            'status': 'success',
            'message': f"Intégration {'activée' if enabled else 'désactivée'} avec succès"
        })
        
    except Exception as e:
        logger.error(f"Erreur dans toggle_integration: {str(e)}")
        return JsonResponse({
            'status': 'error',
            'message': str(e)
        }, status=500)

@login_required
def save_integration_config(request):
    """Endpoint pour sauvegarder la configuration d'une intégration"""
    try:
        if request.method != 'POST':
            return JsonResponse({'status': 'error', 'message': 'Méthode non autorisée'}, status=405)
        
        try:
            data = json.loads(request.body)
        except json.JSONDecodeError:
            return JsonResponse({'status': 'error', 'message': 'Format de données invalide'}, status=400)
        
        integration_id = data.get('integration_id')
        config = data.get('config', {})
        
        if not integration_id:
            return JsonResponse({'status': 'error', 'message': 'ID d\'intégration manquant'}, status=400)
        
        try:
            integration = Integration.objects.get(id=integration_id)
            user_integration, created = UserIntegration.objects.get_or_create(
                user=request.user,
                integration=integration,
                defaults={'config': config, 'enabled': False}
            )
            
            if not created:
                user_integration.config = config
                user_integration.save()
            
            return JsonResponse({
                'status': 'success',
                'message': 'Configuration sauvegardée avec succès'
            })
            
        except Integration.DoesNotExist:
            return JsonResponse({
                'status': 'error',
                'message': 'Intégration non trouvée'
        }, status=404)
            
        except Exception as e:
            logger.error(f"Error saving integration config: {str(e)}")
            return JsonResponse({
                'status': 'error',
                'message': 'Erreur lors de la sauvegarde de la configuration'
            }, status=500)
            
    except Exception as e:
        logger.error(f"Unexpected error in save_integration_config: {str(e)}")
        return JsonResponse({
            'status': 'error',
            'message': 'Une erreur inattendue est survenue'
        }, status=500)

@login_required
def hubspot_oauth(request):
    try:
        # Récupérer l'intégration HubSpot
        integration = Integration.objects.get(name__iexact='hubspot crm')
        
        # Créer ou récupérer l'intégration utilisateur
        user_integration, created = UserIntegration.objects.get_or_create(
            user=request.user,
            integration=integration
        )

        # Configuration OAuth HubSpot
        client_id = settings.HUBSPOT_CLIENT_ID
        redirect_uri = request.build_absolute_uri(reverse('hubspot_callback'))
        # Scopes requis HubSpot
        required_scope = 'oauth'
        
        # Scopes optionnels HubSpot
        optional_scopes = [
            'crm.objects.companies.read',
            'crm.objects.companies.write',
            'crm.objects.contacts.read',
            'crm.objects.contacts.write',
            'crm.objects.leads.read',
            'crm.objects.leads.write'
        ]
        optional_scope = ' '.join(optional_scopes)

        # Construire l'URL d'autorisation
        auth_url = (
            f'https://app.hubspot.com/oauth/authorize'
            f'?client_id={client_id}'
            f'&redirect_uri={redirect_uri}'
            f'&scope={required_scope}'
            f'&optional_scope={optional_scope}'
            f'&state={str(uuid.uuid4())}'  # Ajout d'un state pour la sécurité
        )

        # Sauvegarder l'état de l'intégration
        user_integration.enabled = True
        user_integration.save()
        
        return redirect(auth_url)
        
    except Integration.DoesNotExist:
        logger.error("Erreur OAuth HubSpot: Integration matching query does not exist.")
        messages.error(request, "Configuration de l'intégration HubSpot non trouvée.")
        return redirect('compte')
    except Exception as e:
        logger.error(f"Erreur OAuth HubSpot: {str(e)}")
        messages.error(request, "Une erreur est survenue lors de la configuration de HubSpot.")
        return redirect('compte')

def hubspot_callback(request):
    """Gère le callback OAuth HubSpot"""
    error = request.GET.get('error')
    error_description = request.GET.get('error_description')
    code = request.GET.get('code')
    state = request.GET.get('state')
    
    logger.info(f"HubSpot callback reçu - Params: {request.GET}")
    logger.info(f"Session ID: {request.session.session_key}")
    logger.info(f"Session contents: {dict(request.session)}")
    
    if error:
        logger.error(f"Erreur HubSpot: {error} - {error_description}")
        messages.error(request, f"Erreur HubSpot: {error_description}")
        return redirect('compte')
        
    if not code:
        logger.error("Pas de code d'autorisation reçu")
        messages.error(request, "Autorisation HubSpot échouée")
        return redirect('compte')
    
    try:
        integration = Integration.objects.get(name__iexact='hubspot crm')
        config = {
            'client_id': settings.HUBSPOT_CLIENT_ID,
            'client_secret': settings.HUBSPOT_CLIENT_SECRET,
            'redirect_uri': request.build_absolute_uri(reverse('hubspot_callback'))
        }
        handler = HubSpotHandler(config)
        
        # Échange le code contre des tokens
        logger.info(f"Tentative d'échange du code: {code}")
        tokens = handler.exchange_code_for_tokens(code)
        
        # Récupérer les informations du compte HubSpot
        logger.info("Récupération des informations du compte...")
        account_info = handler.get_account_info(tokens['access_token'])
        logger.info(f"Informations du compte reçues: {account_info}")
        
        # Mettre à jour l'intégration existante avec les tokens OAuth
        user_integration, created = UserIntegration.objects.get_or_create(
            user=request.user,
            integration=integration,
            defaults={'enabled': True}
        )
        
        # Sauvegarder les tokens
        user_integration.access_token = tokens['access_token']
        user_integration.refresh_token = tokens['refresh_token']
        user_integration.token_expires_at = timezone.now() + timedelta(seconds=tokens['expires_in'])
        
        # Garder les informations du compte dans config
        user_integration.config = {
            'portal_id': account_info.get('portalId', 'unknown'),
            'timezone': account_info.get('timeZone', 'UTC'),
            'account_type': account_info.get('accountType', 'unknown')
        }
        
        user_integration.enabled = True
        user_integration.save()
        
        logger.info(f"Intégration sauvegardée pour l'utilisateur {request.user.username}")
        messages.success(request, "Connexion HubSpot réussie")
        
        return redirect('integration_success')
        
    except Exception as e:
        logger.error(f"Erreur lors de la connexion HubSpot: {str(e)}")
        messages.error(request, f"Erreur lors de la connexion HubSpot: {str(e)}")
        return redirect('compte')

@login_required
def chat_view(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            message = data.get('message')
            chat_id = data.get('chat_id')
            
            # Récupérer ou créer une conversation
            if chat_id:
                try:
                    chat = Chat.objects.get(id=chat_id, user=request.user)
                except Chat.DoesNotExist:
                    chat = Chat.objects.create(user=request.user)
            else:
                chat = Chat.objects.create(user=request.user)

            # Sauvegarder le message de l'utilisateur
            ChatHistory.objects.create(
                user=request.user,
                chat=chat,
                content=message,
                is_user=True
            )
            
            # Obtenir la réponse de l'assistant
            orchestrator = AIOrchestrator(user=request.user)
            response = orchestrator.process_message(message)
            
            # Sauvegarder la réponse de l'assistant
            ChatHistory.objects.create(
                user=request.user,
                chat=chat,
                content=response,
                is_user=False
            )
            
            return JsonResponse({
                'status': 'success',
                'response': response,
                'chat_id': chat.id
            })
            
        except Exception as e:
            logger.error(f"Erreur dans le chat: {str(e)}")
            return JsonResponse({
                'status': 'error',
                'message': str(e)
            }, status=500)
    
    return JsonResponse({'status': 'error', 'message': 'Méthode non autorisée'}, status=405)

@login_required
def clear_chat_history(request):
    if request.method == 'POST':
        try:
            Chat.objects.filter(user=request.user).delete()
            return JsonResponse({'status': 'success'})
        except Exception as e:
            logger.error(f"Erreur lors de la suppression de l'historique: {str(e)}")
            return JsonResponse({
                'status': 'error',
                'message': str(e)
            }, status=500)
    
    return JsonResponse({'status': 'error', 'message': 'Méthode non autorisée'}, status=405)

@login_required
def integration_success(request):
    """Vue pour afficher la page de succès après l'intégration"""
    return render(request, 'alyawebapp/integration_success.html')

