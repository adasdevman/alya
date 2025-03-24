from urllib.parse import urlencode
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth import authenticate
from django.contrib.auth import login as auth_login
from django.contrib.auth import logout as auth_logout
from django.contrib import messages
from django.http import HttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_protect, csrf_exempt
from datetime import timedelta
import json
from openai import OpenAI
import logging
import os
from dotenv import load_dotenv
from django.db import transaction
from django.views.decorators.http import require_http_methods
import requests
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
    UserIntegration,
    Message
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
from .integrations.trello.handler import TrelloHandler
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from requests_oauthlib import OAuth2Session

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
@csrf_protect
def login_view(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)
        
        if user is not None:
            auth_login(request, user, backend='django.contrib.auth.backends.ModelBackend')
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
        
        # Récupérer les intégrations activées de l'utilisateur
        user_integrations = UserIntegration.objects.filter(
            user=request.user, 
            enabled=True
        )
        
        # Créer un dictionnaire de configuration des intégrations
        integration_mapping = {
            'HubSpot CRM': 'hubspot',
            'Slack': 'slack',
            'Gmail': 'gmail',
            'Google Drive': 'google_drive',
            'Trello': 'trello',
            'Mailchimp': 'mailchimp'
        }
        
        # Liste des intégrations configurées pour le template
        configured_integrations = []
        
        # Remplir la liste des intégrations configurées
        for ui in user_integrations:
            integration_name = ui.integration.name
            if integration_name in integration_mapping:
                configured_integrations.append(integration_mapping[integration_name])
        
        # Convertir la liste en JSON pour le template
        configured_integrations_json = json.dumps(configured_integrations)
        
        context = {
            'user_domains': user_domains,
            'all_domains': all_domains,
            'user_objectifs': user_objectifs,
            'all_objectifs': all_objectifs,
            'company_sizes': company_sizes,
            'integrations': integrations,
            'integration_configs_data': integration_configs_json,
            'user_integrations': configured_integrations_json,
            'trello_api_key': 'dfdd546608d5f4cbfe3b417f6cba8204',  # Pour déboguer
            'trello_redirect_uri': settings.TRELLO_REDIRECT_URI
        }
        
        # Déboguer les valeurs
        print(f"Trello API Key in context: {context['trello_api_key']}")
        logger.info(f"Intégrations configurées: {configured_integrations}")
        
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
def chat_view(request):
    try:
        data = json.loads(request.body)
        message = data.get('message')
        chat_id = data.get('chat_id')
        
        # Créer ou récupérer le chat existant
        chat = Chat.objects.get_or_create(
            id=chat_id,
            user=request.user
        )[0]
        
        # Sauvegarder le message de l'utilisateur
        Message.objects.create(
            chat=chat,
            content=message,
            is_user=True
        )
        
        # Traitement par l'IA
        orchestrator = AIOrchestrator(user=request.user)
        response = orchestrator.process_message(chat_id, message)
        
        # Sauvegarder la réponse de l'IA
        Message.objects.create(
            chat=chat,
            content=response,
            is_user=False
        )
        
        return JsonResponse({
            'status': 'success',
            'response': response
        })
    except Exception as e:
        logger.error(f"Erreur dans le chat: {str(e)}")
        return JsonResponse({
            'status': 'error',
            'message': str(e)
        }, status=500)

@login_required
def get_chat_history(request):
    try:
        # Récupérer les chats avec au moins un message
        chats = Chat.objects.filter(
            user=request.user,
            messages__isnull=False
        ).distinct()
        
        # Créer un dictionnaire pour stocker les conversations uniques
        unique_chats = {}
        
        for chat in chats:
            if chat.id not in unique_chats:
                messages = Message.objects.filter(chat=chat).order_by('created_at')
                if messages.exists():
                    # Trouver le premier message utilisateur
                    first_user_message = messages.filter(is_user=True).first()
                    # Trouver la dernière réponse
                    last_response = messages.filter(is_user=False).last()
                    
                    unique_chats[chat.id] = {
                        'id': chat.id,
                        'title': first_user_message.content if first_user_message else "Nouvelle conversation",
                        'preview': last_response.content[:100] if last_response else "",
                        'created_at': chat.created_at.strftime('%Y-%m-%d %H:%M:%S'),
                        'message_pairs': messages.count() // 2  # Nombre de paires question/réponse
                    }
        
        # Convertir le dictionnaire en liste pour la réponse
        chat_history = list(unique_chats.values())
        
        return JsonResponse({
            'status': 'success',
            'chats': chat_history
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
        chat = Chat.objects.get(id=chat_id, user_id=request.user.id)
        messages = chat.messages.all().order_by('created_at')
        
        return JsonResponse({
            'status': 'success',
            'messages': [{
                'content': msg.content,
                'is_user': msg.is_user,
                'timestamp': msg.created_at.isoformat()
            } for msg in messages]
        })
    except Chat.DoesNotExist:
        return JsonResponse({
            'status': 'error',
            'message': 'Conversation not found'
        })

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
    
    try:
        # Définir les tailles d'entreprise disponibles
        company_sizes = [
            {'value': '1-10', 'label': '1-10 employés'},
            {'value': '11-50', 'label': '11-50 employés'},
            {'value': '51-200', 'label': '51-200 employés'},
            {'value': '201-500', 'label': '201-500 employés'},
            {'value': '501+', 'label': '501+ employés'}
        ]
        
        # Récupérer toutes les intégrations de l'utilisateur
        user_integrations = UserIntegration.objects.filter(
            user=request.user,
            enabled=True
        ).select_related('integration')
        
        # Debug: afficher les intégrations trouvées
        logger.info("Intégrations actives trouvées:")
        for ui in user_integrations:
            logger.info(f"- {ui.integration.name}")
        
        # Créer un dictionnaire des intégrations configurées
        configured_integrations = {}
        
        # Mapper les noms d'intégration aux clés du template
        integration_mapping = {
            'HubSpot CRM': 'hubspot',
            'Slack': 'slack',
            'Gmail': 'gmail',
            'Google Drive': 'google_drive',
            'Mailchimp': 'mailchimp'
        }
        
        # Remplir le dictionnaire des intégrations configurées
        for ui in user_integrations:
            for db_name, template_key in integration_mapping.items():
                if ui.integration.name == db_name:
                    configured_integrations[template_key] = True
                    break
        
        logger.info(f"État des intégrations: {configured_integrations}")
        
        context = {
            'user_domains': request.user.domains.all(),
            'all_domains': Domain.objects.all(),
            'user_objectifs': request.user.objectifs.all(),
            'all_objectifs': BusinessObjective.objects.all(),
            'company_sizes': company_sizes,
            'user': request.user,
            'configured_integrations': json.dumps(configured_integrations),
        }
        
        return render(request, 'alyawebapp/compte.html', context)
    except Exception as e:
        logger.error(f"FATAL COMPTE ERROR: {str(e)}")
        return redirect('home')

@login_required
def get_integrations(request, domain_name):
    """Récupère les intégrations disponibles pour un domaine"""
    try:
        # Filtrer les intégrations par domaine
        integrations = Integration.objects.filter(domain__name=domain_name)
        # Exclure Mailchimp car il est déjà affiché en haut du modal
        integrations = integrations.exclude(name__icontains='mailchimp')
        
        # Récupérer les intégrations actives de l'utilisateur
        user_integrations = UserIntegration.objects.filter(
            user=request.user,
            integration__in=integrations,
            enabled=True
        ).values_list('integration_id', flat=True)

        # Formater les données
        data = {
            'integrations': [
                {
                    'id': integration.id,
                    'name': integration.name,
                    'description': integration.description,
                    'icon_class': integration.icon_class,
                    'is_active': integration.id in user_integrations
                }
                for integration in integrations
            ]
        }
        return JsonResponse(data)
    except Exception as e:
        logger.error(f"Erreur lors de la récupération des intégrations: {str(e)}")
        return JsonResponse({'error': str(e)}, status=500)

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
    """Récupère l'état des intégrations de l'utilisateur"""
    try:
        # Récupérer les intégrations actives de l'utilisateur
        user_integrations = UserIntegration.objects.filter(
            user=request.user,
            enabled=True
        ).select_related('integration')

        # Créer un dictionnaire des états
        integration_states = {
            'mailchimp': False,
            'slack': False,
            'gmail': False,
            'google_drive': False,
            'hubspot': False,
            'trello': False
        }

        # Mettre à jour les états en fonction des intégrations trouvées
        for ui in user_integrations:
            if 'mailchimp' in ui.integration.name.lower():
                integration_states['mailchimp'] = True
            elif 'slack' in ui.integration.name.lower():
                integration_states['slack'] = True
            elif 'gmail' in ui.integration.name.lower():
                integration_states['gmail'] = True
            elif 'google drive' in ui.integration.name.lower():
                integration_states['google_drive'] = True
            elif 'hubspot' in ui.integration.name.lower():
                integration_states['hubspot'] = True
            elif 'trello' in ui.integration.name.lower() or 'gestion de projet' in ui.integration.name.lower():
                integration_states['trello'] = True

        # Ajout d'un log pour déboguer
        logger.info(f"États des intégrations: {integration_states}")
        logger.info(f"Intégrations trouvées: {[ui.integration.name for ui in user_integrations]}")

        return JsonResponse(integration_states)
    except Exception as e:
        logger.error(f"Erreur lors de la récupération des états des intégrations: {str(e)}")
        return JsonResponse({'error': str(e)}, status=500)

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
    """Page de succès après configuration d'une intégration"""
    messages.success(request, "L'intégration a été configurée avec succès!")
    return redirect('compte')

def handle_chat_request(request):
    if request.method == 'POST':
        chat_id = request.POST.get('chat_id')
        message_content = request.POST.get('message')

        if not message_content:
            return JsonResponse({'error': 'Le message ne peut pas être vide.'}, status=400)

        orchestrator = AIOrchestrator(user=request.user)
        try:
            orchestrator.process_message(chat_id, message_content)
            return JsonResponse({'status': 'success'})
        except ValueError as e:
            return JsonResponse({'error': str(e)}, status=400)
        except Exception as e:
            logger.error(f"Erreur lors du traitement du message: {e}")
            return JsonResponse({'error': 'Erreur interne du serveur.'}, status=500)

@login_required
def get_messages(request, chat_id):
    try:
        chat = Chat.objects.get(id=chat_id, user=request.user)
        messages = Message.objects.filter(chat=chat).order_by('created_at')
        
        message_list = [{
            'content': msg.content,
            'is_user': msg.is_user,
            'created_at': msg.created_at.strftime('%Y-%m-%d %H:%M:%S')
        } for msg in messages]
        
        return JsonResponse({
            'status': 'success',
            'messages': message_list
        })
    except Exception as e:
        logger.error(f"Erreur lors de la récupération des messages: {str(e)}")
        return JsonResponse({
            'status': 'error',
            'message': str(e)
        }, status=500)

def get_hubspot_auth_url(request):
    config = {
        'client_id': settings.HUBSPOT_CLIENT_ID,
        'client_secret': settings.HUBSPOT_CLIENT_SECRET,
        'redirect_uri': settings.HUBSPOT_REDIRECT_URI
    }
    handler = HubSpotHandler(config)
    auth_url = handler.get_authorization_url()
    return redirect(auth_url)

@login_required
def trello_oauth(request):
    try:
        integration = Integration.objects.get(name__iexact='trello')
        user_integration, created = UserIntegration.objects.get_or_create(
            user=request.user,
            integration=integration
        )

        handler = TrelloHandler({
            'api_key': settings.TRELLO_API_KEY,
            'api_secret': settings.TRELLO_API_SECRET,
            'redirect_uri': settings.TRELLO_REDIRECT_URI
        })

        auth_url = handler.get_authorization_url()
        return redirect(auth_url)

    except Exception as e:
        logger.error(f"Erreur OAuth Trello: {str(e)}")
        messages.error(request, "Une erreur est survenue lors de la configuration de Trello.")
        return redirect('compte')

@login_required
def trello_callback(request):
    return render(request, 'alyawebapp/trello_callback.html')

@login_required
@csrf_protect
def trello_save_token(request):
    try:
        data = json.loads(request.body)
        token = data.get('token')
        
        if not token:
            return JsonResponse({'success': False, 'error': 'Token manquant'})

        integration = Integration.objects.get(name__iexact='trello')
        user_integration, created = UserIntegration.objects.get_or_create(
            user=request.user,
            integration=integration
        )

        user_integration.access_token = token
        user_integration.enabled = True
        user_integration.save()

        return JsonResponse({'success': True})

    except Exception as e:
        logger.error(f"Erreur sauvegarde token Trello: {str(e)}")
        return JsonResponse({'success': False, 'error': str(e)})

# INTEGRATION slack
def slack_oauth(request):
    slack_auth_url = "https://slack.com/oauth/v2/authorize"
    # ssl_link = os.getenv('SLACK_REDIRECT_URI')

    redirect_uri = os.getenv('SLACK_REDIRECT_URI')
    params = {
        "client_id": os.getenv("SLACK_CLIENT_ID"),
        "scope": "users:read",  # Ajustez en fonction de vos besoins
        "redirect_uri": redirect_uri,
    }
    return redirect(f"{slack_auth_url}?{urlencode(params)}")

@login_required
def slack_callback(request):
    code = request.GET.get('code')
    if not code:
        return JsonResponse({'error': 'Code manquant'})

    # Échanger le code contre un token
    response = requests.post('https://slack.com/api/oauth.v2.access', data={
        'client_id': os.getenv('SLACK_CLIENT_ID'),
        'client_secret': os.getenv('SLACK_CLIENT_SECRET'),
        'code': code,
        'redirect_uri': os.getenv('SLACK_REDIRECT_URI')
    })
    
    data = response.json()
    
    if data.get('ok'):
        try:
            integration = Integration.objects.get(name__icontains='slack')
            user_integration, created = UserIntegration.objects.get_or_create(
                user=request.user,
                integration=integration,
                defaults={'enabled': True}
            )
            user_integration.access_token = data['access_token']
            user_integration.config = {
                'team_id': data.get('team', {}).get('id'),
                'team_name': data.get('team', {}).get('name')
            }
            user_integration.save()
            return redirect('integration_success', integration_name='Slack')
        except Exception as e:
            logger.error(f"Erreur lors de la sauvegarde du token Slack: {str(e)}")
            return render(request, 'alyawebapp/integration_error.html', {
                'integration_name': 'Slack',
                'error_message': str(e)
            })
    else:
        return JsonResponse({'error': data.get('error', 'Unknown error')})


# INTEGRATION GMAIL
def gmail_oauth(request):
    # Lire les informations du client depuis le .env
    client_id = os.getenv('GOOGLE_CLIENT_ID')
    client_secret = os.getenv('GOOGLE_CLIENT_SECRET')

    redirect_uri = os.getenv('GOOGLE_REDIRECT_URI')

    flow = Flow.from_client_config({
        "web": {
            "client_id": client_id,
            "client_secret": client_secret,
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "redirect_uris": [redirect_uri]
        }
    }, scopes=['https://www.googleapis.com/auth/gmail.readonly'])

    flow.redirect_uri = redirect_uri

    authorization_url, state = flow.authorization_url(
        access_type='offline',
        include_granted_scopes='true'
    )

    # Sauvegarder l'état de la requête pour vérification plus tard
    request.session['state'] = state

    return redirect(authorization_url)

@login_required
def gmail_callback(request):
    try:
        # Récupérer l'intégration Gmail
        integration = Integration.objects.get(name__iexact='Gmail')
        
        state = request.session['state']
        code = request.GET.get('code')

        if not code:
            logger.error("No authorization code received from Gmail")
            messages.error(request, "Erreur lors de l'authentification Gmail")
            return redirect('compte')

        client_id = os.getenv('GOOGLE_CLIENT_ID')
        client_secret = os.getenv('GOOGLE_CLIENT_SECRET')
        redirect_uri = os.getenv('GOOGLE_REDIRECT_URI')

        flow = Flow.from_client_config({
            "web": {
                "client_id": client_id,
                "client_secret": client_secret,
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "redirect_uris": [redirect_uri]
            }
        }, scopes=['https://www.googleapis.com/auth/gmail.readonly'], state=state)

        flow.redirect_uri = redirect_uri

        # Construire l'URL complète avec HTTPS
        url = request.build_absolute_uri()
        if not url.startswith("https://"):
            url = url.replace("http://", "https://")

        # Échanger le code d'autorisation contre des jetons
        flow.fetch_token(authorization_response=url)
        credentials = flow.credentials

        # Créer ou mettre à jour l'intégration utilisateur
        user_integration, created = UserIntegration.objects.get_or_create(
            user=request.user,
            integration=integration,
            defaults={'enabled': True}
        )

        # Mettre à jour les tokens
        user_integration.access_token = credentials.token
        user_integration.config = {
            'refresh_token': credentials.refresh_token,
            'token_uri': credentials.token_uri,
            'client_id': credentials.client_id,
            'client_secret': credentials.client_secret,
            'scopes': credentials.scopes
        }
        user_integration.enabled = True
        user_integration.save()

        messages.success(request, "Gmail a été configuré avec succès!")
        return redirect('compte')

    except Integration.DoesNotExist:
        logger.error("Gmail integration not found in database")
        messages.error(request, "Configuration Gmail non trouvée")
        return redirect('compte')
    except Exception as e:
        logger.error(f"Error in Gmail callback: {str(e)}")
        messages.error(request, f"Erreur lors de la configuration de Gmail: {str(e)}")
        return redirect('compte')

# INTEGRATION GOOGLE DRIVE
SCOPES = ['https://www.googleapis.com/auth/drive.file']

def google_drive_oauth(request):
    # Reconstituer les informations d'identification à partir des variables d'environnement
    client_config = {
        "web": {  # Utilisation de 'web' au lieu de 'installed' si vous configurez une application web
            "client_id": os.getenv('GOOGLE_CLIENT_DRIVE_ID'),
            "client_secret": os.getenv('GOOGLE_CLIENT_DRIVE_SECRET'),
            "redirect_uris": [os.getenv('GOOGLE_REDIRECT_DRIVE_URI')],
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token"
        }
    }

    # Créer le flux d'authentification
    flow = Flow.from_client_config(client_config, SCOPES, redirect_uri = os.getenv('GOOGLE_REDIRECT_DRIVE_URI'))

    # Définir explicitement l'URI de redirection dans le flux
    # flow.redirect_uri = os.getenv('GOOGLE_REDIRECT_DRIVE_URI')
    
    # Générer l'URL d'autorisation et rediriger l'utilisateur
    auth_url, state = flow.authorization_url(access_type='offline', include_granted_scopes='true')
    request.session['state'] = state
    return redirect(auth_url)

@login_required
def google_drive_callback(request):
    code = request.GET.get('code')
    state = request.session['state']

    if not code:
        return HttpResponse("Error: Missing authorization code.", status=400)
    flow = Flow.from_client_config(
        {
            "web": {
                "client_id": os.getenv('GOOGLE_CLIENT_DRIVE_ID'),
                "client_secret": os.getenv('GOOGLE_CLIENT_DRIVE_SECRET'),
                "redirect_uris": [os.getenv('GOOGLE_REDIRECT_DRIVE_URI')],
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
            }
        },
        SCOPES,
        state=state,
        redirect_uri = os.getenv('GOOGLE_REDIRECT_DRIVE_URI')
    )

    url = request.build_absolute_uri()
    if not url.startswith("https://"):
        url = url.replace("http://", "https://")

    
    # Récupérer le token d'authentification
    credentials = flow.fetch_token(authorization_response=url, client_secret=os.getenv('GOOGLE_CLIENT_DRIVE_SECRET'))
    
    try:
        integration = Integration.objects.get(name__icontains='google drive')
        user_integration, created = UserIntegration.objects.get_or_create(
            user=request.user,
            integration=integration,
            defaults={'enabled': True}
        )
        user_integration.access_token = credentials.token
        user_integration.config = {
            'refresh_token': credentials.refresh_token,
            'token_uri': credentials.token_uri,
            'expiry': credentials.expiry.isoformat() if credentials.expiry else None
        }
        user_integration.save()
        return redirect('integration_success', integration_name='Google Drive')
    except Exception as e:
        logger.error(f"Erreur lors de la sauvegarde des credentials Google Drive: {str(e)}")
        return render(request, 'alyawebapp/integration_error.html', {
            'integration_name': 'Google Drive',
            'error_message': str(e)
        })
   
# ssh -R yourcustomsubdomain:80:localhost:8000 serveo.net
# INTEGRATION MAILCHIMP
def mailchimp_oauth(request):
    """Redirige vers l'authentification Mailchimp"""
    logger.info(f"MAILCHIMP_CLIENT_ID: {settings.MAILCHIMP_CLIENT_ID}")
    logger.info(f"MAILCHIMP_REDIRECT_URI: {settings.MAILCHIMP_REDIRECT_URI}")
    
    if not settings.MAILCHIMP_CLIENT_ID or not settings.MAILCHIMP_REDIRECT_URI:
        logger.error("Configuration Mailchimp manquante!")
        return JsonResponse({
            'error': 'Configuration Mailchimp incomplète',
            'client_id': settings.MAILCHIMP_CLIENT_ID,
            'redirect_uri': settings.MAILCHIMP_REDIRECT_URI
        })

    query_params = {
        "response_type": "code",
        "client_id": settings.MAILCHIMP_CLIENT_ID,
        "redirect_uri": settings.MAILCHIMP_REDIRECT_URI,
    }
    
    auth_url = settings.MAILCHIMP_AUTHORIZATION_URL + "?" + urlencode(query_params)
    logger.info(f"URL d'authentification Mailchimp: {auth_url}")
    return redirect(auth_url)

# Step 2: Handle callback and exchange code for token
def mailchimp_callback(request):
    code = request.GET.get('code')
    if not code:
        return JsonResponse({'error': 'Aucun code fournit par Mailchimp'})

    # Exchange authorization code for access token
    token_data = {
        'grant_type': 'authorization_code',
        'client_id': settings.MAILCHIMP_CLIENT_ID,
        'client_secret': settings.MAILCHIMP_CLIENT_SECRET,
        'redirect_uri': settings.MAILCHIMP_REDIRECT_URI,
        'code': code,
    }
    response = requests.post(settings.MAILCHIMP_TOKEN_URL, data=token_data)
    token_json = response.json()

    if 'access_token' in token_json:
        # Save the token or user details as per your requirement
        access_token = token_json['access_token']

        # Now you can use the access token to make Mailchimp API requests
        # Example: Get the authenticated account details
        account_url = "https://login.mailchimp.com/oauth2/metadata"
        headers = {
            "Authorization": f"Bearer {access_token}"
        }
        account_response = requests.get(account_url, headers=headers)
        account_data = account_response.json()

        # Sauvegarder le token dans UserIntegration
        try:
            integration = Integration.objects.get(name__icontains='mailchimp')
            user_integration, created = UserIntegration.objects.get_or_create(
                user=request.user,
                integration=integration,
                defaults={'enabled': True}
            )
            user_integration.access_token = access_token
            user_integration.save()
            
            # Ajoutons un log pour confirmer la sauvegarde
            logger.info(f"Integration {integration.name} configurée pour l'utilisateur {request.user.username}")
            
            return redirect('integration_success', integration_name='Mailchimp')
        except Exception as e:
            logger.error(f"Erreur lors de la sauvegarde du token Mailchimp: {str(e)}")
            return render(request, 'alyawebapp/integration_error.html', {
                'integration_name': 'Mailchimp',
                'error_message': str(e)
            })
    else:
        return JsonResponse({'error': 'Failed to obtain access token'})

def integration_success_view(request, integration_name):
    """Page de succès après configuration d'une intégration"""
    return render(request, 'alyawebapp/integration_success.html', {
        'integration_name': integration_name
    })