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
		overlay.style.background = 'rgba(255,255,255,0.7) url(/static/admin/img/loading-animation.gif) no-repeat center center';
        overlay.style.zIndex = '9999';
        overlay.style.display = 'flex';
        overlay.style.justifyContent = 'center';
        overlay.style.alignItems = 'center';
        overlay.style.cursor = 'wait';
        
        // Добавляем текст/спиннер
        overlay.innerHTML = '<h1 style="color: #444;">Терпение. Идет создание мультивременного композита ...</h1>';
        
        document.body.appendChild(overlay);
        document.body.style.overflow = 'hidden'; // Запрет прокрутки
    });
});
