from ..base import BaseIntegration
import asana

class AsanaIntegration(BaseIntegration):
    def validate_config(self):
        required_fields = ['access_token', 'workspace_id']
        for field in required_fields:
            if field not in self.config:
                raise ValueError(f"Configuration manquante: {field}")

    def initialize_client(self):
        try:
            return asana.Client.access_token(self.config['access_token'])
        except Exception as e:
            raise ConnectionError(f"Erreur d'initialisation Asana: {str(e)}")

    def test_connection(self):
        try:
            self.client.users.me()
            return True
        except Exception:
            return False

    def get_tasks(self, project_id):
        """Récupère les tâches d'un projet"""
        return self.client.tasks.find_all({
            'project': project_id,
            'opt_fields': ['name', 'notes', 'completed', 'due_on']
        })

    def create_task(self, name, notes, project_id):
        """Crée une nouvelle tâche"""
        return self.client.tasks.create_task({
            'name': name,
            'notes': notes,
            'projects': [project_id],
            'workspace': self.config['workspace_id']
        }) 