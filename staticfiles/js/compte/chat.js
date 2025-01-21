// Gestion du chat dans la page compte
document.addEventListener('DOMContentLoaded', function() {
    const newChatBtn = document.getElementById('new-chat');
    const chatMessages = document.getElementById('chat-messages');
    
    if (newChatBtn) {
        newChatBtn.addEventListener('click', handleNewChat);
    }

    // Chargement de l'historique
    loadChatHistory();
}); 