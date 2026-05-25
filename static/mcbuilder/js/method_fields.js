'use strict';

window.addEventListener('load', function() {
    (function($) {
        $(document).ready(function() {

            function toggleAgregatField() {   // Функция для переключения видимости
                var selectedStatus = $('#id_method').val();

                var agregatField = $('.field-agregat'); // Находим контейнер поля agregat (обычно div.field-имя_поля)

                if (selectedStatus === '5') {
                    agregatField.show();
                } else {
                    agregatField.hide();
                }
            }

            toggleAgregatField();  // Запускаем при загрузке

            $('#id_method').change(function() {  // Запускаем при изменении поля status
                toggleAgregatField();
            });
        });
    })(django.jQuery);
});