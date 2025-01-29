document.addEventListener('DOMContentLoaded', function() {
    // Configuration des intégrations
    const INTEGRATION_CONFIGS = {
        'hubspot crm': {
            auth_type: 'oauth',
            oauth_url: '/integrations/hubspot/oauth/',
            documentation_url: 'https://developers.hubspot.com/docs/api/overview'
        },
        'zoho crm': {
            auth_type: 'api_key',
            fields: [
                { name: 'client_id', label: 'Client ID', type: 'text' },
                { name: 'client_secret', label: 'Client Secret', type: 'password' },
                { name: 'domain', label: 'Domaine', type: 'text' }
            ],
            documentation_url: 'https://www.zoho.com/crm/developer/docs/'
        }
    };

    // Vérifier si on est sur une page avec des intégrations
    const switches = document.querySelectorAll('.integration-switch');
    if (switches.length === 0) {
        console.log('Aucun switch d\'intégration trouvé, arrêt du script');
        return; // Sortir si pas de switches trouvés
    }

    console.log('DOM chargé, ' + switches.length + ' switches trouvés');

    // Gestionnaire de clic pour les secteurs d'activité
    const sectorsCard = document.querySelector('.card:first-child');
    console.log('Carte des secteurs trouvée:', sectorsCard);

    if (sectorsCard) {
        const infoTags = sectorsCard.querySelectorAll('.info-tag');
        console.log('Nombre de tags trouvés:', infoTags.length);

        infoTags.forEach(tag => {
            tag.addEventListener('click', function(e) {
                const domainName = this.querySelector('.info-name').textContent;
                console.log('Chargement des intégrations pour:', domainName);
                
                fetch(`/get-integrations/${domainName}/`, {
                    method: 'GET',
                    headers: {
                        'Cache-Control': 'no-cache',
                        'X-CSRFToken': getCookie('csrftoken')
                    }
                })
                .then(response => response.json())
                .then(data => {
                    console.log('Réponse reçue:', data);
                    if (data.status === 'success') {
                        // Traitement normal des données
                loadIntegrations(domainName);
                    }
                })
                .catch(error => {
                    console.error('Erreur lors du chargement des intégrations:', error);
                    // Ne montrer l'erreur que si ce n'est pas une erreur 404
                    if (!error.message.includes('404')) {
                        showNotification('Erreur lors du chargement des intégrations', 'danger');
                    }
                });
            });
        });
    } else {
        console.warn('Carte des secteurs non trouvée');
    }

    // Fonction pour charger les intégrations
    function loadIntegrations(domainName) {
        console.log('Chargement des intégrations pour le domaine:', domainName);
        const modalElement = document.getElementById(`${domainName.toLowerCase()}Modal`);
        
        if (modalElement) {
            const modal = new bootstrap.Modal(modalElement);
            modal.show();
           
            // Nettoyer le backdrop lors de la fermeture du modal
            modalElement.addEventListener('hidden.bs.modal', function () {
                const backdrop = document.querySelector('.modal-backdrop');
                if (backdrop) {
                    backdrop.remove();
                }
                document.body.classList.remove('modal-open');
                document.body.style.overflow = '';
                document.body.style.paddingRight = '';
            });
        }
    }

    // Fonction pour créer une carte d'intégration
    function createIntegrationCard(id, integration) {
        const div = document.createElement('div');
        div.className = 'domain-card';
        div.innerHTML = `
            <input type="checkbox" 
                   class="domain-checkbox" 
                   name="integrations" 
                   value="${id}"
                   id="integration_${id}"
                   data-integration-name="${integration.name}"
                   ${integration.config ? 'checked' : ''}>
            <label class="domain-label" for="integration_${id}">
                <div class="domain-icon">
                    <i class="${integration.icon}"></i>
                </div>
                <div class="domain-name">${integration.name}</div>
            </label>
            <button type="button" class="btn btn-sm btn-configure" style="display: none;">
                <i class="fas fa-cog"></i> Configurer
            </button>`;

        // Gestionnaire pour afficher le bouton de configuration
        const checkbox = div.querySelector('input[type="checkbox"]');
        const configButton = div.querySelector('.btn-configure');
        
        checkbox.addEventListener('change', function() {
            if (this.checked) {
                configButton.style.display = 'block';
                showConfigurationModal(id, integration);
            } else {
                configButton.style.display = 'none';
            }
        });

        configButton.addEventListener('click', function(e) {
            e.preventDefault();
            showConfigurationModal(id, integration);
        });

        // Si déjà configuré, montrer le bouton
        if (integration.config) {
            configButton.style.display = 'block';
        }

        return div;
    }

    function showConfigurationModal(id, integration) {
        const config = INTEGRATION_CONFIGS[integration.name.toLowerCase()];
        if (!config) {
            console.warn(`Configuration non trouvée pour ${integration.name}`);
            return;
        }

        // Si c'est une intégration OAuth, rediriger directement
        if (config.auth_type === 'oauth' && config.oauth_url) {
            console.log('Redirection OAuth vers:', config.oauth_url);
            window.location.href = config.oauth_url;
            return;
        }

        // Pour les intégrations avec configuration manuelle
        const configModal = new bootstrap.Modal(document.getElementById('integrationConfigModal'));
        document.getElementById('integration-name').textContent = integration.name;
        document.getElementById('integration-id').value = id;
        document.getElementById('configFields').innerHTML = config.fields.map(field => `
            <div class="mb-3">
                <label class="form-label" for="${field.name}">${field.label}</label>
                <input type="${field.type}" 
                       class="form-control" 
                       id="${field.name}" 
                       name="${field.name}"
                       required>
            </div>
        `).join('');

        // Mettre à jour le lien de documentation
        const docLink = document.getElementById('docLink');
        if (docLink && config.documentation_url) {
            docLink.href = config.documentation_url;
        }

        configModal.show();
    }

    function getConfigurationFields(integrationName, existingConfig = null) {
        const configs = {
            'LinkedIn Recruiter': [
                { name: 'api_key', label: 'Clé API', type: 'password' },
                { name: 'organization_id', label: 'ID Organisation', type: 'text' }
            ],
            'Workday': [
                { name: 'tenant_url', label: 'URL du tenant', type: 'url' },
                { name: 'client_id', label: 'Client ID', type: 'text' },
                { name: 'client_secret', label: 'Client Secret', type: 'password' }
            ],
            'BambooHR': [
                { name: 'api_key', label: 'Clé API', type: 'password' },
                { name: 'subdomain', label: 'Sous-domaine', type: 'text' }
            ],
            'Jira': [
                { name: 'domain', label: 'Domaine Jira', type: 'url' },
                { name: 'api_token', label: 'Token API', type: 'password' },
                { name: 'project_key', label: 'Clé du projet', type: 'text' }
            ],
            'Trello': [
                { name: 'api_key', label: 'Clé API', type: 'text' },
                { name: 'token', label: 'Token', type: 'password' },
                { name: 'board_id', label: 'ID du tableau', type: 'text' }
            ],
            'Asana': [
                { name: 'personal_access_token', label: 'Token d\'accès personnel', type: 'password' },
                { name: 'workspace_id', label: 'ID Workspace', type: 'text' },
                { name: 'project_gid', label: 'GID du projet', type: 'text' }
            ],
            'Salesforce': [
                { name: 'instance_url', label: 'URL Instance', type: 'url' },
                { name: 'client_id', label: 'Client ID', type: 'text' },
                { name: 'client_secret', label: 'Client Secret', type: 'password' },
                { name: 'username', label: 'Nom d\'utilisateur', type: 'text' }
            ],
            'HubSpot': [
                { name: 'api_key', label: 'Clé API', type: 'password' },
                { name: 'portal_id', label: 'ID du portail', type: 'text' },
                { name: 'pipeline_id', label: 'ID du pipeline', type: 'text' }
            ],
            'Pipedrive': [
                { name: 'api_token', label: 'Token API', type: 'password' },
                { name: 'company_domain', label: 'Domaine entreprise', type: 'text' },
                { name: 'pipeline_id', label: 'ID du pipeline', type: 'text' }
            ]
        };

        // Configuration par défaut si aucune configuration spécifique n'est trouvée
        const defaultConfig = [
            { name: 'api_key', label: 'Clé API', type: 'password' },
            { name: 'api_url', label: 'URL de l\'API', type: 'url' }
        ];

        const fields = configs[integrationName] || defaultConfig;
        
        if (fields.length === 0) {
            console.warn(`Aucune configuration trouvée pour ${integrationName}, utilisation de la configuration par défaut`);
            return defaultConfig.map(field => createFieldHTML(field, existingConfig));
        }

        return fields.map(field => createFieldHTML(field, existingConfig)).join('');
    }

    function createFieldHTML(field, existingConfig) {
        return `
            <div class="mb-3">
                <label class="form-label" for="${field.name}">${field.label}</label>
                <input type="${field.type}" 
                       class="form-control" 
                       id="${field.name}" 
                       name="config[${field.name}]"
                       value="${existingConfig && existingConfig[field.name] ? existingConfig[field.name] : ''}"
                       required>
            </div>
        `;
    }

    // Gestionnaire pour le formulaire d'intégrations
    const integrationsForm = document.getElementById('integrationsForm');
    if (integrationsForm) {
        integrationsForm.addEventListener('submit', function(e) {
            e.preventDefault();
            const formData = new FormData(this);
            const domainName = document.getElementById('domain-name').textContent;
            formData.append('domain_name', domainName);

            fetch('/update-integrations/', {
                method: 'POST',
                body: formData,
                headers: {
                    'X-CSRFToken': getCookie('csrftoken')
                }
            })
            .then(response => response.json())
            .then(data => {
                if (data.status === 'success') {
                    const modal = bootstrap.Modal.getInstance(document.getElementById('integrationsModal'));
                    if (modal) {
                        modal.hide();
                    }
                    location.reload();
                } else {
                    alert(data.message || 'Une erreur est survenue');
                }
            })
            .catch(error => {
                console.error('Erreur:', error);
                alert('Une erreur est survenue lors de la sauvegarde');
            });
        });
    }

    // Fonction pour charger la configuration d'une intégration
    async function loadIntegrationConfig(integrationId) {
        try {
            console.log('Chargement de la configuration pour l\'intégration:', integrationId);
            
            // Récupérer le nom de l'intégration depuis le bouton
            const button = document.querySelector(`[data-integration-id="${integrationId}"]`);
            const integrationName = button.dataset.integrationName;
            
            // Récupérer la configuration depuis INTEGRATION_CONFIGS
            const config = INTEGRATION_CONFIGS[integrationName];
            if (!config) {
                throw new Error(`Configuration non trouvée pour ${integrationName}`);
            }
            
            console.log('Configuration trouvée:', config);
            
            const configForm = document.getElementById('integrationConfigForm');
            const configFields = document.getElementById('configFields');
            
            // Vider les champs existants
            configFields.innerHTML = '';

            // Ajouter un champ caché pour l'ID de l'intégration
            const hiddenInput = document.createElement('input');
            hiddenInput.type = 'hidden';
            hiddenInput.name = 'integration_id';
            hiddenInput.value = integrationId;
            configFields.appendChild(hiddenInput);
            
            // Ajouter les nouveaux champs
            config.fields.forEach(field => {
                const fieldDiv = document.createElement('div');
                fieldDiv.className = 'mb-3';
                
                const label = document.createElement('label');
                label.className = 'form-label';
                label.textContent = field.label;
                
                const input = document.createElement('input');
                input.type = field.type;
                input.name = field.name;
                input.id = field.name;
                input.className = 'form-control';
                input.required = field.required;
                input.placeholder = field.help_text;
                
                fieldDiv.appendChild(label);
                fieldDiv.appendChild(input);
                configFields.appendChild(fieldDiv);
            });
            
            // Mettre à jour le lien de documentation
            const docLink = document.getElementById('integrationDocLink');
            if (docLink && config.documentation_url) {
                docLink.href = config.documentation_url;
            }
            
            // Afficher le modal
            const configModal = new bootstrap.Modal(document.getElementById('configModal'));
            configModal.show();
            
        } catch (error) {
            console.error('Erreur:', error);
            alert('Erreur lors du chargement de la configuration: ' + error.message);
        }
    }

    // Gérer la soumission du formulaire
    const configForm = document.getElementById('integrationConfigForm');
    if (configForm) {
        configForm.addEventListener('submit', async function(e) {
            e.preventDefault();
            
            // Récupérer le token CSRF
            const csrftoken = getCookie('csrftoken');
            
            // Convertir FormData en objet pour l'envoi
            const formData = new FormData(this);
            const jsonData = {};
            formData.forEach((value, key) => {
                jsonData[key] = value;
            });
            
            try {
                console.log('Envoi des données:', jsonData);
                const response = await fetch('/update-integration-config/', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-CSRFToken': csrftoken
                    },
                    body: JSON.stringify(jsonData)
                });
                
                if (!response.ok) {
                    const errorData = await response.json();
                    throw new Error(errorData.message || 'Erreur lors de la sauvegarde');
                }
                
                const data = await response.json();
                if (data.status === 'success') {
                    // Fermer le modal et rafraîchir la page
                    bootstrap.Modal.getInstance(document.getElementById('configModal')).hide();
                    window.location.reload();
                } else {
                    throw new Error(data.message || 'Erreur lors de la sauvegarde');
                }
            } catch (error) {
                console.error('Erreur:', error);
                alert(error.message);
            }
        });
    }

    // Event listener pour les boutons de configuration
    const configButtons = document.querySelectorAll('.config-integration');
    configButtons.forEach(button => {
        button.addEventListener('click', function(e) {
            e.preventDefault(); // Empêcher le comportement par défaut
            
            // Si c'est une intégration OAuth
            if (this.getAttribute('data-integration-type') === 'oauth') {
                const integrationName = this.closest('.integration-item')
                    .querySelector('.integration-title').textContent.toLowerCase();
                
                if (integrationName === 'hubspot crm') {
                    window.location.href = '/integrations/hubspot/oauth/';
                    return;
                }
            }
            
            // Pour les autres intégrations, afficher le modal de configuration normal
            const integrationId = this.getAttribute('data-integration-id');
            const integrationName = this.closest('.integration-item')
                .querySelector('.integration-title').textContent;
            showConfigurationModal(integrationId, { name: integrationName });
        });
    });

    // Fonction utilitaire pour récupérer le cookie CSRF
    function getCookie(name) {
        let cookieValue = null;
        if (document.cookie && document.cookie !== '') {
            const cookies = document.cookie.split(';');
            for (let i = 0; i < cookies.length; i++) {
                const cookie = cookies[i].trim();
                if (cookie.substring(0, name.length + 1) === (name + '=')) {
                    cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                    break;
                }
            }
        }
        return cookieValue;
    }

    // Fonction pour afficher les notifications
    function showNotification(message, type = 'success') {
        const toast = document.createElement('div');
        toast.className = `toast align-items-center text-white bg-${type} border-0`;
        toast.setAttribute('role', 'alert');
        toast.setAttribute('aria-live', 'assertive');
        toast.setAttribute('aria-atomic', 'true');
        
        toast.innerHTML = `
            <div class="d-flex">
                <div class="toast-body">
                    ${message}
                </div>
                <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast"></button>
            </div>
        `;
        
        const container = document.getElementById('toast-container');
        if (!container) {
            const newContainer = document.createElement('div');
            newContainer.id = 'toast-container';
            newContainer.className = 'toast-container position-fixed top-0 end-0 p-3';
            document.body.appendChild(newContainer);
            newContainer.appendChild(toast);
        } else {
            container.appendChild(toast);
        }
        
        const bsToast = new bootstrap.Toast(toast);
        bsToast.show();
    }

    // Fonction pour charger l'état initial des intégrations
    function loadInitialState() {
        console.log('Chargement de l\'état initial des intégrations');
        // Vérifier que tous les switches sont présents
        const allSwitches = document.querySelectorAll('.integration-switch');
        console.log('Nombre total de switches trouvés:', allSwitches.length);
        allSwitches.forEach(sw => {
            console.log('Switch trouvé:', sw.getAttribute('data-integration-id'));
        });

        fetch('/get-user-integrations-state/', {
            method: 'GET',
            headers: {
                'Cache-Control': 'no-cache',
                'X-CSRFToken': getCookie('csrftoken')
            }
        })
        .then(response => {
            return response.json();
        })
        .then(data => {
            console.log('État des intégrations reçu:', data);
            if (data.status === 'success' && data.enabled_integrations) {
                data.enabled_integrations.forEach(integration_id => {
                    const switchEl = document.querySelector(`input[data-integration-id="${integration_id}"]`);
                    console.log('Recherche du switch pour l\'intégration', integration_id);
                    if (switchEl) {
                        console.log(`Activation de l'intégration ${integration_id}`);
                        switchEl.checked = true;
                    } else {
                        console.warn(`Switch non trouvé pour l'intégration ${integration_id}`);
                    }
                });
            }
        })
        .catch(error => {
            console.error('Erreur détaillée lors du chargement des intégrations:', error);
            // Ne montrer la notification que pour les vraies erreurs réseau
            if (!error.message.includes('HTTP error! status: 404')) {
                showNotification('Erreur lors du chargement des intégrations', 'danger');
            }
        });
    }

    // Gérer les switches d'intégration
    document.querySelectorAll('.integration-switch').forEach(switchEl => {
        switchEl.addEventListener('change', function() {
            const integrationId = this.getAttribute('data-integration-id');
            console.log('Switch basculé:', integrationId, 'Nouvel état:', this.checked);
            
            fetch('/toggle-integration/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': getCookie('csrftoken')
                },
                body: JSON.stringify({
                    integration_id: integrationId,
                    enabled: this.checked
                })
            })
            .then(response => response.json())
            .then(data => {
                if (data.status === 'success') {
                    showNotification(
                        this.checked ? 
                        'L\'intégration a été activée avec succès' : 
                        'L\'intégration a été désactivée'
                    );
                } else {
                    this.checked = !this.checked;
                    showNotification(data.message || 'Une erreur est survenue', 'danger');
                }
            });
        });
    });

    // Charger l'état initial des intégrations au chargement de la page
    loadInitialState();

    // Vérifier que les éléments sont bien trouvés au chargement
    console.log('Switches trouvés:', document.querySelectorAll('.integration-switch').length);
    console.log('Toast container trouvé:', document.getElementById('toast-container'));
}); 