// Fonction pour récupérer le token CSRF (à l'extérieur de DOMContentLoaded)
function getCsrfToken() {
    return document.querySelector('[name=csrfmiddlewaretoken]').value;
}

// Fonction pour gérer l'intégration HubSpot
function toggleHubspotIntegration(button, event) {
    event.preventDefault();
    event.stopPropagation();

    const integrationId = button.dataset.integrationId;
    const buttonText = button.querySelector('.button-text');
    const isEnabled = button.classList.contains('btn-dark');

    // Vérifier d'abord si l'intégration est déjà activée
    fetch('/get-integrations-state/')
    .then(response => response.json())
    .then(data => {
        if (data.status === 'success') {
            const integration = data.integrations.find(i => i.id === parseInt(integrationId));
            
            if (integration && integration.enabled) {
                // Si déjà activée, rediriger directement vers OAuth
                window.location.href = '/integrations/hubspot/oauth/';
            } else {
                // Sinon, activer l'intégration puis rediriger
                return fetch('/toggle-integration/', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-CSRFToken': getCsrfToken()
                    },
                    body: JSON.stringify({
                        integration_id: integrationId,
                        enabled: true
                    })
                });
            }
        }
    })
    .then(response => {
        if (response && !response.ok) {
            throw new Error('Network response was not ok');
        }
        if (response) return response.json();
    })
    .then(data => {
        if (data && data.status === 'success') {
            // Changer l'apparence du bouton
            button.classList.remove('btn-outline-dark');
            button.classList.add('btn-dark');
            buttonText.textContent = 'Connecter';
            
            // Rediriger vers OAuth
            setTimeout(() => {
                window.location.href = '/integrations/hubspot/oauth/';
            }, 500);
        }
    })
    .catch(error => {
        console.error('Error:', error);
        alert('Erreur lors de l\'ajout de l\'intégration');
    });
}

document.addEventListener('DOMContentLoaded', function() {
    let currentIntegrationId = null;

    // Gérer la fermeture des modals
    document.querySelectorAll('.modal').forEach(modal => {
        modal.addEventListener('hidden.bs.modal', function (event) {
            // Ne pas supprimer le backdrop si un autre modal est encore ouvert
            const openModals = document.querySelectorAll('.modal.show');
            if (openModals.length === 0) {
                const backdrop = document.querySelector('.modal-backdrop');
                if (backdrop) {
                    backdrop.remove();
                }
                // Supprimer la classe modal-open du body
                document.body.classList.remove('modal-open');
                // Supprimer le style overflow hidden du body
                document.body.style.overflow = '';
                document.body.style.paddingRight = '';
            }
        });
    });

    // Fonction pour afficher une notification
    function showNotification(message, type = 'success') {
        const notification = document.createElement('div');
        notification.className = `alert alert-${type} alert-dismissible fade show position-fixed top-0 end-0 m-3`;
        notification.style.zIndex = '9999';
        notification.innerHTML = `
            ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        `;
        document.body.appendChild(notification);
        
        // Supprimer la notification après 5 secondes
        setTimeout(() => {
            notification.remove();
        }, 5000);
    }

    // Fonction pour ouvrir le modal de configuration
    async function openConfigModal(integrationId) {
        try {
            currentIntegrationId = integrationId;
            console.log('Chargement de la configuration pour l\'intégration:', integrationId);
            const response = await fetch(`/get-integration-config/${integrationId}/`);
            
            if (!response.ok) {
                console.error('Erreur HTTP:', response.status, response.statusText);
                throw new Error('Erreur lors du chargement de la configuration');
            }
            
            const data = await response.json();
            console.log('Configuration reçue:', data);
            
            // Utiliser le bon ID du modal
            const configModal = document.getElementById('integrationConfigModal');
            if (!configModal) {
                console.error('Modal de configuration non trouvé avec l\'ID integrationConfigModal');
                return;
            }
            
            const formContent = document.getElementById('configFields');
            if (!formContent) {
                console.error('Container des champs de configuration non trouvé');
                return;
            }
            
            // Mettre à jour le nom de l'intégration dans le titre
            const integrationName = document.getElementById('integration-name');
            if (integrationName) {
                integrationName.textContent = data.name || 'Intégration';
            }
            
            // Vider le formulaire
            formContent.innerHTML = '';
            
            // Ajouter un champ caché pour l'ID de l'intégration
            const hiddenInput = document.getElementById('integration-id');
            if (hiddenInput) {
                hiddenInput.value = integrationId;
            }
            
            // Vérifier si nous avons des champs à ajouter
            if (!data.fields || !Array.isArray(data.fields)) {
                console.error('Aucun champ reçu ou format invalide:', data);
                return;
            }
            
            console.log('Génération de', data.fields.length, 'champs');
            
            // Ajouter les champs de configuration
            data.fields.forEach((field, index) => {
                console.log('Génération du champ:', field);
                const div = document.createElement('div');
                div.className = 'mb-3';
                
                const label = document.createElement('label');
                label.className = 'form-label';
                label.textContent = field.label;
                if (field.required) {
                    const required = document.createElement('span');
                    required.className = 'text-danger ms-1';
                    required.textContent = '*';
                    label.appendChild(required);
                }
                
                const input = document.createElement('input');
                input.type = field.type || 'text';
                input.className = 'form-control bg-white';
                input.name = field.name;
                input.id = field.name;
                input.value = data.current_config?.[field.name] || '';
                input.required = field.required || false;
                if (field.help_text) {
                    input.placeholder = field.help_text;
                }
                
                div.appendChild(label);
                div.appendChild(input);
                
                // Ajouter un texte d'aide si présent
                if (field.help_text) {
                    const helpText = document.createElement('small');
                    helpText.className = 'form-text text-muted';
                    helpText.textContent = field.help_text;
                    div.appendChild(helpText);
                }
                
                formContent.appendChild(div);
                console.log('Champ ajouté:', field.name);
            });
            
            // Mettre à jour le lien de documentation
            const docLink = document.getElementById('documentation-link');
            if (docLink && data.documentation_url) {
                docLink.href = data.documentation_url;
                docLink.style.display = 'inline-block';
            } else if (docLink) {
                docLink.style.display = 'none';
            }
            
            // Ouvrir le modal de configuration par-dessus le modal parent
            const modal = new bootstrap.Modal(configModal, {
                backdrop: 'static',
                keyboard: false
            });
            configModal.setAttribute('data-bs-backdrop', 'static');
            configModal.style.zIndex = '1060'; // Assurer que le modal de config est au-dessus
            modal.show();
            
        } catch (error) {
            console.error('Erreur détaillée lors du chargement de la configuration:', error);
            showNotification('Erreur lors du chargement de la configuration', 'danger');
        }
    }

    // Gérer la soumission du formulaire
    const configForm = document.getElementById('configurationForm');
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
                    // Fermer uniquement le modal de configuration
                    bootstrap.Modal.getInstance(document.getElementById('integrationConfigModal')).hide();
                    showNotification('Configuration sauvegardée avec succès');
                } else {
                    throw new Error(data.message || 'Erreur lors de la sauvegarde');
                }
            } catch (error) {
                console.error('Erreur:', error);
                showNotification(error.message, 'danger');
            }
        });
    }

    // Gérer les clics sur les boutons de configuration
    document.querySelectorAll('.config-integration').forEach(btn => {
        btn.addEventListener('click', function(e) {
            const integrationId = this.getAttribute('data-integration-id');
            const switchEl = document.querySelector(`input[data-integration-id="${integrationId}"]`);
            
            if (!switchEl || !switchEl.checked) {
                e.preventDefault();
                alert('Veuillez d\'abord activer l\'intégration avant de la configurer.');
                return;
            }
        });
    });

    // Gérer les switches d'intégration
    document.querySelectorAll('.integration-switch').forEach(switchEl => {
        switchEl.addEventListener('change', function() {
            const integrationId = this.getAttribute('data-integration-id');
            
            fetch('/toggle-integration/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': getCsrfToken()
                },
                body: JSON.stringify({
                    integration_id: integrationId,
                    enabled: this.checked
                })
            })
            .then(response => response.json())
            .then(data => {
                if (!data.status === 'success') {
                    this.checked = !this.checked;
                    console.error('Erreur lors de la mise à jour:', data.message);
                }
            })
            .catch(error => {
                console.error('Erreur:', error);
                this.checked = !this.checked;
            });
        });
    });

    // Charger l'état initial des intégrations
    function loadIntegrationsState() {
        fetch('/get-integrations-state/')
        .then(response => response.json())
        .then(data => {
            if (data.status === 'success') {
                data.integrations.forEach(integration => {
                    const switchEl = document.querySelector(`#switch-${integration.id}`);
                    const configBtn = document.querySelector(`#config-btn-${integration.id}`);
                    console.log('Loading state for integration:', integration.id, integration.enabled); // Debug
                    if (switchEl && configBtn) {
                        switchEl.checked = integration.enabled;
                        configBtn.disabled = !integration.enabled;
                        console.log('Elements found and updated'); // Debug
                    }
                });
            }
        })
        .catch(error => console.error('Erreur lors de l\'initialisation des switches:', error));
    }

    // Charger l'état initial au chargement de la page
    loadIntegrationsState();

    // Fonction pour démarrer l'OAuth HubSpot
    function startHubspotOAuth(button) {
        window.location.href = '/integrations/hubspot/oauth/';
    }
}); 