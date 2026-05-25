'use strict';
// Функция переименования кнопки "Choose Folder" на "Выберите папку"

document.addEventListener("DOMContentLoaded", function() {
    var buttons = document.querySelectorAll('.related-lookup'); // укажите правильный CSS-селектор вашей кнопки

	    buttons.forEach(function(button) {
        if (button.textContent.trim() === 'Choose Folder') {
            button.textContent = 'Выберите папку';
        }
    });
});
