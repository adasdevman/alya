from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth import authenticate
from django.contrib.auth import login as auth_login
from django.contrib.auth import logout as auth_logout
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_protect, csrf_exempt
from datetime import datetime
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
from .utils.openai_utils import call_openai_api

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

def register(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        email = request.POST.get('email')
        password = request.POST.get('password')
        confirm_password = request.POST.get('confirm_password')

        if password != confirm_password:
            messages.error(request, 'Les mots de passe ne correspondent pas.')
            return redirect('register')

        if CustomUser.objects.filter(username=username).exists():
            messages.error(request, 'Ce nom d\'utilisateur est déjà pris.')
            return redirect('register')

        if CustomUser.objects.filter(email=email).exists():
            messages.error(request, 'Cet email est déjà utilisé.')
            return redirect('register')

        try:
            # Créer l'utilisateur
            user = CustomUser.objects.create_user(
                username=username,
                email=email,
                password=password
            )

            # Utiliser get_or_create pour éviter les doublons
            profile, created = UserProfile.objects.get_or_create(
                user=user,
                defaults={
                    # Vous pouvez ajouter des valeurs par défaut ici si nécessaire
                }
            )

            auth_login(request, user)
            messages.success(request, 'Compte créé avec succès!')
            return redirect('onboarding')

        except Exception as e:
            # Log de l'erreur pour le débogage
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
        context = {
            'user_domains': profile.domains.all(),
            'all_domains': Domain.objects.all(),
            'user_objectifs': profile.business_objectives.all(),
            'all_objectifs': BusinessObjective.objects.all(),
            'company_sizes': CompanySize.objects.all(),
            'integrations': Integration.objects.all(),
            'integration_configs': json.dumps(INTEGRATION_CONFIGS)
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

@csrf_exempt
@login_required
def chat_view(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            prompt = data.get('prompt')
            chat_id = data.get('chat_id')

            if not prompt:
                return JsonResponse({
                    'status': 'error',
                    'message': 'Prompt manquant'
                }, status=400)

            # Créer ou récupérer le chat
            if chat_id:
                chat = Chat.objects.get(id=chat_id, user=request.user)
            else:
                chat = Chat.objects.create(user=request.user)

            # Récupérer l'historique du chat
            chat_history = []
            previous_prompts = Prompt.objects.filter(chat=chat).order_by('created_at')
            for p in previous_prompts:
                chat_history.extend([
                    {'content': p.question, 'is_user': True},
                    {'content': p.response, 'is_user': False}
                ])

            # Récupérer les intégrations disponibles pour l'utilisateur
            try:
                available_integrations = IntegrationManager.get_available_integrations(request.user.id)
            except Exception as e:
                logger.error(f"Erreur lors de la récupération des intégrations: {str(e)}")
                available_integrations = {}
                
            # Ajouter les intégrations disponibles et l'historique au contexte
            context = {
                "available_integrations": list(available_integrations.keys()),
                "user_prompt": prompt,
                "chat_history": chat_history
            }

            # Appeler l'API OpenAI avec le contexte enrichi
            response = call_openai_api(prompt, context)

            # Si la réponse contient une action d'intégration
            if 'integration_action' in response:
                action = response['integration_action']
                integration_name = action.get('integration')
                method_name = action.get('method')
                params = action.get('params', {})

                if integration_name and method_name:
                    # Récupérer le vrai nom de l'intégration (avec la casse correcte)
                    real_integration_name = available_integrations.get(integration_name.lower())
                    if real_integration_name:
                        # Exécuter l'action d'intégration
                        result = IntegrationManager.execute_integration_action(
                            integration_name=real_integration_name,
                            user_id=request.user.id,
                            action=method_name,
                            **params
                        )

                        # Ajouter le résultat à la réponse
                        if result['status'] == 'success':
                            response['message'] += f"\n\nAction effectuée avec succès : {result.get('data', '')}"
                        else:
                            response['message'] += f"\n\nErreur lors de l'action : {result.get('message', '')}"
                    else:
                        response['message'] += f"\n\nErreur : Intégration {integration_name} non disponible"

            # Sauvegarder l'échange dans l'historique
            Prompt.objects.create(
                user=request.user,
                chat=chat,
                question=prompt,
                response=response['message']
            )

            return JsonResponse({
                'status': 'success',
                'message': response['message'],
                'chat_id': chat.id
            })

        except json.JSONDecodeError:
            return JsonResponse({
                'status': 'error',
                'message': 'Format JSON invalide'
            }, status=400)
        except Exception as e:
            logger.error(f"Erreur lors du traitement du chat: {str(e)}")
            return JsonResponse({
                'status': 'error',
                'message': str(e)
            }, status=500)

    return JsonResponse({
        'status': 'error',
        'message': 'Méthode non autorisée'
    }, status=405)

@login_required
def chat_history(request):
    try:
        # Récupérer toutes les sessions de chat de l'utilisateur
        chats = Chat.objects.filter(user=request.user).order_by('-created_at')
        
        chat_list = []
        for chat in chats:
            # Récupérer les messages de cette session
            prompts = Prompt.objects.filter(chat=chat).order_by('created_at')
            messages = []
            for prompt in prompts:
                messages.append({
                    'prompt': prompt.question,
                    'response': prompt.response,
                    'timestamp': prompt.created_at.isoformat()
                })
            
            if messages:  # N'ajouter que les chats qui ont des messages
                chat_list.append({
                    'id': chat.id,
                    'created_at': chat.created_at.isoformat(),
                    'messages': messages,
                    'preview': messages[0]['prompt'][:50] + '...' if len(messages[0]['prompt']) > 50 else messages[0]['prompt']
                })
        
        return JsonResponse({
            'status': 'success',
            'chats': chat_list
        })
    except Exception as e:
        logger.error(f"CHAT HISTORY ERROR: {str(e)}")
        return JsonResponse({
            'status': 'error',
            'message': str(e)
        }, status=500)

@login_required
def get_conversation(request, chat_id):
    try:
        # Vérifier que le chat appartient à l'utilisateur
        chat = Chat.objects.get(id=chat_id, user=request.user)
        
        # Récupérer tous les messages de la conversation
        prompts = Prompt.objects.filter(chat=chat).order_by('created_at')
        
        # Formater les messages pour le front-end
        messages = []
        for prompt in prompts:
            messages.append({
                'content': prompt.question,
                'is_user': True
            })
            if prompt.response:
                messages.append({
                    'content': prompt.response,
                    'is_user': False
                })
        
        return JsonResponse({
            'status': 'success',
            'messages': messages
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
            'message': 'Erreur lors de la récupération de la conversation'
        }, status=500)

@login_required
def get_chat_history(request):
    try:
        # Récupérer l'historique des conversations pour l'utilisateur connecté
        recent_chats = ChatHistory.objects.filter(user=request.user).order_by('-created_at')[:10]
        
        conversations = []
        for chat in recent_chats:
            conversations.append({
                'id': str(chat.id),  # Convertir en string pour le JSON
                'created_at': chat.created_at.isoformat(),
                'first_message': chat.prompt[:50],  # Limiter à 50 caractères
                'messages': [
                    {
                        'content': chat.prompt,
                        'is_user': True
                    },
                    {
                        'content': chat.response,
                        'is_user': False
                    } if chat.response else None
                ]
            })
        
        return JsonResponse({
            'status': 'success',
            'conversations': conversations
        })
    except Exception as e:
        logger.error(f"Erreur lors de la récupération de l'historique: {str(e)}")
        return JsonResponse({
            'status': 'error',
            'message': 'Erreur lors de la récupération de l\'historique'
        }, status=500)

@login_required
def update_company_size(request):
    if request.method == 'POST':
        try:
            company_size = request.POST.get('company_size')
            if company_size:
                request.user.company_size = company_size
                request.user.save()
                return JsonResponse({
                    'status': 'success',
                    'message': 'Taille de l\'entreprise mise à jour avec succès!'
                })
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
            profile = UserProfile.objects.get(user=request.user)
            selected_domain_ids = request.POST.getlist('domains')
            
            # Nettoyer les domaines existants
            profile.domains.clear()
            
            if selected_domain_ids:
                domains_to_add = Domain.objects.filter(id__in=selected_domain_ids)
                profile.domains.add(*domains_to_add)
                
                return JsonResponse({
                    'status': 'success',
                    'message': 'Secteurs d\'activité mis à jour avec succès!'
                })
            
            return JsonResponse({
                'status': 'error',
                'message': 'Veuillez sélectionner au moins un secteur d\'activité.'
            })
            
        except Exception as e:
            logger.error(f"ERREUR DE MISE À JOUR DES DOMAINES: {str(e)}")
            return JsonResponse({
                'status': 'error',
                'message': 'Une erreur est survenue lors de la mise à jour.'
            })
    return JsonResponse({'status': 'error', 'message': 'Méthode non autorisée'})

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
def get_integrations_state(request):
    """Endpoint pour récupérer l'état de toutes les intégrations de l'utilisateur"""
    try:
        user_integrations = UserIntegration.objects.filter(user=request.user)
        integrations_state = [{
            'id': ui.integration.id,
            'enabled': ui.enabled
        } for ui in user_integrations]
        
        return JsonResponse({
            'status': 'success',
            'integrations': integrations_state
        })
    except Exception as e:
        logger.error(f"Erreur lors de la récupération des états des intégrations: {str(e)}")
        return JsonResponse({
            'status': 'error',
            'message': 'Erreur lors de la récupération des états des intégrations'
        }, status=500)

@login_required
def toggle_integration(request):
    """Endpoint pour activer/désactiver une intégration"""
    try:
        logger.info(f"Toggle integration request received - Method: {request.method}")
        logger.info(f"Request body: {request.body.decode()}")
        
        if request.method != 'POST':
            return JsonResponse({'status': 'error', 'message': 'Méthode non autorisée'}, status=405)
        
        try:
            data = json.loads(request.body)
        except json.JSONDecodeError as e:
            logger.error(f"JSON decode error: {str(e)}")
            return JsonResponse({'status': 'error', 'message': 'Format de données invalide'}, status=400)
        
        integration_id = data.get('integration_id')
        enabled = data.get('enabled', False)
        
        logger.info(f"Received data - ID: {integration_id}, Enabled: {enabled}")
        
        if integration_id is None:
            return JsonResponse({'status': 'error', 'message': 'ID d\'intégration manquant'}, status=400)
        
        try:
            integration_id = int(integration_id)
        except (ValueError, TypeError):
            logger.error(f"Invalid integration ID: {integration_id}")
            return JsonResponse({'status': 'error', 'message': 'ID d\'intégration invalide'}, status=400)
        
        try:
            integration = Integration.objects.get(id=integration_id)
            logger.info(f"Integration found: {integration.name}")
            
            # Configuration par défaut si manquante
            config_template = INTEGRATION_CONFIGS.get(integration.name, {
                'fields': [],
                'optional_config': True
            })
            
            with transaction.atomic():
                try:
                    user_integration = UserIntegration.objects.get(
                        user=request.user,
                        integration=integration
                    )
                    exists = True
                except UserIntegration.DoesNotExist:
                    user_integration = UserIntegration(
                        user=request.user,
                        integration=integration,
                        enabled=enabled,
                        config={}
                    )
                    exists = False
                
                if exists:
                    # Si l'intégration existe déjà
                    if user_integration.config is None:
                        user_integration.config = {}
                    
                    # Vérifier la configuration uniquement lors de l'activation
                    if enabled:
                        # Si la configuration n'est pas optionnelle
                        if not config_template.get('optional_config', True):
                            required_fields = [
                                field['name'] for field in config_template.get('fields', [])
                                if field.get('required', False)
                            ]
                            missing_fields = [
                                field for field in required_fields 
                                if not user_integration.config.get(field)
                            ]
                            if missing_fields:
                                missing_field_labels = [
                                    next(f['label'] for f in config_template['fields'] if f['name'] == field)
                                    for field in missing_fields
                                ]
                                return JsonResponse({
                                    'status': 'warning',
                                    'message': f'Configuration requise : {", ".join(missing_field_labels)}',
                                    'needs_config': True,
                                    'missing_fields': missing_field_labels
                                }, status=200)
                
                # Mettre à jour l'état
                user_integration.enabled = enabled
                
                # Sauvegarder avec skip_validation si on désactive
                user_integration.save(skip_validation=not enabled)
                logger.info(f"Integration {'enabled' if enabled else 'disabled'} successfully")
            
            return JsonResponse({
                'status': 'success',
                'message': 'État de l\'intégration mis à jour avec succès'
            })
            
        except Integration.DoesNotExist:
            logger.error(f"Integration not found with ID: {integration_id}")
            return JsonResponse({'status': 'error', 'message': 'Intégration non trouvée'}, status=404)
            
        except ValidationError as e:
            logger.error(f"Validation error: {str(e)}")
            # Si c'est une désactivation, on ignore la validation
            if not enabled:
                user_integration.save(skip_validation=True)
                return JsonResponse({
                    'status': 'success',
                    'message': 'Intégration désactivée avec succès'
                })
            return JsonResponse({
                'status': 'warning',
                'message': str(e),
                'needs_config': True
            }, status=200)
            
        except Exception as e:
            logger.error(f"Database error: {str(e)}")
            return JsonResponse({'status': 'error', 'message': 'Erreur lors de la mise à jour'}, status=500)
            
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        return JsonResponse({'status': 'error', 'message': 'Une erreur est survenue'}, status=500)

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

