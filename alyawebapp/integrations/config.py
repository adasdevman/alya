INTEGRATION_CONFIGS = {
    # Analytics
    'Amplitude': {
        'fields': [
            {
                'name': 'api_key',
                'label': 'Clé API Amplitude',
                'type': 'text',
                'required': False,
                'help_text': 'Optionnel : Votre clé API Amplitude'
            }
        ],
        'documentation_url': 'https://help.amplitude.com/hc/en-us/articles/360058073772-Create-and-manage-API-credentials',
        'optional_config': True
    },
    'Google Analytics': {
        'fields': [
            {
                'name': 'view_id',
                'label': 'View ID',
                'type': 'text',
                'required': True,
                'help_text': 'ID de la vue Google Analytics'
            },
            {
                'name': 'service_account_json',
                'label': 'Service Account JSON',
                'type': 'textarea',
                'required': True,
                'help_text': 'Contenu JSON du compte de service'
            },
            {
                'name': 'tracking_id',
                'label': 'ID de suivi',
                'type': 'text',
                'required': False,
                'help_text': 'Optionnel : Votre ID de suivi Google Analytics'
            }
        ],
        'documentation_url': 'https://developers.google.com/analytics/devguides/reporting/core/v4',
        'auth_type': 'service_account',
        'optional_config': True
    },
    'Mixpanel': {
        'fields': [
            {
                'name': 'project_token',
                'label': 'Jeton de projet',
                'type': 'text',
                'required': False,
                'help_text': 'Optionnel : Votre jeton de projet Mixpanel'
            },
            {
                'name': 'api_secret',
                'label': 'API Secret',
                'type': 'password',
                'required': True,
                'help_text': 'Secret API Mixpanel'
            }
        ],
        'documentation_url': 'https://developer.mixpanel.com/reference/project-token',
        'auth_type': 'api_key',
        'optional_config': True
    },

    # Marketing
    'ActiveCampaign': {
        'fields': [
            {
                'name': 'api_key',
                'label': 'API Key',
                'type': 'password',
                'required': True,
                'help_text': 'Clé API ActiveCampaign'
            },
            {
                'name': 'base_url',
                'label': 'URL de base',
                'type': 'url',
                'required': True,
                'help_text': 'URL de votre compte ActiveCampaign'
            }
        ],
        'documentation_url': 'https://developers.activecampaign.com/reference',
        'auth_type': 'api_key',
        'optional_config': False
    },
    'Buffer': {
        'fields': [
            {
                'name': 'access_token',
                'label': 'Access Token',
                'type': 'password',
                'required': True,
                'help_text': 'Token d\'accès Buffer'
            }
        ],
        'documentation_url': 'https://buffer.com/developers/api',
        'auth_type': 'oauth2',
        'optional_config': False
    },
    'Mailchimp': {
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
                'help_text': 'Préfixe du serveur (ex: us1)'
            }
        ],
        'documentation_url': 'https://mailchimp.com/help/about-api-keys/',
        'auth_type': 'api_key',
        'optional_config': False
    },
    'Sendinblue': {
        'fields': [
            {
                'name': 'api_key',
                'label': 'Clé API Sendinblue',
                'type': 'text',
                'required': True,
                'help_text': 'Trouvez votre clé API dans les paramètres de votre compte Sendinblue'
            }
        ],
        'documentation_url': 'https://developers.sendinblue.com/reference/how-to-get-your-api-key',
        'auth_type': 'api_key',
        'optional_config': False
    },

    # CRM
    'HubSpot': {
        'fields': [
            {
                'name': 'api_key',
                'label': 'Clé API HubSpot',
                'type': 'text',
                'required': True,
                'help_text': 'Trouvez votre clé API dans les paramètres de votre compte HubSpot'
            },
            {
                'name': 'deal_pipeline_id',
                'label': 'ID du Pipeline de Vente',
                'type': 'text',
                'required': True,
                'help_text': 'ID du pipeline de vente dans HubSpot'
            }
        ],
        'documentation_url': 'https://developers.hubspot.com/docs/api/private-apps',
        'auth_type': 'api_key',
        'optional_config': False
    },
    'Pipedrive': {
        'fields': [
            {
                'name': 'api_token',
                'label': 'API Token',
                'type': 'password',
                'required': True,
                'help_text': 'Token API Pipedrive'
            }
        ],
        'documentation_url': 'https://developers.pipedrive.com/',
        'auth_type': 'api_key',
        'optional_config': False
    },
    'Salesforce': {
        'fields': [
            {
                'name': 'username',
                'label': 'Username',
                'type': 'text',
                'required': True,
                'help_text': 'Nom d\'utilisateur Salesforce'
            },
            {
                'name': 'password',
                'label': 'Password',
                'type': 'password',
                'required': True,
                'help_text': 'Mot de passe'
            },
            {
                'name': 'security_token',
                'label': 'Security Token',
                'type': 'password',
                'required': True,
                'help_text': 'Token de sécurité'
            }
        ],
        'documentation_url': 'https://developer.salesforce.com/',
        'auth_type': 'password'
    },

    # Support
    'Freshdesk': {
        'fields': [
            {
                'name': 'domain',
                'label': 'Domain',
                'type': 'text',
                'required': True,
                'help_text': 'Domaine Freshdesk (ex: votre-entreprise.freshdesk.com)'
            },
            {
                'name': 'api_key',
                'label': 'API Key',
                'type': 'password',
                'required': True,
                'help_text': 'Clé API Freshdesk'
            }
        ],
        'documentation_url': 'https://developers.freshdesk.com/',
        'auth_type': 'api_key'
    },
    'Intercom': {
        'fields': [
            {
                'name': 'access_token',
                'label': 'Access Token',
                'type': 'password',
                'required': True,
                'help_text': 'Token d\'accès Intercom'
            }
        ],
        'documentation_url': 'https://developers.intercom.com/',
        'auth_type': 'bearer'
    },
    'Zendesk': {
        'fields': [
            {
                'name': 'subdomain',
                'label': 'Subdomain',
                'type': 'text',
                'required': True,
                'help_text': 'Sous-domaine Zendesk'
            },
            {
                'name': 'email',
                'label': 'Email',
                'type': 'email',
                'required': True,
                'help_text': 'Email administrateur'
            },
            {
                'name': 'api_token',
                'label': 'API Token',
                'type': 'password',
                'required': True,
                'help_text': 'Token API Zendesk'
            }
        ],
        'documentation_url': 'https://developer.zendesk.com/',
        'auth_type': 'basic'
    },

    # Finance
    'QuickBooks': {
        'fields': [
            {
                'name': 'client_id',
                'label': 'Client ID',
                'type': 'text',
                'required': True,
                'help_text': 'ID Client QuickBooks'
            },
            {
                'name': 'client_secret',
                'label': 'Client Secret',
                'type': 'password',
                'required': True,
                'help_text': 'Secret Client QuickBooks'
            },
            {
                'name': 'refresh_token',
                'label': 'Refresh Token',
                'type': 'password',
                'required': True,
                'help_text': 'Token de rafraîchissement'
            }
        ],
        'documentation_url': 'https://developer.intuit.com/app/developer/qbo/docs/develop',
        'auth_type': 'oauth2'
    },
    'Stripe': {
        'fields': [
            {
                'name': 'secret_key',
                'label': 'Secret Key',
                'type': 'password',
                'required': True,
                'help_text': 'Clé secrète Stripe'
            },
            {
                'name': 'publishable_key',
                'label': 'Publishable Key',
                'type': 'text',
                'required': True,
                'help_text': 'Clé publique Stripe'
            }
        ],
        'documentation_url': 'https://stripe.com/docs/api',
        'auth_type': 'api_key'
    },

    # RH
    'BambooHR': {
        'fields': [
            {
                'name': 'subdomain',
                'label': 'Subdomain',
                'type': 'text',
                'required': True,
                'help_text': 'Sous-domaine BambooHR'
            },
            {
                'name': 'api_key',
                'label': 'API Key',
                'type': 'password',
                'required': True,
                'help_text': 'Clé API BambooHR'
            }
        ],
        'documentation_url': 'https://documentation.bamboohr.com/reference',
        'auth_type': 'api_key'
    },
    'Workday': {
        'fields': [
            {
                'name': 'tenant_name',
                'label': 'Tenant Name',
                'type': 'text',
                'required': True,
                'help_text': 'Nom du tenant Workday'
            },
            {
                'name': 'client_id',
                'label': 'Client ID',
                'type': 'text',
                'required': True,
                'help_text': 'ID Client Workday'
            },
            {
                'name': 'client_secret',
                'label': 'Client Secret',
                'type': 'password',
                'required': True,
                'help_text': 'Secret Client Workday'
            }
        ],
        'documentation_url': 'https://developer.workday.com/',
        'auth_type': 'oauth2'
    },

    # Projet
    'Asana': {
        'fields': [
            {
                'name': 'access_token',
                'label': 'Personal Access Token',
                'type': 'password',
                'required': True,
                'help_text': 'Token d\'accès personnel Asana'
            }
        ],
        'documentation_url': 'https://developers.asana.com/docs',
        'auth_type': 'bearer'
    },
    'Jira': {
        'fields': [
            {
                'name': 'domain',
                'label': 'Domain',
                'type': 'text',
                'required': True,
                'help_text': 'Domaine Jira (ex: votre-entreprise.atlassian.net)'
            },
            {
                'name': 'email',
                'label': 'Email',
                'type': 'email',
                'required': True,
                'help_text': 'Email administrateur'
            },
            {
                'name': 'api_token',
                'label': 'API Token',
                'type': 'password',
                'required': True,
                'help_text': 'Token API Jira'
            }
        ],
        'documentation_url': 'https://developer.atlassian.com/cloud/jira/platform/rest/v3/',
        'auth_type': 'basic'
    },

    # Automation
    'Make': {
        'fields': [
            {
                'name': 'api_token',
                'label': 'API Token',
                'type': 'password',
                'required': True,
                'help_text': 'Token API Make'
            },
            {
                'name': 'team_id',
                'label': 'Team ID',
                'type': 'text',
                'required': True,
                'help_text': 'ID de l\'équipe Make'
            }
        ],
        'documentation_url': 'https://www.make.com/en/api-documentation',
        'auth_type': 'api_key'
    },
    'UiPath': {
        'fields': [
            {
                'name': 'tenant_name',
                'label': 'Tenant Name',
                'type': 'text',
                'required': True,
                'help_text': 'Nom du tenant UiPath'
            },
            {
                'name': 'client_id',
                'label': 'Client ID',
                'type': 'text',
                'required': True,
                'help_text': 'ID Client UiPath'
            },
            {
                'name': 'client_secret',
                'label': 'Client Secret',
                'type': 'password',
                'required': True,
                'help_text': 'Secret Client UiPath'
            }
        ],
        'documentation_url': 'https://docs.uipath.com/orchestrator/reference/api-references',
        'auth_type': 'oauth2'
    },
    'Zapier': {
        'fields': [
            {
                'name': 'webhook_url',
                'label': 'Webhook URL',
                'type': 'url',
                'required': True,
                'help_text': 'URL du webhook Zapier'
            }
        ],
        'documentation_url': 'https://platform.zapier.com/docs/api-reference',
        'auth_type': 'webhook'
    },

    # Marketing (ajouts)
    'Facebook Ads': {
        'fields': [
            {
                'name': 'access_token',
                'label': 'Access Token',
                'type': 'password',
                'required': True,
                'help_text': 'Token d\'accès Facebook Ads'
            },
            {
                'name': 'account_id',
                'label': 'Account ID',
                'type': 'text',
                'required': True,
                'help_text': 'ID du compte publicitaire'
            }
        ],
        'documentation_url': 'https://developers.facebook.com/docs/marketing-apis',
        'auth_type': 'oauth2'
    },
    'LinkedIn Ads': {
        'fields': [
            {
                'name': 'access_token',
                'label': 'Access Token',
                'type': 'password',
                'required': True,
                'help_text': 'Token d\'accès LinkedIn'
            },
            {
                'name': 'account_id',
                'label': 'Account ID',
                'type': 'text',
                'required': True,
                'help_text': 'ID du compte publicitaire'
            }
        ],
        'documentation_url': 'https://docs.microsoft.com/en-us/linkedin/marketing/',
        'auth_type': 'oauth2'
    },
    'Twitter Ads': {
        'fields': [
            {
                'name': 'access_token',
                'label': 'Access Token',
                'type': 'password',
                'required': True,
                'help_text': 'Token d\'accès Twitter'
            },
            {
                'name': 'account_id',
                'label': 'Account ID',
                'type': 'text',
                'required': True,
                'help_text': 'ID du compte publicitaire'
            }
        ],
        'documentation_url': 'https://developer.twitter.com/en/docs/twitter-ads-api',
        'auth_type': 'oauth2'
    },

    # Logistique
    'Freightview': {
        'fields': [
            {
                'name': 'api_key',
                'label': 'API Key',
                'type': 'password',
                'required': True,
                'help_text': 'Clé API Freightview'
            }
        ],
        'documentation_url': 'https://www.freightview.com/api-documentation',
        'auth_type': 'api_key'
    },
    'Odoo': {
        'fields': [
            {
                'name': 'url',
                'label': 'URL',
                'type': 'url',
                'required': True,
                'help_text': 'URL de votre instance Odoo'
            },
            {
                'name': 'db',
                'label': 'Database',
                'type': 'text',
                'required': True,
                'help_text': 'Nom de la base de données'
            },
            {
                'name': 'username',
                'label': 'Username',
                'type': 'text',
                'required': True,
                'help_text': 'Nom d\'utilisateur'
            },
            {
                'name': 'api_key',
                'label': 'API Key',
                'type': 'password',
                'required': True,
                'help_text': 'Clé API Odoo'
            }
        ],
        'documentation_url': 'https://www.odoo.com/documentation/15.0/developer/api.html',
        'auth_type': 'api_key'
    },
    'ShipStation': {
        'fields': [
            {
                'name': 'api_key',
                'label': 'API Key',
                'type': 'password',
                'required': True,
                'help_text': 'Clé API ShipStation'
            },
            {
                'name': 'api_secret',
                'label': 'API Secret',
                'type': 'password',
                'required': True,
                'help_text': 'Secret API ShipStation'
            }
        ],
        'documentation_url': 'https://www.shipstation.com/docs/api/',
        'auth_type': 'basic'
    },

    # Legal
    'Clio': {
        'fields': [
            {
                'name': 'client_id',
                'label': 'Client ID',
                'type': 'text',
                'required': True,
                'help_text': 'ID Client Clio'
            },
            {
                'name': 'client_secret',
                'label': 'Client Secret',
                'type': 'password',
                'required': True,
                'help_text': 'Secret Client Clio'
            }
        ],
        'documentation_url': 'https://app.clio.com/api/v4/documentation',
        'auth_type': 'oauth2'
    },
    'LexisNexis': {
        'fields': [
            {
                'name': 'api_key',
                'label': 'API Key',
                'type': 'password',
                'required': True,
                'help_text': 'Clé API LexisNexis'
            },
            {
                'name': 'api_secret',
                'label': 'API Secret',
                'type': 'password',
                'required': True,
                'help_text': 'Secret API LexisNexis'
            }
        ],
        'documentation_url': 'https://developer.lexisnexis.com/',
        'auth_type': 'api_key'
    },

    # Projet (ajout)
    'Trello': {
        'fields': [
            {
                'name': 'api_key',
                'label': 'API Key',
                'type': 'password',
                'required': True,
                'help_text': 'Clé API Trello'
            },
            {
                'name': 'token',
                'label': 'Token',
                'type': 'password',
                'required': True,
                'help_text': 'Token d\'authentification'
            }
        ],
        'documentation_url': 'https://developer.atlassian.com/cloud/trello/rest/',
        'auth_type': 'api_key',
        'actions': {
            'create_task': {
                'name': 'Créer une tâche',
                'description': 'Crée une nouvelle tâche dans Trello',
                'parameters': ['name', 'list_name', 'description', 'due_date', 'assignee']
            },
            'get_overdue_tasks': {
                'name': 'Tâches en retard',
                'description': 'Récupère la liste des tâches en retard',
                'parameters': []
            },
            'create_board': {
                'name': 'Créer un tableau',
                'description': 'Crée un nouveau tableau Trello',
                'parameters': ['name', 'description', 'background_color']
            },
            'create_list': {
                'name': 'Créer une liste',
                'description': 'Crée une nouvelle liste dans un tableau',
                'parameters': ['board_name', 'list_name', 'position']
            },
            'move_card': {
                'name': 'Déplacer une carte',
                'description': 'Déplace une carte vers une autre liste',
                'parameters': ['card_name', 'source_list', 'target_list']
            },
            'add_comment': {
                'name': 'Ajouter un commentaire',
                'description': 'Ajoute un commentaire à une carte',
                'parameters': ['card_name', 'comment']
            },
            'add_checklist': {
                'name': 'Ajouter une checklist',
                'description': 'Ajoute une checklist à une carte',
                'parameters': ['card_name', 'checklist_name', 'items']
            },
            'add_label': {
                'name': 'Ajouter un label',
                'description': 'Ajoute un label à une carte',
                'parameters': ['card_name', 'label_name', 'color']
            },
            'get_board_activity': {
                'name': 'Activité du tableau',
                'description': 'Récupère l\'activité récente d\'un tableau',
                'parameters': ['board_name', 'limit']
            }
        }
    },

    # Marketing (ajouts manquants)
    'Google Ads': {
        'fields': [
            {
                'name': 'client_id',
                'label': 'Client ID',
                'type': 'text',
                'required': True,
                'help_text': 'ID Client Google Ads'
            },
            {
                'name': 'client_secret',
                'label': 'Client Secret',
                'type': 'password',
                'required': True,
                'help_text': 'Secret Client Google Ads'
            },
            {
                'name': 'developer_token',
                'label': 'Developer Token',
                'type': 'password',
                'required': True,
                'help_text': 'Token développeur Google Ads'
            },
            {
                'name': 'refresh_token',
                'label': 'Refresh Token',
                'type': 'password',
                'required': True,
                'help_text': 'Token de rafraîchissement OAuth2'
            },
            {
                'name': 'customer_id',
                'label': 'Customer ID',
                'type': 'text',
                'required': True,
                'help_text': 'ID client Google Ads (sans tirets)'
            }
        ],
        'documentation_url': 'https://developers.google.com/google-ads/api/docs/start',
        'auth_type': 'oauth2'
    },
    'Klaviyo': {
        'fields': [
            {
                'name': 'private_key',
                'label': 'Private API Key',
                'type': 'password',
                'required': True,
                'help_text': 'Clé API privée Klaviyo'
            },
            {
                'name': 'public_key',
                'label': 'Public API Key',
                'type': 'text',
                'required': True,
                'help_text': 'Clé API publique Klaviyo'
            }
        ],
        'documentation_url': 'https://developers.klaviyo.com/',
        'auth_type': 'api_key'
    },

    # Legal (ajout manquant)
    'DocuSign': {
        'fields': [
            {
                'name': 'client_id',
                'label': 'Integration Key',
                'type': 'text',
                'required': True,
                'help_text': 'Clé d\'intégration DocuSign'
            },
            {
                'name': 'client_secret',
                'label': 'Secret Key',
                'type': 'password',
                'required': True,
                'help_text': 'Clé secrète DocuSign'
            },
            {
                'name': 'account_id',
                'label': 'Account ID',
                'type': 'text',
                'required': True,
                'help_text': 'ID du compte DocuSign'
            },
            {
                'name': 'refresh_token',
                'label': 'Refresh Token',
                'type': 'password',
                'required': True,
                'help_text': 'Token de rafraîchissement OAuth'
            }
        ],
        'documentation_url': 'https://developers.docusign.com/',
        'auth_type': 'oauth2'
    },

    # Finance (ajout manquant)
    'Xero': {
        'fields': [
            {
                'name': 'client_id',
                'label': 'Client ID',
                'type': 'text',
                'required': True,
                'help_text': 'ID Client Xero'
            },
            {
                'name': 'client_secret',
                'label': 'Client Secret',
                'type': 'password',
                'required': True,
                'help_text': 'Secret Client Xero'
            },
            {
                'name': 'refresh_token',
                'label': 'Refresh Token',
                'type': 'password',
                'required': True,
                'help_text': 'Token de rafraîchissement OAuth2'
            },
            {
                'name': 'tenant_id',
                'label': 'Tenant ID',
                'type': 'text',
                'required': True,
                'help_text': 'ID du tenant Xero'
            }
        ],
        'documentation_url': 'https://developer.xero.com/',
        'auth_type': 'oauth2'
    },

    # RH (ajout manquant)
    'LinkedIn Recruiter': {
        'fields': [
            {
                'name': 'client_id',
                'label': 'Client ID',
                'type': 'text',
                'required': True,
                'help_text': 'ID Client LinkedIn'
            },
            {
                'name': 'client_secret',
                'label': 'Client Secret',
                'type': 'password',
                'required': True,
                'help_text': 'Secret Client LinkedIn'
            },
            {
                'name': 'access_token',
                'label': 'Access Token',
                'type': 'password',
                'required': True,
                'help_text': 'Token d\'accès LinkedIn Recruiter'
            }
        ],
        'documentation_url': 'https://docs.microsoft.com/en-us/linkedin/talent/',
        'auth_type': 'oauth2'
    },
} 