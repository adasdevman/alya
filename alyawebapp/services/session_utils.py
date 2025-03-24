from datetime import datetime
import uuid
from typing import Dict, Any

class SessionState:
    """Classe pour gérer l'état de la session"""
    def __init__(self, user_id: int):
        self.session_id = str(uuid.uuid4())
        self.user_id = user_id
        self.created_at = datetime.now()
        self.last_activity = datetime.now()
        self.conversation_history = []
        self.current_context = {}
        self.pending_actions = []
        self.integration_states = {}
        self.error_count = 0

    def to_dict(self) -> Dict[str, Any]:
        """Convertit l'état en dictionnaire pour le cache"""
        return {
            'session_id': self.session_id,
            'user_id': self.user_id,
            'created_at': self.created_at.isoformat(),
            'last_activity': self.last_activity.isoformat(),
            'conversation_history': self.conversation_history,
            'current_context': self.current_context,
            'pending_actions': self.pending_actions,
            'integration_states': self.integration_states,
            'error_count': self.error_count
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'SessionState':
        """Crée une instance à partir d'un dictionnaire"""
        instance = cls(data['user_id'])
        instance.session_id = data['session_id']
        instance.created_at = datetime.fromisoformat(data['created_at'])
        instance.last_activity = datetime.fromisoformat(data['last_activity'])
        instance.conversation_history = data['conversation_history']
        instance.current_context = data['current_context']
        instance.pending_actions = data['pending_actions']
        instance.integration_states = data['integration_states']
        instance.error_count = data['error_count']
        return instance 