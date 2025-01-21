document.addEventListener('DOMContentLoaded', function() {
    const chatForm = document.getElementById('chat-form');
    if (chatForm) {
        chatForm.addEventListener('submit', async function(e) {
            e.preventDefault();
            const prompt = document.getElementById('prompt').value;
            const response = await fetch('/ask-alya/', {
                method: 'POST',
                headers: {
                    'X-CSRFToken': getCookie('csrftoken'),
                },
                body: new FormData(chatForm)
            });
            const data = await response.json();
            // Mettre à jour l'interface avec la réponse
        });
    }
}); 