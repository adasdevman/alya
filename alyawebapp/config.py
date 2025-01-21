INTEGRATION_CONFIGS = {
    'mailchimp': {
        'name': 'Mailchimp',
        'description': 'Plateforme de marketing par email',
        'auth_type': 'api_key',
        'optional_config': True,
        'fields': [
            {
                'name': 'api_key',
                'label': 'Clé API Mailchimp',
                'type': 'text',
                'required': True,
                'help_text': 'Trouvez votre clé API dans les paramètres de votre compte Mailchimp'
            },
            {
                'name': 'server_prefix',
                'label': 'Server Prefix',
                'type': 'text',
                'required': True,
                'help_text': 'Le préfixe du serveur se trouve dans votre URL Mailchimp (ex: us19)'
            }
        ]
    },
    'sendinblue': {
        'name': 'Sendinblue',
        'description': 'Plateforme de marketing digital tout-en-un',
        'auth_type': 'api_key',
        'optional_config': True,
        'fields': [
            {
                'name': 'api_key',
                'label': 'Clé API Sendinblue',
                'type': 'text',
                'required': True,
                'help_text': 'Trouvez votre clé API dans les paramètres de votre compte Sendinblue'
            }
        ]
    },
    'hubspot_marketing': {
        'name': 'HubSpot Marketing',
        'description': 'Plateforme de marketing automation',
        'auth_type': 'api_key',
        'optional_config': True,
        'fields': [
            {
                'name': 'api_key',
                'label': 'Clé API HubSpot',
                'type': 'text',
                'required': True,
                'help_text': 'Trouvez votre clé API dans les paramètres de votre compte HubSpot'
            },
            {
                'name': 'pipeline_id',
                'label': 'ID du Pipeline de Vente',
                'type': 'text',
                'required': True,
                'help_text': 'ID du pipeline de vente par défaut'
            }
        ]
    },
    'activecampaign': {
        'name': 'ActiveCampaign',
        'description': 'Plateforme de marketing automation et CRM',
        'auth_type': 'api_key',
        'optional_config': True,
        'fields': [
            {
                'name': 'api_key',
                'label': 'API Key',
                'type': 'text',
                'required': True,
                'help_text': 'Votre clé API ActiveCampaign'
            },
            {
                'name': 'base_url',
                'label': 'URL de base',
                'type': 'text',
                'required': True,
                'help_text': 'URL de votre compte ActiveCampaign'
            }
        ]
    },
    'buffer': {
        'name': 'Buffer',
        'description': 'Gestion des réseaux sociaux',
        'auth_type': 'oauth2',
        'optional_config': True,
        'fields': [
            {
                'name': 'access_token',
                'label': 'Access Token',
                'type': 'text',
                'required': True,
                'help_text': 'Token d\'accès Buffer'
            }
        ]
    },
    'pipedrive': {
        'name': 'Pipedrive',
        'description': 'CRM pour la gestion des ventes',
        'auth_type': 'api_key',
        'optional_config': True,
        'fields': [
            {
                'name': 'api_token',
                'label': 'API Token',
                'type': 'text',
                'required': True,
                'help_text': 'Token API Pipedrive'
            }
        ]
    }
} 