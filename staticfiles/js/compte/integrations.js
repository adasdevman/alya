document.addEventListener('DOMContentLoaded', function() {
    console.log('DOM chargé, initialisation du script integrations.js');

    // Gestionnaire de clic pour les secteurs d'activité
    const sectorsCard = document.querySelector('.card:first-child');
    console.log('Carte des secteurs trouvée:', sectorsCard);

    if (sectorsCard) {
        const infoTags = sectorsCard.querySelectorAll('.info-tag');
        console.log('Nombre de tags trouvés:', infoTags.length);

        infoTags.forEach(tag => {
            tag.addEventListener('click', function(e) {
                console.log('Tag cliqué:', this);
                const domainName = this.querySelector('.info-name').textContent;
                console.log('Nom du domaine:', domainName);
                loadIntegrations(domainName);
            });
        });
    } else {
        console.warn('Carte des secteurs non trouvée');
    }

    // Fonction pour charger les intégrations
    function loadIntegrations(domainName) {
        console.log('Chargement des intégrations pour:', domainName);
        
        const modalElement = document.getElementById('integrationsModal');
        console.log('Modal element trouvé:', modalElement);

        fetch(`/get-integrations/${domainName}/`)
            .then(response => {
                console.log('Réponse reçue:', response.status);
                return response.json();
            })
            .then(data => {
                console.log('Données reçues:', data);
                
                if (data.status === 'success') {
                    console.log('Mise à jour du modal avec les données');
                    document.getElementById('domain-name').textContent = domainName;
                    const grid = document.querySelector('#integrationsModal .domains-grid');
                    
                    if (!grid) {
                        console.error('Grid element non trouvé');
                        return;
                    }

                    grid.innerHTML = '';

                    if (!data.integrations || Object.keys(data.integrations).length === 0) {
                        console.log('Aucune intégration disponible');
                        grid.innerHTML = `
                            <div class="text-center text-muted p-3">
                                <i class="fa-solid fa-info-circle"></i>
                                Aucune intégration disponible
                            </div>`;
                    } else {
                        console.log('Création des cartes d\'intégration');
                        Object.entries(data.integrations).forEach(([id, integration]) => {
                            grid.appendChild(createIntegrationCard(id, integration));
                        });
                    }

                    try {
                        console.log('Tentative d\'affichage du modal');
                        const myModal = new bootstrap.Modal(modalElement);
                        myModal.show();
                        console.log('Modal affiché avec succès');
                    } catch (error) {
                        console.error('Erreur lors de l\'affichage du modal:', error);
                    }
                }
            })
            .catch(error => {
                console.error('Erreur fetch:', error);
                alert('Erreur lors du chargement des intégrations');
            });
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
        const configModal = new bootstrap.Modal(document.getElementById('integrationConfigModal'));
        document.getElementById('integration-name').textContent = integration.name;
        document.getElementById('integration-id').value = id;
        document.getElementById('configFields').innerHTML = getConfigurationFields(integration.name, integration.config);
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

    // Gestionnaire pour le formulaire de configuration
    const configForm = document.getElementById('configurationForm');
    if (configForm) {
        configForm.addEventListener('submit', function(e) {
            e.preventDefault();
            const formData = new FormData(this);
            const integrationId = document.getElementById('integration-id').value;

            fetch('/update-integration-config/', {
                method: 'POST',
                body: formData,
                headers: {
                    'X-CSRFToken': getCookie('csrftoken')
                }
            })
            .then(response => response.json())
            .then(data => {
                if (data.status === 'success') {
                    const configModal = bootstrap.Modal.getInstance(document.getElementById('integrationConfigModal'));
                    configModal.hide();
                    // Mettre à jour l'interface si nécessaire
                    document.querySelector(`#integration_${integrationId}`).checked = true;
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

    // Fonction utilitaire pour récupérer le CSRF token
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
}); 