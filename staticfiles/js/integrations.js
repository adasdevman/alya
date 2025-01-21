function showConfigurationModal(integrationId, integrationName) {
    // Récupère la configuration de l'intégration
    fetch(`/api/integration/${integrationId}/config/`)
        .then(response => response.json())
        .then(data => {
            const modal = document.getElementById('integrationConfigModal');
            const configFields = document.getElementById('configFields');
            const integrationNameSpan = document.getElementById('integration-name');
            const integrationIdInput = document.getElementById('integration-id');
            const docLink = document.getElementById('documentation-link');
            
            // Met à jour les éléments de base du modal
            integrationNameSpan.textContent = integrationName;
            integrationIdInput.value = integrationId;
            
            // Vide les champs existants
            configFields.innerHTML = '';
            
            // Génère les champs de formulaire basés sur la configuration
            data.fields.forEach(field => {
                const formGroup = document.createElement('div');
                formGroup.className = 'form-group mb-2';
                
                // Crée le label
                const label = document.createElement('label');
                label.className = 'form-label';
                label.htmlFor = field.name;
                label.textContent = field.label;
                
                // Crée le champ de saisie
                let input;
                if (field.type === 'textarea') {
                    input = document.createElement('textarea');
                    input.rows = 5;
                } else {
                    input = document.createElement('input');
                    input.type = field.type;
                }
                
                input.className = 'form-control';
                input.id = field.name;
                input.name = field.name;
                input.required = field.required;
                
                // Ajoute le texte d'aide si présent
                if (field.help_text) {
                    const helpText = document.createElement('small');
                    helpText.className = 'form-text text-muted mt-1 mb-0';
                    helpText.textContent = field.help_text;
                    formGroup.appendChild(label);
                    formGroup.appendChild(input);
                    formGroup.appendChild(helpText);
                } else {
                    formGroup.appendChild(label);
                    formGroup.appendChild(input);
                }
                
                configFields.appendChild(formGroup);
            });
            
            // Met à jour le lien de documentation
            if (data.documentation_url) {
                docLink.href = data.documentation_url;
                docLink.style.display = 'inline';
            } else {
                docLink.style.display = 'none';
            }
            
            // Pré-remplit les valeurs si elles existent
            if (data.current_config) {
                Object.entries(data.current_config).forEach(([key, value]) => {
                    const input = document.getElementById(key);
                    if (input) {
                        input.value = value;
                    }
                });
            }
            
            // Affiche le modal
            const bsModal = new bootstrap.Modal(modal);
            bsModal.show();
        })
        .catch(error => {
            console.error('Erreur lors du chargement de la configuration:', error);
            showToast('error', 'Erreur lors du chargement de la configuration');
        });
} 