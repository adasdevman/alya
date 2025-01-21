document.addEventListener('DOMContentLoaded', function() {
    console.log('=== Début initialisation modals.js ===');

    // Vérification de Bootstrap
    console.log('Bootstrap disponible:', typeof bootstrap !== 'undefined');
    console.log('Bootstrap Modal disponible:', typeof bootstrap.Modal !== 'undefined');

    // Initialisation de tous les modals Bootstrap
    var modals = [].slice.call(document.querySelectorAll('.modal'));
    console.log('Nombre de modals trouvés:', modals.length);
    
    modals.forEach(function(modalElement) {
        console.log('Modal trouvé:', {
            id: modalElement.id,
            classes: modalElement.className
        });
        
        try {
            const modalInstance = new bootstrap.Modal(modalElement);
            console.log('Modal initialisé avec succès:', modalElement.id);
            
            // Ajout d'écouteurs d'événements pour le modal
            modalElement.addEventListener('show.bs.modal', function() {
                console.log('Événement show.bs.modal déclenché pour:', this.id);
            });
            
            modalElement.addEventListener('shown.bs.modal', function() {
                console.log('Modal affiché:', this.id);
            });
            
            modalElement.addEventListener('hide.bs.modal', function() {
                console.log('Modal en cours de fermeture:', this.id);
            });
        } catch (error) {
            console.error('Erreur lors de l\'initialisation du modal:', modalElement.id, error);
        }
    });

    // Liste des IDs de modals
    const modalIds = [
        'editDomainsModal',
        'editObjectifsModal',
        'editProfileModal',
        'editTailleModal',
        'integrationsModal',
        'configModal',
        'analyticsModal',
        'marketingModal',
        'crmModal',
        'supportModal',
        'projetModal',
        'rhModal',
        'financeModal',
        'legalModal',
        'logisticModal',
        'automationModal'
    ];

    // Initialisation des modals Bootstrap
    console.log('Initialisation des modals...');
    modalIds.forEach(modalId => {
        const modalElement = document.getElementById(modalId);
        if (modalElement) {
            console.log(`Modal trouvé: ${modalId}`);
            new bootstrap.Modal(modalElement);
        }
    });

    // Gestion des clics sur les secteurs d'activité
    const infoTags = document.querySelectorAll('.info-tag[data-bs-toggle="modal"]');
    console.log(`Nombre de secteurs trouvés: ${infoTags.length}`);
    
    infoTags.forEach(tag => {
        tag.addEventListener('click', function(event) {
            const modalTarget = this.getAttribute('data-bs-target');
            console.log(`Clic sur le secteur. Modal cible: ${modalTarget}`);
            
            const modalElement = document.querySelector(modalTarget);
            if (modalElement) {
                console.log('Modal trouvé, ouverture...');
                const modal = new bootstrap.Modal(modalElement);
                modal.show();
            } else {
                console.error(`Modal non trouvé: ${modalTarget}`);
            }
        });
    });

    // Gestion des clics sur les boutons de configuration d'intégration
    document.querySelectorAll('.config-integration').forEach(button => {
        button.addEventListener('click', function(event) {
            event.preventDefault();
            const integrationId = this.getAttribute('data-integration-id');
            console.log(`Configuration de l'intégration: ${integrationId}`);
            
            // Fermer le modal actuel
            const currentModal = bootstrap.Modal.getInstance(this.closest('.modal'));
            if (currentModal) {
                currentModal.hide();
            }

            // Ouvrir le modal de configuration
            const configModal = document.getElementById('configModal');
            if (configModal) {
                const modal = new bootstrap.Modal(configModal);
                modal.show();
            }
        });
    });

    // Gestion des formulaires
    const forms = {
        'domainsForm': '/update-domains/',
        'objectifsForm': '/update-objectifs/',
        'profileForm': '/update-profile/',
        'tailleForm': '/update-company-size/',
        'configurationForm': '/update-integration-config/'
    };

    Object.entries(forms).forEach(([formId, url]) => {
        const form = document.getElementById(formId);
        if (form) {
            console.log('Form trouvé et initialisé:', formId);
            form.addEventListener('submit', async function(e) {
                e.preventDefault();
                console.log('Soumission du formulaire:', formId);

                try {
                    const formData = new FormData(this);
                    const response = await fetch(url, {
                        method: 'POST',
                        body: formData,
                        headers: {
                            'X-CSRFToken': getCookie('csrftoken')
                        }
                    });

                    const data = await response.json();
                    console.log('Réponse reçue:', data);

                    if (data.status === 'success') {
                        const modalElement = form.closest('.modal');
                        if (modalElement) {
                            const modalInstance = bootstrap.Modal.getInstance(modalElement);
                            if (modalInstance) {
                                console.log('Fermeture du modal après succès:', modalElement.id);
                                modalInstance.hide();
                            }
                        }
                        window.location.reload();
                    } else {
                        throw new Error(data.message || 'Une erreur est survenue');
                    }
                } catch (error) {
                    console.error('Erreur lors de la soumission:', error);
                    alert(error.message);
                }
            });
        } else {
            console.warn('Form non trouvé:', formId);
        }
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

    console.log('=== Fin initialisation modals.js ===');
}); 