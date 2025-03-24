import logging
import json
from datetime import datetime
from ..config import INTEGRATION_CAPABILITIES, GENERAL_RESPONSES

logger = logging.getLogger(__name__)

class IntentAnalyzer:
    """Analyseur d'intention qui gère la détection et le routage des intentions"""
    
    def __init__(self, orchestrator):
        self.orchestrator = orchestrator
        self.user = orchestrator.user
        self.openai_client = orchestrator.openai_client
    
    def analyze_intent(self, message: str) -> dict:
        """
        Analyse l'intention de l'utilisateur dans le message.
        
        Args:
            message (str): Le message de l'utilisateur
            
        Returns:
            dict: Un dictionnaire contenant l'intention détectée et les informations associées
        """
        # Liste des mots-clés indiquant une conversation simple
        conversation_keywords = [
            'bonjour', 'salut', 'hello', 'hi', 'hey',
            'merci', 'thanks', 'thank you',
            'au revoir', 'bye', 'goodbye',
            'comment vas-tu', 'ça va', 'comment allez-vous',
            'bien', 'mal', 'bof', 'super',
            'oui', 'non', 'ok', 'd\'accord'
        ]
        
        # Vérifier si le message contient des mots-clés de conversation
        message_lower = message.lower()
        for keyword in conversation_keywords:
            if keyword in message_lower:
                # Utiliser OpenAI pour générer une réponse conversationnelle
                response = self._get_conversational_response(message)
                return {
                    'intent': 'conversation',
                    'raw_response': response
                }

        # Détecter si c'est une requête générale (heure, date, etc.)
        general_response = self._detect_general_query(message)
        if general_response:
            return {
                'intent': 'general_query',
                'raw_response': general_response
            }

        # Si aucun mot-clé de conversation n'est trouvé, continuer avec l'analyse des intégrations
        active_integrations = self._get_active_integrations()
        
        # Dictionnaire des mots-clés par intégration
        integration_patterns = {
            'gmail': {
                'keywords': ['email', 'mail', 'envoyer', 'message', 'gmail'],
                'actions': {
                    'envoyer': ['envoyer', 'composer', 'créer', 'rédiger'],
                    'lire': ['lire', 'consulter', 'vérifier', 'voir'],
                    'rechercher': ['rechercher', 'trouver', 'chercher']
                }
            },
            'slack': {
                'keywords': ['slack', 'chat', 'message', 'équipe', 'canal', 'channel'],
                'actions': {
                    'envoyer': ['envoyer', 'poster', 'partager', 'publier'],
                    'créer': ['créer', 'nouveau', 'ouvrir'],
                    'inviter': ['inviter', 'ajouter', 'membre']
                }
            },
            'hubspot': {
                'keywords': ['contact', 'client', 'prospect', 'crm', 'hubspot', 'entreprise'],
                'actions': {
                    'créer': ['créer', 'ajouter', 'nouveau'],
                    'mettre à jour': ['mettre à jour', 'modifier', 'changer'],
                    'rechercher': ['rechercher', 'chercher', 'trouver']
                }
            },
            'trello': {
                'keywords': ['tâche', 'carte', 'projet', 'board', 'trello', 'tableau', 'colonne'],
                'actions': {
                    'créer': ['créer', 'ajouter', 'nouvelle'],
                    'déplacer': ['déplacer', 'changer', 'transférer'],
                    'assigner': ['assigner', 'attribuer', 'donner']
                }
            },
            'google_drive': {
                'keywords': ['fichier', 'document', 'dossier', 'drive', 'google drive', 'partager'],
                'actions': {
                    'créer': ['créer', 'nouveau', 'ajouter'],
                    'partager': ['partager', 'donner accès', 'autoriser'],
                    'télécharger': ['télécharger', 'charger', 'upload']
                }
            }
        }

        # Détecter les intégrations possibles
        possible_integrations = []
        detected_actions = {}
        
        # Vérifier les intégrations actives
        for integration, patterns in integration_patterns.items():
            # Vérifier si l'intégration est active
            if not any(integration.lower() in ai.lower() for ai in active_integrations):
                continue
                
            # Détecter les mots-clés de l'intégration
            if any(keyword in message_lower for keyword in patterns['keywords']):
                possible_integrations.append(integration)
                
                # Détecter les actions possibles pour cette intégration
                for action, keywords in patterns['actions'].items():
                    if any(keyword in message_lower for keyword in keywords):
                        if integration not in detected_actions:
                            detected_actions[integration] = []
                        detected_actions[integration].append(action)

        # Cas 1: Aucune intégration détectée
        if not possible_integrations:
            # Utiliser OpenAI pour une analyse plus approfondie
            return self._analyze_with_openai(message)

        # Cas 2: Une seule intégration détectée
        if len(possible_integrations) == 1:
            integration = possible_integrations[0]
            actions = detected_actions.get(integration, [])
            
            # Si une seule action est détectée
            if len(actions) == 1:
                return {
                    'intent': 'integration_action',
                    'integration': integration,
                    'action': actions[0],
                    'parameters': {},
                    'raw_response': None,
                    'possible_integrations': [integration]
                }
            # Si plusieurs actions sont possibles ou aucune action détectée
            else:
                return {
                    'intent': 'integration',
                    'integration': integration,
                    'action': None,
                    'parameters': {},
                    'raw_response': "Quelle action souhaitez-vous effectuer ?",
                    'possible_integrations': [integration],
                    'possible_actions': actions
                }

        # Cas 3: Plusieurs intégrations possibles
        return {
            'intent': 'ambiguous',
            'action': None,
            'parameters': {},
            'raw_response': "Votre demande pourrait correspondre à plusieurs services. Lequel souhaitez-vous utiliser ?",
            'possible_integrations': possible_integrations,
            'detected_actions': detected_actions
        }
    
    def _get_conversational_response(self, message):
        """Obtient une réponse conversationnelle simple"""
        system_message = """Tu es Alya, une assistante IA experte et conviviale.
        Instructions :
        1. Réponds toujours de manière naturelle, amicale et engageante
        2. Utilise un ton conversationnel et professionnel
        3. Fournis des réponses courtes et précises
        4. Si tu ne sais pas quelque chose, dis-le honnêtement
        5. Utilise des émojis avec modération pour rendre la conversation plus vivante"""

        response = self.openai_client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": system_message},
                {"role": "user", "content": message}
            ],
            temperature=0.7,
            max_tokens=100
        )
        return response.choices[0].message.content
    
    def _detect_general_query(self, message):
        """Détecte si le message est une question générale non liée aux intégrations"""
        message_lower = message.lower()
        
        # Vérification spécifique pour les questions de temps/heure
        if any(time_word in message_lower for time_word in ["heure", "temps", "date", "jour"]):
            if "heure" in message_lower or "temps" in message_lower:
                # Utiliser la fonction lambda définie dans GENERAL_RESPONSES
                return GENERAL_RESPONSES['time']['response']()
            elif "date" in message_lower or "jour" in message_lower:
                return GENERAL_RESPONSES['date']['response']()
        
        # Parcourir toutes les catégories de réponses générales
        for category, info in GENERAL_RESPONSES.items():
            if any(pattern in message_lower for pattern in info['patterns']):
                if callable(info['response']):
                    return info['response']()
                return info['response']
        
        return None
    
    def _analyze_with_openai(self, message):
        """Utilise OpenAI pour une analyse plus approfondie de l'intention"""
        from ..utils.openai_utils import get_system_prompt
        
        try:
            response = self.openai_client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": get_system_prompt()},
                    {"role": "user", "content": message}
                ]
            )
            return self._parse_openai_response(response)
        except Exception as e:
            logger.error(f"Erreur lors de l'analyse OpenAI: {str(e)}")
            return {
                'intent': 'conversation',
                'raw_response': "Je suis désolé, je n'ai pas compris votre requête. Pouvez-vous reformuler ou préciser ce que vous souhaitez faire ?"
            }
    
    def _parse_openai_response(self, response):
        """
        Parse la réponse d'OpenAI pour extraire les informations pertinentes.
        """
        try:
            # Initialiser le dictionnaire de retour
            intent_data = {
                'intent': 'conversation',  # Intent par défaut
                'action': None,
                'parameters': {},
                'raw_response': ''
            }
            
            # Extraire le contenu de la réponse
            if hasattr(response, 'choices') and response.choices:
                content = response.choices[0].message.content
                intent_data['raw_response'] = content
            else:
                raise ValueError("Format de réponse OpenAI invalide")

            # Rechercher les intégrations connues dans la réponse
            known_integrations = {
                'gmail': ['email', 'mail', 'gmail', 'message'],
                'slack': ['slack', 'channel', 'chat'],
                'hubspot': ['crm', 'contact', 'lead', 'hubspot'],
                'google_drive': ['drive', 'document', 'file', 'folder'],
                'trello': ['task', 'card', 'board', 'trello']
            }

            # Détecter l'intégration
            for integration, keywords in known_integrations.items():
                if any(keyword.lower() in content.lower() for keyword in keywords):
                    intent_data['intent'] = 'integration'
                    intent_data['integration'] = integration
                    break

            # Si une intégration est détectée, chercher l'action correspondante
            if intent_data['intent'] == 'integration':
                # Définir les actions possibles pour chaque intégration
                integration_actions = {
                    'gmail': ['send', 'read', 'draft', 'search'],
                    'slack': ['send', 'notify', 'update'],
                    'hubspot': ['create', 'update', 'search', 'delete'],
                    'google_drive': ['upload', 'share', 'create', 'list'],
                    'trello': ['create', 'move', 'update', 'delete']
                }

                # Chercher l'action dans le contenu
                actions = integration_actions.get(intent_data['integration'], [])
                for action in actions:
                    if action.lower() in content.lower():
                        intent_data['action'] = action
                        # Extraire les paramètres potentiels
                        # Exemple: recherche d'emails, destinataires, sujets, etc.
                        if 'to:' in content:
                            intent_data['parameters']['recipient'] = content.split('to:')[1].split()[0]
                        if 'subject:' in content:
                            intent_data['parameters']['subject'] = content.split('subject:')[1].split('\n')[0]
                        if 'body:' in content:
                            intent_data['parameters']['body'] = content.split('body:')[1].split('\n')[0]
                        break

            return intent_data

        except Exception as e:
            logger.error(f"Erreur lors du parsing de la réponse OpenAI: {str(e)}")
            return {
                'intent': 'error',
                'action': None,
                'parameters': {},
                'error': str(e)
            }
    
    def _get_active_integrations(self):
        """Récupère la liste des intégrations actives pour l'utilisateur"""
        try:
            from alyawebapp.models import UserIntegration
            
            user_integrations = UserIntegration.objects.filter(
                user=self.user,
                enabled=True
            ).select_related('integration')
            
            return [ui.integration.name for ui in user_integrations]
        except Exception as e:
            logger.error(f"Erreur lors de la récupération des intégrations actives: {str(e)}")
            return [] 