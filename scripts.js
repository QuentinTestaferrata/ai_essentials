document.getElementById('send-btn').addEventListener('click', () => {
    const userInput = document.getElementById('user-input').value;
    if (userInput.trim() === '') return;

    addMessage('user', userInput);
    document.getElementById('user-input').value = '';

    fetch('http://localhost:5000/query', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({ query: userInput })
    })
    .then(response => response.json())
    .then(data => {
        addMessage('bot', data.response);
    })
    .catch(error => {
        console.error('Error:', error);
        addMessage('bot', 'Sorry, something went wrong.');
    });
});

function addMessage(sender, text) {
    const chatMessages = document.getElementById('chat-messages');
    const messageElement = document.createElement('div');
    messageElement.classList.add('message', sender);
    messageElement.innerText = text;
    chatMessages.appendChild(messageElement);
    chatMessages.scrollTop = chatMessages.scrollHeight;
}
