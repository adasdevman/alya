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

    // Event listener pour les boutons de configuration
    const configButtons = document.querySelectorAll('.config-integration');
    configButtons.forEach(button => {
        button.addEventListener('click', function(e) {
            e.preventDefault(); // Empêcher le comportement par défaut
            e.stopPropagation(); // Empêcher la propagation de l'événement
            const integrationId = this.dataset.integrationId;
            openConfigModal(integrationId);
        });
    });

    // Fonction pour récupérer le cookie CSRF
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

    // Gestionnaire d'événements pour les switches d'intégration
    document.querySelectorAll('.integration-switch').forEach(switchElement => {
        switchElement.addEventListener('change', async function() {
            const integrationId = this.dataset.integrationId;
            const enabled = this.checked;
            
            try {
                const response = await fetch('/toggle-integration/', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-CSRFToken': getCookie('csrftoken')
                    },
                    body: JSON.stringify({
                        integration_id: integrationId,
                        enabled: enabled
                    })
                });

                const data = await response.json();
                
                if (data.status === 'warning') {
                    // Si une configuration est requise, ouvrir le modal de configuration
                    openConfigModal(integrationId);
                    showNotification(data.message, 'warning');
                } else if (data.status === 'success') {
                    showNotification(data.message, 'success');
                } else {
                    throw new Error(data.message || 'Une erreur est survenue');
                }
            } catch (error) {
                console.error('Erreur:', error);
                this.checked = !enabled; // Remettre le switch dans son état précédent
                showNotification(error.message, 'danger');
            }
        });
    });

    // Charger l'état initial des intégrations
    async function loadIntegrationsState() {
        try {
            const response = await fetch('/get-integrations-state/');
            const data = await response.json();
            
            if (data.status === 'success') {
                data.integrations.forEach(integration => {
                    const switchEl = document.querySelector(`.integration-switch[data-integration-id="${integration.id}"]`);
                    if (switchEl) {
                        switchEl.checked = integration.enabled;
                    }
                });
            }
        } catch (error) {
            console.error('Erreur lors du chargement des états:', error);
            showNotification('Erreur lors du chargement des états', 'error');
        }
    }

    // Charger l'état initial
    loadIntegrationsState();
}); 