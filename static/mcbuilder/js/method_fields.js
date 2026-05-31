'use strict';

window.addEventListener('load', function() {
    (function($) {
        $(document).ready(function() {

            function toggleAgregatField() {   // Функция для переключения видимости
//                var selectedStatus = $('#id_method').val();
                var selectedStatus = $('#id_method option:selected').text()

                var agregatField = $('.field-agregat'); // Находим контейнер поля agregat (обычно div.field-имя_поля)
//                if (selectedStatus === '5') {
                if (selectedStatus === 'Многовременной композит') {
                    agregatField.show();
                } else {
                    agregatField.hide();
                }

                var ctypesField = $('.field-ctypes'); // Находим контейнер поля ctypes (обычно div.field-имя_поля)
                var bandsField = $('.field-bands');   // Находим контейнер поля bands (обычно div.field-имя_поля)
//                if (selectedStatus === '6') {
                if (selectedStatus === 'Разностный композит') {
                    ctypesField.show();
                    bandsField.show();
                } else {
                    ctypesField.hide();
                    bandsField.hide();
                }
            }

            toggleAgregatField();  // Запускаем при загрузке

            $('#id_method').change(function() {  // Запускаем при изменении поля status
                toggleAgregatField();
            });
        });
    })(django.jQuery);
});