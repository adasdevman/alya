from abc import ABC, abstractmethod

class BaseIntegration(ABC):
    def __init__(self, config):
        self.config = config
        self.validate_config()
        self.client = self.initialize_client()

    @abstractmethod
    def validate_config(self):
        """Valide la configuration de l'intégration"""
        pass

    @abstractmethod
    def initialize_client(self):
        """Initialise le client de l'API"""
        pass

    @abstractmethod
    def test_connection(self):
        """Teste la connexion avec le service"""
        pass 