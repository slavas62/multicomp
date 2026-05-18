'use strict';

document.addEventListener('DOMContentLoaded', function() {
    const actionForm = document.querySelector('#changelist-form');
    if (!actionForm) return;

    actionForm.addEventListener('submit', function(e) {
        // Проверяем, выбрано ли действие
        const actionSelect = document.querySelector('select[name="action"]');
        if (actionSelect.value === "") return;

        // Создаем оверлей
        const overlay = document.createElement('div');
        overlay.style.position = 'fixed';
        overlay.style.top = '0';
        overlay.style.left = '0';
        overlay.style.width = '100%';
        overlay.style.height = '100%';
        overlay.style.backgroundColor = 'rgba(255, 255, 255, 0.7)';
		overlay.style.background = 'rgba(255,255,255,0.7) url(/static/admin/img/loading-animation.gif) no-repeat center center';// Добавляем спиннер
        overlay.style.zIndex = '9999';
        overlay.style.display = 'flex';
        overlay.style.justifyContent = 'center';
        overlay.style.alignItems = 'center';
        overlay.style.cursor = 'wait';
        
        // Добавляем текст
        overlay.innerHTML = '<h1 style="color: #444; text-shadow: 0 0 5px #fff, 0 0 10px #fff, 0 0 15px #fff, 0 0 20px #5d3d5d;">Терпение. Идет создание мультивременного композита ...</h1>';
        
        document.body.appendChild(overlay);
        document.body.style.overflow = 'hidden'; // Запрет прокрутки
    });
});
