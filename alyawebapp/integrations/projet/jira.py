from ..base import BaseIntegration
from jira import JIRA

class JiraIntegration(BaseIntegration):
    def validate_config(self):
        required_fields = ['server', 'username', 'api_token']
        for field in required_fields:
            if field not in self.config:
                raise ValueError(f"Configuration manquante: {field}")

    def initialize_client(self):
        try:
            options = {'server': self.config['server']}
            return JIRA(
                options,
                basic_auth=(self.config['username'], self.config['api_token'])
            )
        except Exception as e:
            raise ConnectionError(f"Erreur d'initialisation JIRA: {str(e)}")

    def test_connection(self):
        try:
            self.client.projects()
            return True
        except Exception:
            return False

    def get_issues(self, project_key):
        """Récupère les tickets d'un projet"""
        return self.client.search_issues(f'project={project_key}')

    def create_issue(self, project_key, summary, description, issue_type='Task'):
        """Crée un nouveau ticket"""
        return self.client.create_issue(
            project=project_key,
            summary=summary,
            description=description,
            issuetype={'name': issue_type}
        ) 