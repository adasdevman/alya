import logging
import json
import requests
import re
from datetime import datetime, timedelta, timezone
from ..exceptions import NetworkError

logger = logging.getLogger(__name__)

class TrelloHandler:
    """Gestionnaire pour les intégrations Trello"""
    
    def __init__(self, orchestrator):
        self.orchestrator = orchestrator
        self.user = orchestrator.user
        self.openai_client = orchestrator.openai_client
        self.trello_integration = None
        self.task_info = {}
        self.available_members = []
        self.members_data = []
        self.available_lists = []
        self._initialize()
    
    def _initialize(self):
        """Initialise l'intégration Trello si elle existe"""
        from alyawebapp.models import Integration, UserIntegration
        
        try:
            integration = Integration.objects.get(name__iexact='trello')
            self.trello_integration = UserIntegration.objects.get(
                user=self.user,
                integration=integration,
                enabled=True
            )
        except (Integration.DoesNotExist, UserIntegration.DoesNotExist):
            self.trello_integration = None
    
    def handle_request(self, message):
        """Gère les requêtes Trello"""
        from django.conf import settings
        from ..utils.retry_handler import RetryHandler
        
        try:
            # Ajouter des logs détaillés pour le diagnostic
            logger.info(f"[TRELLO] Début du traitement de la requête: '{message}'")
            
            # Détection spécifique pour les cas problématiques (Marie, franck adas, etc.)
            assignee_patterns = [
                # Pattern spécifique pour les noms composés (priorité)
                r"assign[eé][^a-zA-Z]*(?:la\s+)?[àa]\s+([A-Za-z]+(?:\s+[A-Za-z]+){0,2})(?:\.\s+|\.$|$)",
                r"assign[eé][^a-zA-Z]*(?:la\s+)?[àa]\s+([^\.]+?)(?:\.\s+|\.$|$)"
            ]
            
            assignee_name = None
            for pattern in assignee_patterns:
                assignee_match = re.search(pattern, message, re.IGNORECASE)
                if assignee_match:
                    assignee_name = assignee_match.group(1).strip()
                    logger.info(f"[TRELLO] Détection spécifique pour assigné avec pattern '{pattern}': '{assignee_name}'")
                    break
            
            # Vérifier si le nom de la tâche est présent
            task_name_match = re.search(r"['']([^'']*)['']|[\"]([^\"]*)[\"]", message)
            task_name = None
            if task_name_match:
                task_name = next((g for g in task_name_match.groups() if g is not None), None)
            
            # Vérifier si la liste est présente avec une regex améliorée
            list_patterns = [
                # Pattern pour capturer la liste entre guillemets
                r"dans\s+(?:la\s+)?(?:colonne\s+)?[''\"](.*?)['\"\s](?:\s+sur|\s+et|\s+pour|\s+à|\s+avec|$)",
                r"dans\s+(?:la\s+)?(?:colonne\s+)?[''\"]([^'\"]+)[''\"]",
                # Pattern sans guillemets
                r"dans\s+(?:la\s+)?(?:colonne\s+)?([^,\.\"\']+?)(?:\s+sur|\s+et|\s+pour|\s+à|\s+avec|$)"
            ]
            
            list_name = "À faire"  # Valeur par défaut
            for pattern in list_patterns:
                list_match = re.search(pattern, message, re.IGNORECASE)
                if list_match:
                    list_name = list_match.group(1).strip()
                    logger.info(f"[TRELLO] Liste détectée avec pattern '{pattern}': '{list_name}'")
                    break
            
            # Nettoyer les guillemets potentiels et autres caractères problématiques
            list_name = list_name.strip("'").strip('"').strip()
            if list_name.startswith("'") or list_name.startswith('"'):
                list_name = list_name[1:]
            if list_name.endswith("'") or list_name.endswith('"'):
                list_name = list_name[:-1]
            
            logger.info(f"[TRELLO] Liste après nettoyage: '{list_name}'")
            
            # Vérifier si la date d'échéance est présente
            due_date = None
            day_patterns = {
                "vendredi": 4, "lundi": 0, "mardi": 1, "mercredi": 2, 
                "jeudi": 3, "samedi": 5, "dimanche": 6
            }
            for day, weekday in day_patterns.items():
                if day in message.lower():
                    today = datetime.now()
                    days_until = (weekday - today.weekday()) % 7
                    next_day = today + timedelta(days=days_until)
                    next_day = next_day.replace(hour=23, minute=59, second=59)
                    due_date = next_day.strftime("%Y-%m-%dT%H:%M:%S.000Z")
                    break
            
            # Charger les membres du tableau pour vérifier si l'assigné existe
            try:
                self._load_board_members()
                self._load_board_lists()
                
                # Vérifier si l'assigné existe (recherche plus flexible)
                assignee_member = None
                
                if assignee_name:
                    logger.info(f"[TRELLO] Recherche du membre: '{assignee_name}'")
                    
                    # Normaliser le nom en enlevant les espaces pour comparer avec username
                    normalized_name = assignee_name.lower().replace(" ", "")
                    
                    for member in self.members_data:
                        member_username = member.get('username', '').lower()
                        member_fullname = member.get('fullName', '').lower() if member.get('fullName') else ''
                        assignee_lower = assignee_name.lower()
                        
                        logger.info(f"[TRELLO] Comparaison avec membre: username='{member_username}', fullName='{member_fullname}'")
                        
                        # Vérification plus flexible
                        if (member_username == assignee_lower or  # Correspondance exacte username
                            member_fullname == assignee_lower or  # Correspondance exacte fullName
                            normalized_name == member_username or  # franckadas == franckadas
                            assignee_lower in member_fullname or  # franck dans "franck adas"
                            member_username in normalized_name):  # franckadas dans franckadas
                            assignee_member = member
                            logger.info(f"[TRELLO] Membre trouvé: {assignee_member}")
                            break
                
                if assignee_name and not assignee_member:
                    # Le membre n'existe pas dans le tableau Trello
                    members_list = "\n".join([f"• {m.get('fullName', '')} (@{m.get('username', '')})" 
                                            for m in self.members_data if m.get('fullName') or m.get('username')])
                    return f"❌ Le membre '{assignee_name}' n'existe pas dans ce tableau Trello.\n\nVoici les membres disponibles :\n{members_list}\n\nVeuillez réessayer avec un de ces membres."
                
                # Vérifier si la liste existe
                list_exists = False
                exact_list_name = None
                
                # Afficher toutes les listes disponibles pour le debug
                logger.info(f"[TRELLO] Listes disponibles: {self.available_lists}")
                
                # Nettoyage supplémentaire pour éliminer les guillemets problématiques
                # Cette étape est cruciale pour éviter les guillemets doubles comme ''En cours''
                list_name = list_name.replace("''", "").replace('""', "").strip()
                logger.info(f"[TRELLO] Liste après nettoyage supplémentaire: '{list_name}'")
                
                # 1. Recherche exacte
                if list_name in self.available_lists:
                    list_exists = True
                    exact_list_name = list_name
                    logger.info(f"[TRELLO] Liste trouvée par correspondance exacte: '{exact_list_name}'")
                else:
                    # 2. Recherche insensible à la casse
                    for available_list in self.available_lists:
                        logger.info(f"[TRELLO] Comparaison: '{available_list.lower()}' vs '{list_name.lower()}'")
                        if available_list.lower() == list_name.lower():
                            list_exists = True
                            exact_list_name = available_list  # Utiliser le nom exact avec la bonne casse
                            logger.info(f"[TRELLO] Liste trouvée par correspondance insensible à la casse: '{exact_list_name}'")
                            break
                
                if not list_exists:
                    list_suggestions = "\n".join([f"• {lst}" for lst in self.available_lists])
                    return f"❌ La liste '{list_name}' n'existe pas dans le tableau actif.\n\nListes disponibles :\n{list_suggestions}"
                
                # Si on a un nom de tâche, on peut créer la tâche
                if task_name:
                    self.task_info = {
                        "name": task_name,
                        "list_name": exact_list_name,  # Utiliser le nom exact avec la bonne casse
                        "assignee": assignee_member.get('username'),
                        "due_date": due_date
                    }
                    return self._create_task()
            except Exception as e:
                logger.error(f"[TRELLO] Erreur lors de la vérification des membres: {str(e)}")
                return f"❌ Erreur lors de la vérification: {str(e)}"
        
            # Continuer avec le traitement normal si la détection spécifique n'a pas fonctionné
            if not self.trello_integration:
                logger.warning("[TRELLO] Intégration Trello non trouvée pour l'utilisateur")
                return "Vous n'avez pas installé cette intégration. Veuillez configurer Trello dans vos intégrations avant de l'utiliser."

            # Vérifier la présence des attributs requis et les logger
            logger.info(f"[TRELLO] Vérification des attributs de l'intégration")
            try:
                active_board_id = self.trello_integration.get_active_board_id()
                logger.info(f"[TRELLO] Active board ID: {active_board_id}")
            except Exception as e:
                logger.error(f"[TRELLO] Erreur lors de la récupération du board ID: {str(e)}")
                return f"❌ Erreur de configuration Trello: {str(e)}"
            
            if not active_board_id:
                logger.warning("[TRELLO] Aucun tableau actif configuré")
                return "❌ Aucun tableau Trello actif n'a été configuré. Veuillez configurer un tableau dans vos paramètres d'intégration Trello."

            # Vérifier les variables d'environnement
            logger.info(f"[TRELLO] Vérification des variables d'environnement")
            trello_api_url = getattr(settings, 'TRELLO_API_URL', None)
            trello_api_key = getattr(settings, 'TRELLO_API_KEY', None)
            
            if not trello_api_url or not trello_api_key:
                logger.error(f"[TRELLO] Variables d'environnement manquantes: API_URL={trello_api_url is not None}, API_KEY={trello_api_key is not None}")
                return "❌ Configuration Trello incomplète sur le serveur. Veuillez contacter l'administrateur."

            # Vérifier si le tableau existe et est accessible
            logger.info(f"[TRELLO] Vérification de l'existence du tableau {active_board_id}")
            if not self._verify_board_exists(active_board_id):
                logger.warning(f"[TRELLO] Tableau {active_board_id} non accessible")
                return f"❌ Le tableau Trello configuré n'est pas accessible. Veuillez vérifier que le tableau existe et que vous avez les permissions nécessaires."

            logger.info(f"[TRELLO] Tableau validé, traitement de la requête")

            # Si c'est une demande de tâches en retard
            if "tâches en retard" in message.lower():
                overdue_tasks = self.get_overdue_tasks()
                
                if not overdue_tasks:
                    return "✅ Bonne nouvelle ! Aucune tâche n'est en retard."
                
                response = "📅 Voici les tâches en retard :\n\n"
                for task in overdue_tasks:
                    response += f"• {task['name']} (dans '{task['list']}')\n"
                    if task['assignees']:
                        response += f"  Assignée à : {', '.join(task['assignees'])}\n"
                    response += f"  Échéance : {task['due_date'].strftime('%d/%m/%Y')}\n\n"
                
                response += "Voulez-vous que j'envoie un rappel aux responsables ?"
                return response

            # Si c'est une demande de lister les tableaux
            if "affiche" in message.lower() and "tableaux" in message.lower():
                boards = self._get_available_boards()
                if not boards:
                    return "❌ Je n'ai pas pu récupérer vos tableaux Trello. Veuillez vérifier votre intégration."
                
                response = "📋 Voici vos tableaux Trello :\n\n"
                active_board_id = self.trello_integration.get_active_board_id()
                
                for board in boards:
                    is_active = board['id'] == active_board_id
                    response += f"• {board['name']}{' (Tableau actif)' if is_active else ''}\n"
                
                response += "\nVous pouvez changer de tableau actif dans les paramètres de votre intégration Trello."
                return response

            # Si c'est une demande de lister les listes du tableau
            if "affiche" in message.lower() and "listes" in message.lower():
                self._load_board_lists()
                
                if not self.available_lists:
                    return "❌ Je n'ai pas pu récupérer les listes du tableau. Veuillez vérifier que le tableau existe et que vous avez les permissions nécessaires."
                
                response = "📝 Voici les listes disponibles sur votre tableau Trello actif :\n\n"
                for lst in self.available_lists:
                    response += f"• {lst}\n"
                
                return response

            # Si c'est une réponse simple avec juste le nom d'un membre
            if self.task_info and message.strip().lower() in [
                m.get('username', '').lower() for m in self.members_data
            ]:
                # Mettre à jour l'assigné dans task_info
                member = next(
                    m for m in self.members_data 
                    if m.get('username', '').lower() == message.strip().lower()
                )
                self.task_info['assignee'] = member['username']
                # Créer la tâche avec les informations mises à jour
                return self._create_task()

            # Récupérer d'abord les membres disponibles
            try:
                self._load_board_members()
                self._load_board_lists()
            except Exception as e:
                logger.error(f"Erreur lors de la récupération des données Trello: {str(e)}")
                return "Désolée, je n'arrive pas à récupérer les informations du tableau Trello. Veuillez vérifier votre configuration."

            # Extraire les informations de la tâche
            task_info = self._extract_task_info(message)
            if not task_info:
                return "Je n'ai pas pu comprendre les détails de la tâche. Pouvez-vous reformuler en précisant le nom de la tâche entre guillemets simple (par exemple : 'Ma tâche') et la liste où l'ajouter ?"

            # Vérifier si la liste existe
            if task_info.get('list_name'):
                # Nettoyer encore une fois le nom de la liste
                list_name = task_info['list_name'].replace("''", "").replace('""', "").strip()
                logger.info(f"[TRELLO] Vérification de l'existence de la liste (traitement normal): '{list_name}'")
                
                # Afficher toutes les listes disponibles pour le debug
                logger.info(f"[TRELLO] Listes disponibles: {self.available_lists}")
                
                list_exists = False
                exact_list_name = None
                
                # 1. Recherche exacte
                if list_name in self.available_lists:
                    list_exists = True
                    exact_list_name = list_name
                    logger.info(f"[TRELLO] Liste trouvée (correspondance exacte): '{exact_list_name}'")
                else:
                    # 2. Recherche insensible à la casse
                    for available_list in self.available_lists:
                        logger.info(f"[TRELLO] Comparaison: '{available_list.lower()}' vs '{list_name.lower()}'")
                        if available_list.lower() == list_name.lower():
                            list_exists = True
                            exact_list_name = available_list  # Utiliser le nom exact avec la bonne casse
                            logger.info(f"[TRELLO] Liste trouvée (correspondance insensible à la casse): '{exact_list_name}'")
                            break
                
                if not list_exists:
                    list_suggestions = "\n\nListes disponibles :\n" + "\n".join([f"• {lst}" for lst in self.available_lists])
                    return f"❌ La liste '{list_name}' n'existe pas dans le tableau actif.{list_suggestions}"
                else:
                    # Mettre à jour le nom de la liste avec le nom exact
                    task_info['list_name'] = exact_list_name

            # Vérifier si le membre assigné existe
            if task_info.get('assignee'):
                assignee = task_info['assignee']
                
                # Nettoyer le nom d'assigné
                assignee = assignee.strip("'").strip('"').strip()
                normalized_name = assignee.lower().replace(" ", "")
                
                logger.info(f"[TRELLO] Vérification de l'existence du membre: '{assignee}' (normalized: '{normalized_name}')")
                
                # Recharger les membres pour être à jour
                self._load_board_members()
                
                member_exists = False
                exact_member_info = None
                
                for member in self.members_data:
                    member_username = member.get('username', '').lower()
                    member_fullname = member.get('fullName', '').lower() if member.get('fullName') else ''
                    
                    logger.info(f"[TRELLO] Comparaison avec membre: username='{member_username}', fullName='{member_fullname}'")
                    
                    # Vérification plus flexible
                    if (member_username == assignee.lower() or
                        member_fullname == assignee.lower() or
                        normalized_name == member_username or
                        assignee.lower() in member_fullname or
                        member_username in normalized_name):
                        member_exists = True
                        exact_member_info = member
                        logger.info(f"[TRELLO] Membre trouvé: {exact_member_info}")
                        break
                
                if not member_exists:
                    members_list = "\n\nMembres disponibles:\n" + "\n".join([f"• {m.get('fullName', '')} (@{m.get('username', '')})" 
                                                    for m in self.members_data if m.get('fullName') or m.get('username')])
                    return f"❌ Le membre '{assignee}' n'existe pas dans ce tableau Trello.{members_list}"
                else:
                    # Mettre à jour avec le nom d'utilisateur exact
                    task_info['assignee'] = exact_member_info.get('username')

            # Créer la tâche avec les informations complètes
            self.task_info = task_info
            return self._create_task()

        except Exception as e:
            logger.error(f"Erreur lors de la gestion de la requête Trello: {str(e)}")
            return "Désolée, une erreur s'est produite lors de la création de la tâche. Veuillez réessayer."
    
    def _verify_board_exists(self, board_id):
        """Vérifie si le tableau existe et est accessible"""
        from django.conf import settings
        
        try:
            response = requests.get(
                f"{settings.TRELLO_API_URL}/boards/{board_id}",
                params={
                    'key': settings.TRELLO_API_KEY,
                    'token': self.trello_integration.access_token,
                    'fields': 'name'
                }
            )
            return response.status_code == 200
        except Exception as e:
            logger.error(f"Erreur lors de la vérification du tableau: {str(e)}")
            return False
    
    def _get_available_boards(self):
        """Récupère la liste des tableaux disponibles"""
        from django.conf import settings
        
        try:
            response = requests.get(
                f"{settings.TRELLO_API_URL}/members/me/boards",
                params={
                    'key': settings.TRELLO_API_KEY,
                    'token': self.trello_integration.access_token,
                    'filter': 'open',
                    'fields': 'name'
                }
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Erreur lors de la récupération des tableaux: {str(e)}")
            return []
    
    def _load_board_members(self):
        """Charge les membres du tableau Trello actif"""
        from django.conf import settings
        
        response = requests.get(
            f"{settings.TRELLO_API_URL}/boards/{self.trello_integration.get_active_board_id()}/members",
            params={
                'key': settings.TRELLO_API_KEY,
                'token': self.trello_integration.access_token,
                'fields': 'username,fullName'
            }
        )
        response.raise_for_status()
        members = response.json()
        self.members_data = members
        self.available_members = []
        for m in members:
            # Créer une description claire pour chaque membre
            member_desc = []
            if m.get('username'):
                member_desc.append(f"@{m['username']}")
            if m.get('fullName'):
                member_desc.append(f"({m['fullName']})")
            if member_desc:
                self.available_members.append(" ".join(member_desc))
    
    def _load_board_lists(self):
        """Charge les listes du tableau Trello actif"""
        from django.conf import settings
        
        response = requests.get(
            f"{settings.TRELLO_API_URL}/boards/{self.trello_integration.get_active_board_id()}/lists",
            params={
                'key': settings.TRELLO_API_KEY,
                'token': self.trello_integration.access_token,
                'fields': 'name'
            }
        )
        response.raise_for_status()
        lists = response.json()
        self.available_lists = [lst['name'] for lst in lists]
    
    def _extract_task_info(self, text):
        """Extrait les informations de tâche du texte"""
        try:
            logger.info(f"[TRELLO] Extraction des informations de tâche à partir de: '{text}'")
            
            # Fonction utilitaire pour normaliser les guillemets
            def normalize_quotes(input_text):
                # Convertir tous les types de guillemets simples en apostrophe standard
                for quote in [''', ''', '′', '‛', '´', '`']:
                    input_text = input_text.replace(quote, "'")
                
                # Convertir tous les types de guillemets doubles en guillemet standard
                for quote in ['"', '"', '″', '″', '‟']:
                    input_text = input_text.replace(quote, '"')
                
                # Convertir les guillemets français
                input_text = input_text.replace('«', '"').replace('»', '"')
                
                return input_text
            
            # Normaliser les guillemets dans le texte pour améliorer la détection
            normalized_text = normalize_quotes(text)
            logger.info(f"[TRELLO] Texte normalisé: '{normalized_text}'")
            
            # Extraire le nom de la tâche avec des patterns améliorés
            name_patterns = [
                # Pattern pour créer/ajouter une tâche avec guillemet simple - Plus spécifique en premier
                r"(?:créer|cree|ajoute[rz]?)\s+(?:une\s+)?(?:tâche|tache|carte)\s+'([^']+)'",
                
                # Pattern pour créer/ajouter une tâche avec n'importe quel type de guillemet
                r"(?:créer|cree|ajoute[rz]?)\s+(?:une\s+)?(?:tâche|tache|carte)\s+['\"]([^'\"]+)['\"]",
                
                # Pattern spécifique pour nouvelle tâche et nova tâche
                r"(?:nouvelle|nova)\s+(?:tâche|tache|carte)\s+['\"]([^'\"]+)['\"]",
                
                # Pattern simplifié pour guillemets simples - uniquement le texte entre guillemets
                r"'([^']+)'",
                
                # Pattern général pour guillemets mixtes (simples ou doubles)
                r"['\"]([^'\"]+)['\"]",
                
                # Patterns pour titre explicite entre guillemets
                r"(?:tâche|carte|todo|ticket)\s+['\"]([^'\"]+)['\"]",
                
                # Pattern pour titre en début de phrase
                r"^['\"]([^'\"]+)['\"]"
            ]
            
            name = None
            for pattern in name_patterns:
                name_match = re.search(pattern, normalized_text, re.IGNORECASE)
                if name_match:
                    name = name_match.group(1).strip()
                    logger.info(f"[TRELLO] Nom de tâche trouvé avec pattern '{pattern}': '{name}'")
                    break
                else:
                    logger.debug(f"[TRELLO] Pattern '{pattern}' non trouvé dans '{normalized_text}'")
            
            # Si un nom a été trouvé, vérifier s'il ne contient pas d'instructions de création
            if name:
                # Liste d'indicateurs d'instructions qui ne devraient pas faire partie du titre
                instruction_indicators = [
                    "dans la colonne", "dans colonne", "assigne", "à faire", 
                    "sur trello", "avec échéance", "pour", "dans la liste",
                    "dans", "colonne", "sur", "trello", "assigné", "échéance"
                ]
                
                # Chercher ces indicateurs dans le titre pour extraire uniquement le vrai titre
                for indicator in instruction_indicators:
                    if indicator in name.lower():
                        # Extraire seulement la partie avant l'indicateur
                        indicator_pos = name.lower().find(indicator)
                        if indicator_pos > 0:
                            clean_name = name[:indicator_pos].strip()
                            logger.info(f"[TRELLO] Titre nettoyé de l'instruction '{indicator}': '{clean_name}'")
                            name = clean_name
            
                # Vérifier si le nom ne contient pas encore d'autres mots-clés problématiques
                suspicious_words = ["colonne", "liste", "assigne", "trello"]
                contains_suspicious = any(word in name.lower() for word in suspicious_words)
                
                if contains_suspicious:
                    # Si le titre contient encore des mots suspicieux, on peut essayer de diviser
                    # et prendre seulement la première partie qui semble être le titre réel
                    words = name.split()
                    for i, word in enumerate(words):
                        if any(sus in word.lower() for sus in suspicious_words) and i > 0:
                            clean_name = " ".join(words[:i]).strip()
                            logger.info(f"[TRELLO] Titre nettoyé des mots suspicieux: '{clean_name}'")
                            name = clean_name
                            break
            
            # Si toujours pas de nom, essayer avec des patterns alternatifs sans guillemets
            if not name:
                # Si pas de guillemets, essayer de trouver le nom de tâche basé sur des motifs usuels
                task_patterns = [
                    r"tâche\s+(?:intitulée\s+)?['']?([^''.,]+)['']?",
                    r"(?:ajoute|créer?)\s+(?:une\s+)?tâche\s+['']?([^''.,]+)['']?",
                    r"(?:ajoute|créer?)\s+(?:une\s+)?carte\s+['']?([^''.,]+)['']?"
                ]
                
                for pattern in task_patterns:
                    pattern_match = re.search(pattern, normalized_text, re.IGNORECASE)
                    if pattern_match:
                        name = pattern_match.group(1).strip()
                        logger.info(f"[TRELLO] Nom de tâche trouvé avec pattern alternatif '{pattern}': '{name}'")
                        break

            if not name:
                logger.warning(f"[TRELLO] Nom de tâche non trouvé dans: '{text}'")
                return None  # Si pas de nom clairement identifié, on ne peut pas créer la tâche

            logger.info(f"[TRELLO] Nom de tâche final: '{name}'")

            # Extraire la colonne - AMÉLIORATION : délimiteurs plus précis et gestion des guillemets problématiques
            column_patterns = [
                # Patterns qui indiquent clairement qu'il s'agit d'une colonne
                r"dans\s+(?:la\s+)?(?:colonne\s+)?['\"](.+?)['\"](?:\s+sur|\s+et|\s+pour|\s+à|\s+avec|$)",
                r"dans\s+(?:la\s+)?(?:colonne\s+)?['\"]([^'\"]+)['\"]",
                # Ensuite sans guillemets
                r"dans\s+(?:la\s+)?(?:colonne\s+)?([^,\.\"\']+?)(?:\s+sur|\s+et|\s+pour|\s+à|\s+avec|$)",
                r"colonne\s+['\"]?([^'\".,]+?)(?:\s+sur|\s+et|\s+pour|\s+à|\s+avec|$)",
                r"liste\s+['\"]?([^'\".,]+?)(?:\s+sur|\s+et|\s+pour|\s+à|\s+avec|$)"
            ]
            
            list_name = "À faire"  # Valeur par défaut
            for pattern in column_patterns:
                column_match = re.search(pattern, normalized_text, re.IGNORECASE)
                if column_match:
                    list_name = column_match.group(1).strip()
                    logger.info(f"[TRELLO] Liste détectée avec pattern '{pattern}': '{list_name}'")
                    # Arrêter dès qu'on trouve une correspondance
                    break
            
            # Nettoyer le nom de la liste (enlever les guillemets et espaces supplémentaires)
            list_name = list_name.strip("'").strip('"').strip()
            # Supprimer les guillemets doubles supplémentaires qui pourraient être inclus
            list_name = list_name.replace("''", "").replace('""', "")
            if list_name.startswith("'") or list_name.startswith('"'):
                list_name = list_name[1:]
            if list_name.endswith("'") or list_name.endswith('"'):
                list_name = list_name[:-1]
                
            logger.info(f"[TRELLO] Liste détectée et nettoyée: '{list_name}'")

            # Extraire l'assigné - AMÉLIORATION : capture des noms composés
            assignee_patterns = [
                # Pattern spécifique pour les noms composés (priorité)
                r"assign[eé][^a-zA-Z]*la\s+[àa]\s+([A-Za-z]+(?:\s+[A-Za-z]+){0,2})",
                r"assign[eé][^a-zA-Z]*la\s+[àa]\s+(?:[''\"]?)([^'\".,;]+(?:\s+[^'\".,;]+)?)(?:[''\"]?)(?:\s+|$|\.|,)",
                # Patterns génériques
                r"assign[eé][eé]?\s+[àa]\s+(?:[''\"]?)([^'\".,;]+(?:\s+[^'\".,;]+)?)(?:[''\"]?)(?:\s+|$|\.|,)",
                r"assign[eé][eé]?\s+[àa]\s+(.+?)(?:\s+(?:et|pour|avec|ayant)|\.|\,|$)",
                r"[àa]\s+([^\.]+?)(?:\s+(?:et|pour|avec|ayant)|\.|\,|$)"
            ]
            
            assignee = None
            for pattern in assignee_patterns:
                assignee_match = re.search(pattern, normalized_text, re.IGNORECASE)
                if assignee_match:
                    assignee = assignee_match.group(1).strip()
                    logger.info(f"[TRELLO] Assigné détecté avec pattern '{pattern}': '{assignee}'")
                    break
            
            # Recherche spécifique pour les noms fréquents
            if not assignee:
                for name in ["marie", "franck", "adas", "franckadas"]:
                    if name in normalized_text.lower():
                        # Chercher le nom complet, potentiellement composé
                        name_match = re.search(r"[àa]\s+([A-Za-z]+(?:\s+[A-Za-z]+){0,2})", normalized_text, re.IGNORECASE)
                        if name_match:
                            assignee = name_match.group(1).strip()
                            logger.info(f"[TRELLO] Assigné détecté avec recherche spécifique: '{assignee}'")
                            break
            
            # Nettoyage final de l'assigné
            if assignee:
                assignee = assignee.strip("'").strip('"').strip()
                logger.info(f"[TRELLO] Assigné final après nettoyage: '{assignee}'")

            # Extraire la date d'échéance
            due_date = None
            day_patterns = {
                "vendredi": 4,
                "lundi": 0,
                "mardi": 1,
                "mercredi": 2,
                "jeudi": 3,
                "samedi": 5,
                "dimanche": 6
            }
            
            for day, weekday in day_patterns.items():
                if day in normalized_text.lower():
                    # Calculer le prochain jour de la semaine correspondant
                    today = datetime.now()
                    days_until = (weekday - today.weekday()) % 7
                    next_day = today + timedelta(days=days_until)
                    next_day = next_day.replace(hour=23, minute=59, second=59)
                    due_date = next_day.strftime("%Y-%m-%dT%H:%M:%S.000Z")
                    logger.info(f"[TRELLO] Date d'échéance détectée: {day} ({next_day.strftime('%d/%m/%Y')})")
                    break
                    
            if not due_date:
                if "demain" in normalized_text.lower():
                    tomorrow = datetime.now() + timedelta(days=1)
                    tomorrow = tomorrow.replace(hour=23, minute=59, second=59)
                    due_date = tomorrow.strftime("%Y-%m-%dT%H:%M:%S.000Z")
                    logger.info(f"[TRELLO] Date d'échéance: demain ({tomorrow.strftime('%d/%m/%Y')})")
                elif "semaine prochaine" in normalized_text.lower():
                    next_week = datetime.now() + timedelta(days=7)
                    next_week = next_week.replace(hour=23, minute=59, second=59)
                    due_date = next_week.strftime("%Y-%m-%dT%H:%M:%S.000Z")
                    logger.info(f"[TRELLO] Date d'échéance: semaine prochaine ({next_week.strftime('%d/%m/%Y')})")

            task_info = {
                "name": name,
                "list_name": list_name,
                "assignee": assignee,
                "due_date": due_date
            }
            
            logger.info(f"[TRELLO] Informations de tâche extraites: {task_info}")
            return task_info
            
        except Exception as e:
            logger.error(f"[TRELLO] Erreur lors de l'extraction des informations de tâche: {str(e)}")
            return None
    
    def get_overdue_tasks(self):
        """Récupère les tâches en retard de Trello"""
        from django.conf import settings
        
        try:
            # Récupérer toutes les listes du tableau
            lists_response = requests.get(
                f"{settings.TRELLO_API_URL}/boards/{self.trello_integration.get_active_board_id()}/lists",
                params={
                    'key': settings.TRELLO_API_KEY,
                    'token': self.trello_integration.access_token
                }
            )
            lists_response.raise_for_status()
            lists = lists_response.json()
            
            # Récupérer toutes les cartes avec une date d'échéance
            cards_response = requests.get(
                f"{settings.TRELLO_API_URL}/boards/{self.trello_integration.get_active_board_id()}/cards",
                params={
                    'key': settings.TRELLO_API_KEY,
                    'token': self.trello_integration.access_token,
                    'fields': 'name,due,idList,dueComplete,idMembers'
                }
            )
            cards_response.raise_for_status()
            all_cards = cards_response.json()
            
            # Récupérer les membres du tableau
            members_response = requests.get(
                f"{settings.TRELLO_API_URL}/boards/{self.trello_integration.get_active_board_id()}/members",
                params={
                    'key': settings.TRELLO_API_KEY,
                    'token': self.trello_integration.access_token
                }
            )
            members_response.raise_for_status()
            members = {m['id']: m['username'] for m in members_response.json()}
            
            # Filtrer les cartes en retard
            now = datetime.now(timezone.utc)
            overdue_cards = []
            for card in all_cards:
                if (card.get('due') and not card.get('dueComplete') and 
                    datetime.fromisoformat(card['due'].replace('Z', '+00:00')) < now):
                    list_name = next(lst['name'] for lst in lists if lst['id'] == card['idList'])
                    assignees = [members.get(member_id) for member_id in card.get('idMembers', [])]
                    overdue_cards.append({
                        'name': card['name'],
                        'list': list_name,
                        'due_date': datetime.fromisoformat(card['due'].replace('Z', '+00:00')),
                        'assignees': assignees
                    })
            
            return overdue_cards

        except Exception as e:
            logger.error(f"Erreur lors de la récupération des tâches en retard: {str(e)}")
            raise
    
    def _get_list_id(self, list_name):
        """Retourne l'ID de la liste Trello à partir de son nom"""
        from django.conf import settings
        
        # Nettoyer le nom de liste pour éviter les problèmes de guillemets
        list_name = list_name.replace("''", "").replace('""', "").strip()
        logger.info(f"[TRELLO] Recherche de l'ID pour la liste: '{list_name}'")
        
        if not self.available_lists:
            self._load_board_lists()
            logger.info(f"[TRELLO] Listes disponibles chargées: {self.available_lists}")
        
        # Recherche insensible à la casse
        target_list_name = list_name.lower()
        exact_match_list = None
        
        # D'abord, essayer de trouver une correspondance exacte
        for lst in self.available_lists:
            if lst.lower() == target_list_name:
                exact_match_list = lst
                logger.info(f"[TRELLO] Liste correspondante trouvée: '{exact_match_list}'")
                break
        
        if not exact_match_list:
            lists_names = "\n".join([f"• {lst}" for lst in self.available_lists])
            logger.error(f"[TRELLO] Liste '{list_name}' non trouvée. Listes disponibles:\n{lists_names}")
            raise ValueError(f"Liste '{list_name}' non trouvée")
            
        # Récupérer l'ID de la liste correspondante
        response = requests.get(
            f"{settings.TRELLO_API_URL}/boards/{self.trello_integration.get_active_board_id()}/lists",
            params={
                'key': settings.TRELLO_API_KEY,
                'token': self.trello_integration.access_token,
                'fields': 'name,id'
            }
        )
        response.raise_for_status()
        lists = response.json()
        
        # Rechercher avec le nom exact trouvé
        for trello_list in lists:
            if trello_list['name'] == exact_match_list:
                logger.info(f"[TRELLO] ID trouvé pour la liste '{exact_match_list}': {trello_list['id']}")
                return trello_list['id']
                
        # Recherche avec insensibilité à la casse (fallback)
        for trello_list in lists:
            if trello_list['name'].lower() == target_list_name:
                logger.info(f"[TRELLO] ID trouvé (fallback) pour la liste '{list_name}': {trello_list['id']}")
                return trello_list['id']
        
        # Si on arrive ici, c'est qu'on n'a pas trouvé l'ID
        logger.error(f"[TRELLO] Impossible de trouver l'ID pour la liste '{list_name}' malgré sa présence")
        raise ValueError(f"Liste '{list_name}' trouvée mais ID non récupérable")
    
    def _get_member_info(self, member_name):
        """Retourne les informations d'un membre à partir de son nom ou username"""
        
        if not self.members_data:
            self._load_board_members()
        
        member_name_lower = member_name.lower()
        
        # Recherche flexible du membre
        for member in self.members_data:
            member_username = member.get('username', '').lower()
            member_fullname = member.get('fullName', '').lower() if member.get('fullName') else ''
            
            # Vérifier si le nom correspond exactement ou partiellement
            if (member_username == member_name_lower or 
                member_fullname == member_name_lower or
                member_name_lower in member_fullname or 
                member_username in member_name_lower):
                return member
        
        return None
    
    def _create_task(self):
        """Crée une tâche Trello avec les informations fournies"""
        from django.conf import settings
        
        try:
            info = self.task_info
            if not info or not info.get('name'):
                return "Désolée, je n'ai pas les informations nécessaires pour créer la tâche."

            # Obtenir l'id de la liste (recherche insensible à la casse)
            try:
                # D'abord essayer de trouver une correspondance exacte
                list_id = None
                
                # Si la liste a été mise à jour depuis le chargement initial, recharger
                self._load_board_lists()
                
                # Nettoyer le nom de la liste pour être sûr
                list_name = info['list_name'].replace("''", "").replace('""', "").strip()
                logger.info(f"[TRELLO] Création de tâche - liste nettoyée: '{list_name}'")
                
                # Rechercher une correspondance exacte ou insensible à la casse
                for lst in self.available_lists:
                    if lst == list_name or lst.lower() == list_name.lower():
                        try:
                            list_id = self._get_list_id(lst)
                            logger.info(f"[TRELLO] Liste trouvée pour la tâche: '{lst}' (ID: {list_id})")
                            break
                        except ValueError as ve:
                            logger.warning(f"[TRELLO] Erreur lors de la récupération de l'ID de liste '{lst}': {str(ve)}")
                            # Continuer à chercher
                            pass
                
                # Si aucune correspondance n'a été trouvée, essayer la méthode normale
                if not list_id:
                    try:
                        list_id = self._get_list_id(list_name)
                        logger.info(f"[TRELLO] ID de liste trouvé avec la méthode normale: {list_id}")
                    except ValueError as ve:
                        logger.error(f"[TRELLO] Échec de récupération de l'ID pour '{list_name}': {str(ve)}")
                        raise
                    
            except ValueError as e:
                # Retourner une liste des listes disponibles
                list_suggestions = "\n".join([f"• {lst}" for lst in self.available_lists])
                logger.error(f"[TRELLO] Liste '{list_name}' non trouvée: {str(e)}")
                return f"❌ La liste '{list_name}' n'existe pas dans le tableau actif.\n\nListes disponibles :\n{list_suggestions}"

            # Création de la tâche dans Trello
            data = {
                'name': info['name'],
                'idList': list_id,
                'key': settings.TRELLO_API_KEY,
                'token': self.trello_integration.access_token
            }

            if info.get('due_date'):
                data['due'] = info['due_date']

            member_not_found = False
            member_name = None
            if info.get('assignee'):
                member_name = info['assignee']
                # Recharger les membres pour s'assurer qu'ils sont à jour
                self._load_board_members()
                
                # Trouver l'ID du membre avec une correspondance plus flexible
                member = None
                assignee = info['assignee']
                assignee_lower = assignee.lower()
                # Normaliser le nom en enlevant les espaces pour comparer avec username
                normalized_name = assignee_lower.replace(" ", "")
                
                logger.info(f"[TRELLO] Recherche du membre pour assignation: '{assignee}'")
                
                # Recherche plus flexible
                for m in self.members_data:
                    member_username = m.get('username', '').lower()
                    member_fullname = m.get('fullName', '').lower() if m.get('fullName') else ''
                    
                    # Vérifier si le nom correspond exactement ou partiellement
                    if (member_username == assignee_lower or 
                        member_fullname == assignee_lower or
                        normalized_name == member_username or 
                        assignee_lower in member_fullname or 
                        member_username in normalized_name):
                        member = m
                        logger.info(f"[TRELLO] Membre trouvé pour assignation: {member}")
                        break
                
                if member:
                    data['idMembers'] = [member['id']]
                    # Utiliser le nom complet pour l'affichage si disponible
                    if member.get('fullName'):
                        member_name = member['fullName']
                else:
                    # Membre non trouvé - on le signalera dans le message
                    member_not_found = True
                    logger.warning(f"[TRELLO] Membre assigné non trouvé: {assignee}")

            # Appel API pour créer la carte
            logger.info(f"[TRELLO] Création de la carte avec les données: {data}")
            response = requests.post(
                f"{settings.TRELLO_API_URL}/cards",
                json=data
            )
            response.raise_for_status()

            # Réinitialiser après succès
            result = response.json()
            card_url = result.get('shortUrl', '#')
            self.task_info = {}
            
            success_message = f"✅ J'ai créé la tâche '{info['name']}' dans la liste '{info['list_name']}'"
            
            if member_not_found and member_name:
                members_list = "\n".join([f"• {m.get('fullName', '')} (@{m.get('username', '')})" 
                                        for m in self.members_data if m.get('fullName') or m.get('username')])
                
                success_message += f"\n\n⚠️ Attention: Je n'ai pas pu assigner la tâche à '{member_name}' car ce membre n'existe pas dans ce tableau Trello."
                success_message += f"\n\nMembres disponibles :\n{members_list}"
            elif info.get('assignee'):
                success_message += f" et je l'ai assignée à {member_name}"
            
            if info.get('due_date'):
                due_date = datetime.fromisoformat(info['due_date'].replace('Z', '+00:00'))
                success_message += f", avec échéance le {due_date.strftime('%d/%m/%Y')}"
            
            success_message += f"\n\nVoir la carte: {card_url}"
            
            return success_message

        except Exception as e:
            logger.error(f"Erreur lors de la création de la tâche: {str(e)}")
            return f"Désolée, une erreur s'est produite lors de la création de la tâche: {str(e)}" 