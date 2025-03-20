INTEGRATION_CONFIGS = {
    'Amplitude': {
        'name': 'Amplitude',
        'description': 'Analytics produit',
        'icon': 'fa-chart-line',
        'fields': [
            {
                'name': 'api_key',
                'label': 'Clé API',
                'type': 'password',
                'required': True
            }
        ],
        'category': 'analytics'
    },
    
    'Asana': {
        'name': 'Asana',
        'description': 'Gestion de projet collaborative',
        'icon': 'fa-tasks',
        'fields': [
            {
                'name': 'access_token',
                'label': 'Token d\'accès',
                'type': 'password',
                'required': True
            }
        ],
        'category': 'project_management'
    },

    'HubSpot': {
        'name': 'HubSpot CRM',
        'description': 'Gestion de la relation client',
        'icon': 'fa-users',
        'auth_type': 'oauth2',
        'oauth_config': {
            'authorize_url': 'https://app.hubspot.com/oauth/authorize',
            'token_url': 'https://api.hubapi.com/oauth/v1/token',
            'scope': ['contacts', 'timeline', 'content']
        },
        'category': 'crm',
        'button_config': {
            'text': 'Configurer',
            'class': 'btn btn-dark btn-sm',
            'action': 'configure'
        },
        'auth_provider': 'auth0'
    },

    'Trello': {
        'name': 'Trello',
        'description': 'Gérez vos projets et tâches d\'équipe',
        'icon': 'fab fa-trello',
        'auth_type': 'oauth2',
        'oauth_config': {
            'authorize_url': 'https://trello.com/1/authorize',
            'scope': ['read', 'write', 'account']
        },
        'category': 'project_management',
        'button_config': {
            'text': 'Configurer',
            'class': 'btn btn-dark btn-sm',
            'action': 'configure'
        },
        'auth_provider': 'auth0'
    },

    'Gmail': {
        'name': 'Gmail',
        'description': 'Service de messagerie électronique',
        'icon': 'fa fa-envelope',
        'auth_type': 'oauth2',
        'category': 'communication',
        'button_config': {
            'text': 'Configurer',
            'class': 'btn btn-outline-dark btn-sm',
            'action': 'configure'
        },
        'auth_provider': 'auth0'
    },

    'Salesforce': {
        'name': 'Salesforce',
        'description': 'Plateforme CRM complète',
        'icon': 'fa-cloud',
        'auth_type': 'oauth2',
        'category': 'crm',
        'button_config': {
            'text': 'Configurer',
            'class': 'btn btn-dark btn-sm',
            'action': 'configure'
        },
        'auth_provider': 'auth0'
    },

    'QuickBooks': {
        'name': 'QuickBooks',
        'description': 'Comptabilité',
        'icon': 'fa-calculator',
        'auth_type': 'oauth2',
        'oauth_config': {
            'authorize_url': 'https://appcenter.intuit.com/connect/oauth2',
            'scope': ['com.intuit.quickbooks.accounting']
        },
        'category': 'finance',
        'button_config': {
            'text': 'Configurer',
            'class': 'btn btn-dark btn-sm',
            'action': 'configure'
        },
        'auth_provider': 'auth0'
    },

    'Slack': {
        'name': 'Slack',
        'description': 'Communication interne avec Slack',
        'icon': 'fab fa-slack',
        'auth_type': 'oauth2',
        'category': 'communication',
        'button_config': {
            'text': 'Configurer',
            'class': 'btn btn-outline-dark btn-sm',
            'action': 'configure'
        },
        'auth_provider': 'auth0'
    },

    # Ajout des autres intégrations...
    'Google Analytics': {
        'name': 'Google Analytics',
        'description': 'Analyse web',
        'icon': 'fa-chart-bar',
        'auth_type': 'oauth2',
        'category': 'analytics'
    },

    'Mailchimp': {
        'name': 'Mailchimp',
        'description': 'Email marketing',
        'icon': 'fa-envelope',
        'auth_type': 'oauth2',
        'oauth_config': {
            'authorize_url': 'https://login.mailchimp.com/oauth2/authorize',
            'token_url': 'https://login.mailchimp.com/oauth2/token',
            'scope': ['']
        },
        'button_config': {
            'text': 'Configurer',
            'class': 'btn btn-outline-dark btn-sm',
            'action': 'configure'
        },
        'auth_provider': 'oauth2',
        'category': 'marketing'
    },

    'Stripe': {
        'name': 'Stripe',
        'description': 'Paiements en ligne',
        'icon': 'fa-credit-card',
        'fields': [
            {
                'name': 'secret_key',
                'label': 'Clé secrète',
                'type': 'password',
                'required': True
            },
            {
                'name': 'publishable_key',
                'label': 'Clé publique',
                'type': 'text',
                'required': True
            }
        ],
        'category': 'payment'
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

    'Google Drive': {
        'name': 'Google Drive',
        'description': 'Gestion et partage de documents',
        'icon': 'fab fa-google-drive',
        'auth_type': 'oauth2',
        'category': 'document_management',
        'button_config': {
            'text': 'Configurer',
            'class': 'btn btn-outline-dark btn-sm',
            'action': 'configure'
        },
        'auth_provider': 'auth0'
    },

    'Zoho CRM': {
        'name': 'Zoho CRM',
        'description': 'Solution CRM intégrée',
        'icon': 'fa-users-cog',
        'category': 'crm',
        'button_config': {
            'text': 'Configurer',
            'class': 'btn btn-dark btn-sm',
            'action': 'configure'
        }
    },

    'HubSpot Marketing': {
        'name': 'HubSpot Marketing',
        'description': 'Marketing automation',
        'icon': 'fa-bullhorn',
        'category': 'marketing',
        'button_config': {
            'text': 'Configurer',
            'class': 'btn btn-dark btn-sm',
            'action': 'configure'
        }
    },

    'Mixpanel': {
        'name': 'Mixpanel',
        'description': 'Analyse produit',
        'icon': 'fa-chart-pie',
        'category': 'analytics',
        'button_config': {
            'text': 'Configurer',
            'class': 'btn btn-dark btn-sm',
            'action': 'configure'
        }
    },
}

# Catégories d'intégrations
INTEGRATION_CATEGORIES = {
    'crm': 'Gestion de la relation client',
    'project_management': 'Gestion de projet',
    'communication': 'Communication',
    'analytics': 'Analyse de données',
    'marketing': 'Marketing',
    'finance': 'Finance',
    'payment': 'Paiement',
    'document_management': 'Gestion Documentaire',
    'logistics': 'Logistique',
    'legal': 'Juridique',
    'erp': 'ERP',
    'other': 'Autres',
    'support': 'Support Client',
    'rh': 'Ressources Humaines'
} 