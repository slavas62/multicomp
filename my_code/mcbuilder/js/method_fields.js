'use strict';

window.addEventListener('load', function() {
    (function($) {
        $(document).ready(function() {

            function toggleAgregatField() {   // Функция для переключения видимости
//                var selectedStatus = $('#id_method').val();
                var selectedStatus = $('#id_method option:selected').text()

                var autolevelsField = $('.field-autolevels').hide();
                if (selectedStatus === 'Синтезированный композит') {
                    autolevelsField.show();
                }

                var agregatField = $('.field-agregat').hide();     // Находим контейнер поля agregat (обычно div.field-имя_поля)
//                if (selectedStatus === '5') {
                if (selectedStatus === 'Многовременной композит') {
                    agregatField.show();
                    autolevelsField.show();
                }

                var ctypesField = $('.field-ctypes').hide();       // Находим контейнер поля ctypes (обычно div.field-имя_поля)
                var bandsField = $('.field-bands').hide();         // Находим контейнер поля bands (обычно div.field-имя_поля)
                if (selectedStatus === 'Разностный композит') {
                    ctypesField.show();
                    bandsField.show();
                }

                var metthreshField = $('.field-metthresh').hide(); // Находим контейнер поля metthresh (обычно div.field-имя_поля)
                var thresholdField = $('.field-threshold').hide(); // Находим контейнер поля threshold (обычно div.field-имя_поля)
                if (selectedStatus === 'Пороговый композит') {
                    metthreshField.show();
                    thresholdField.show();
                    bandsField.show();
                }

                if (selectedStatus === 'Композит по индексу NDVI') {
                }
            }

            toggleAgregatField();  // Запускаем при загрузке

            $('#id_method').change(function() {  // Запускаем при изменении поля status
                toggleAgregatField();
            });
        });
    })(django.jQuery);
});