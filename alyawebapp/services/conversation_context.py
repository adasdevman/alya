class ConversationContext:
    def __init__(self, chat_id: str):
        self.chat_id = chat_id
        self.current_intent = None
        self.missing_params = []
        self.collected_params = {}
        
    def update_context(self, message: str):
        if self.missing_params:
            # Compléter les paramètres manquants
            param = self.missing_params[0]
            self.collected_params[param] = message
            self.missing_params.pop(0)
        else:
            # Analyser une nouvelle intention
            self.current_intent = self.analyze_intent(message)
            self.missing_params = self.get_missing_params()
    
    def is_complete(self) -> bool:
        return len(self.missing_params) == 0