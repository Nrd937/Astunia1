const messages = [
    "Astunia est en cours de mise à jour...",
    "Astunia est en développement...",
    "Nous revenons bientôt"
];

let index = 0;
const messageElement = document.getElementById("message");

function changeMessage() {
    messageElement.textContent = messages[index];
    index = (index + 1) % messages.length;
}

setInterval(changeMessage, 2500);

// premier message
changeMessage();
