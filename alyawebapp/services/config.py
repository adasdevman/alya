from datetime import datetime

# Configuration des timeouts
API_TIMEOUT = 10  # secondes
LONG_OPERATION_TIMEOUT = 30  # secondes
MAX_RETRIES = 3
NETWORK_TIMEOUT = 5  # secondes pour les vérifications réseau
SESSION_TIMEOUT = 3600  # 1 heure
CACHE_KEY_PREFIX = 'alya_session_'

# Configuration des modèles
INTENT_MODEL = "gpt-3.5-turbo"  # Pour la détection d'intention
RESPONSE_MODEL = "gpt-4"        # Pour les réponses complexes
TASK_MODEL = "gpt-3.5-turbo"   # Pour l'extraction d'informations simples

# Dictionnaire des capacités des intégrations
INTEGRATION_CAPABILITIES = {
    # Actions communes
    'create_contact': {
        'name': 'Créer un contact',
        'integrations': ['HubSpot', 'Salesforce', 'Zoho CRM', 'Gmail'],
        'required_fields': ['nom', 'email'],
        'optional_fields': ['téléphone', 'entreprise', 'poste']
    },
    'send_email': {
        'name': 'Envoyer un email',
        'integrations': ['Gmail', 'Mailchimp', 'HubSpot Marketing'],
        'required_fields': ['destinataire', 'sujet', 'contenu']
    },
    'create_task': {
        'name': 'Créer une tâche',
        'integrations': ['Trello', 'Asana', 'Slack'],
        'required_fields': ['titre', 'description'],
        'optional_fields': ['date_échéance', 'assigné_à']
    },
    'schedule_meeting': {
        'name': 'Planifier une réunion',
        'integrations': ['Google Calendar', 'HubSpot', 'Salesforce'],
        'required_fields': ['date', 'heure', 'participants']
    },
    'share_document': {
        'name': 'Partager un document',
        'integrations': ['Google Drive', 'Slack'],
        'required_fields': ['document', 'destinataires']
    },
    'create_invoice': {
        'name': 'Créer une facture',
        'integrations': ['QuickBooks', 'Stripe'],
        'required_fields': ['client', 'montant', 'description']
    },
    
    # Intégrations spécifiques
    'HubSpot': {
        'actions': ['create_contact', 'create_deal', 'schedule_meeting', 'send_email'],
        'entities': ['contact', 'entreprise', 'affaire', 'ticket'],
        'keywords': ['crm', 'client', 'prospect', 'pipeline', 'vente']
    },
    'Trello': {
        'actions': ['create_task', 'assign_task', 'create_board', 'create_list'],
        'entities': ['carte', 'tableau', 'liste', 'tâche'],
        'keywords': ['projet', 'kanban', 'tâche', 'assignation']
    },
    'Slack': {
        'actions': ['send_message', 'create_channel', 'share_document'],
        'entities': ['message', 'canal', 'conversation'],
        'keywords': ['communication', 'équipe', 'discussion', 'notification']
    },
    'Gmail': {
        'actions': ['send_email', 'create_draft', 'schedule_email'],
        'entities': ['email', 'brouillon', 'pièce jointe'],
        'keywords': ['mail', 'message', 'envoyer', 'communiquer']
    },
    'Google Drive': {
        'actions': ['upload_file', 'share_document', 'create_folder'],
        'entities': ['document', 'dossier', 'fichier'],
        'keywords': ['stockage', 'partage', 'collaboration', 'fichier']
    },
    'Salesforce': {
        'actions': ['create_contact', 'create_opportunity', 'track_deal'],
        'entities': ['contact', 'opportunité', 'compte', 'lead'],
        'keywords': ['vente', 'pipeline', 'client', 'affaire']
    },
    'QuickBooks': {
        'actions': ['create_invoice', 'track_expense', 'generate_report'],
        'entities': ['facture', 'dépense', 'client', 'paiement'],
        'keywords': ['comptabilité', 'finance', 'facturation', 'paiement']
    }
}

# Dictionnaire des réponses générales (non liées aux intégrations)
GENERAL_RESPONSES = {
    'time': {
        'patterns': ['quelle heure', 'heure actuelle', "l'heure"],
        'response': lambda: f"Il est actuellement {datetime.now().strftime('%H:%M')}.",
    },
    'date': {
        'patterns': ['quel jour', "date aujourd'hui", 'la date'],
        'response': lambda: f"Nous sommes le {datetime.now().strftime('%d/%m/%Y')}.",
    },
    'weather': {
        'patterns': ['météo', "temps qu'il fait", 'température'],
        'response': "Je ne peux pas accéder aux informations météo en temps réel, mais je peux vous aider à configurer une intégration météo si vous le souhaitez.",
    },
    'greeting': {
        'patterns': ['bonjour', 'salut', 'hello', 'coucou'],
        'response': "Bonjour ! Je suis Alya, votre assistant IA. Comment puis-je vous aider aujourd'hui ?",
    },
    'help': {
        'patterns': ['aide', 'help', 'que peux-tu faire', 'fonctionnalités'],
        'response': "Je peux vous aider avec vos intégrations comme Trello, HubSpot, Gmail, etc. Je peux créer des contacts, envoyer des emails, créer des tâches et bien plus encore. Que souhaitez-vous faire ?",
    },
} 