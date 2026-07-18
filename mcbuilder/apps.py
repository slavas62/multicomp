from django.apps import AppConfig

from osgeo import gdal, gdal_array
from django.contrib import messages
from django.utils.html import format_html

import os
import glob
import numpy as np

import time
import datetime

from pathlib import Path

class McbuilderConfig(AppConfig):
    name = 'mcbuilder'
    verbose_name = 'Создание МВК'

    def ready(self):              # Импортируем сигналы, чтобы они зарегистрировались
        import mcbuilder.signals  # noqa: F401

    def mvc_build(self, modeladmin, request, obj):
        global mad, req
        mad = modeladmin
        req = request
        size_block = 512 # Определим размер блока для построчной обработки
        ext = '.tif'

        outdir = os.environ.get('GEOSERVER_OUTDIR_MULTICOMP', 'media/composite/')

        mad.message_user(req, f'Время начала расчета: {datetime.datetime.now()}', level=messages.WARNING)
        print(f'Директория результата: {outdir}')

        input_files = get_filenames_by_folder_name(obj.files_folder)
        print(f'Исходные файлы из папки {obj.files_folder}: {input_files}')
        if not input_files:
            mad.message_user(req, f"Список файлов исходных данных пуст. Выберите папку с данными.", level=messages.ERROR)
            return False

        if not resamling_files_as_first(input_files, obj.resampl): # проверка необходимости проведения ресэмплинга и ресэмплинг по данным первого файла
            return False

        source_folder = obj.files_folder.name  # Папка результата

#   *** Создание СИНТЕЗИРОВАННОГО композита из двух разновременных снимков ***
        if obj.method.alias == 'sintez':
        # Пример использования:
        # Берём самый яркий 2-ой канал (зеленый) из первого файла, снятого последним
        # и каналы 3,1  (красный и синий) из второго файла, снятого ранее
            output_file = obj.author.username + '_' + source_folder + '_' + obj.method.alias  # "{имя папки}_{метод создания}.tif"  # Файл результата
            created = sintez_composite(
                input_files,
                bands1 = [2],    # это будет красный канал в результирующем файле
                bands2 = [3, 1],
                out_path = outdir + output_file + ext
            )
#   *** Создание композита по данным NDVI из двух разновременных снимков ***
        elif obj.method.alias == 'ndvi':
            output_file = obj.author.username + '_' + source_folder + '_' + obj.method.alias  # "{имя папки}_{метод создания}.tif"  # Файл результата
            created = ndvi_composite(
                input_files,
                bands = [2, 3],    # каналы для расчета NDVI 2 - красный 3 - ближний ИК
                output_path = outdir + output_file + ext
            )
#   *** Создание МНОГОВРЕМЕННОГО композита из нескольких разновременных снимков с различными методами агреации значений пикселей ***
        elif obj.method.alias == 'multitemp':
            agmet = obj.agregat # методы агрегации: 'median', 'mean', 'max', 'min'.
            output_file = obj.author.username + '_' + source_folder + '_' + obj.method.alias + '_' + agmet  # "{имя папки}_{метод создания}.tif"  # Файл результата
            created = multitemp_composite(
                input_files,
                outdir + output_file + ext,
                agmet,
                block_size = size_block
            )
#   *** Создание различных типов РАЗНОСТНОГО композита из нескольких разновременных снимков с различными методами разностей значений пикселей ***
        elif obj.method.alias == 'differеnce':
            agmet = obj.ctypes # 'range'
            if obj.bands == 'rgb':
                bands = [1,2,3]
            elif obj.bands == 'red':
                bands = [1]
            elif obj.bands == 'green':
                bands = [2]
            elif obj.bands == 'blue':
                bands = [3]

            output_file = obj.author.username + '_' + source_folder + '_' + obj.method.alias + '_' + agmet + '_' + obj.bands  # "{имя папки}_{метод создания}.tif"  # Файл результата
            created = differеnce_composite(
                input_files,
                outdir + output_file + ext,
                bands = bands,
                composite_type = agmet,
                block_size = size_block
            )
#   *** Создание различных типов композита по ПОРОГОВОМУ значению из нескольких разновременных снимков с различными методами агрегации значений пикселей ***
        elif obj.method.alias == 'threshold':
            agmet = obj.metthresh  # методы агрегации: 'max', 'mean', 'euclidean', 'sum'.
            threshold=obj.threshold
            if obj.bands == 'rgb':
                bands = [1,2,3]
            elif obj.bands == 'red':
                bands = [1]
            elif obj.bands == 'green':
                bands = [2]
            elif obj.bands == 'blue':
                bands = [3]

            output_file = obj.author.username + '_' + source_folder + '_' + obj.method.alias + '_' + agmet + '_' + obj.bands  # "{имя папки}_{метод создания}.tif"  # Файл результата
            created = threshold_composite(
                input_files,
                outdir + output_file + ext,
                bands = bands,
                threshold = threshold,
                block_size = size_block,
                aggregation = agmet # euclidean, max, sum, mean
            )       
        else:
            mad.message_user(req, f"Этот метод пока не поддерживается: {obj.method.name}", level=messages.ERROR)
            obj.builded = False
            return obj.builded

        obj.builded = created
        if not created: # Выходим если при создании композита возникла ошибка
            return obj.builded

        result_file = output_file + ext # Имя файла композита с расширением

#   *** 1. Улучшающая обработка результата (автоуровни) кроме порогового композита ***
        if obj.autolevels and obj.method.alias != 'threshold':
            apply_autolevels_to_file(
                outdir + output_file + ext,
                outdir + output_file + '_ac' + ext,
                lower_pct=2,
                upper_pct=99,
                block_size=256,
                stretch_mode=obj.autolevels  # 'percentile', 'minmax', 'std', 'adaptive'
            )

            try:
                os.remove(outdir + output_file + ext)
                print("Файл удалён.")
            except FileNotFoundError:
                print("Файл не найден — ничего удалять не нужно.")
            except PermissionError:
                print("Отказано в доступе.")

            result_file = output_file + '_ac' + ext # Имя файла обработанного композита с расширением

#   *** 2. Публикуем слой на геосервере, подключенном к ГИП "Геотрон" ***
        import subprocess
        # Запуск скрипта с аргументами
        if obj.geotron:
            username = os.environ.get('GEOSERVER_DEFAULT_USERNAME', 'admin')
            password = os.environ.get('GEOSERVER_DEFAULT_PASSWORD', 'geoserver')
            result = subprocess.run(
                ['bash', 'static/scripts/geotron_public.sh', result_file, username + ':' + password],
                capture_output=False,
                text=True
            )
            # Вывод результата
            if result.returncode == 0:
                mad.message_user(req, f'Композит {result_file} опубликован на ГИП "Геотрон"')
            else:
                mad.message_user(req, f'Ошибка {result.returncode} публикации композита {result_file}!', level=messages.ERROR)
                obj.geotron = False
#            mad.message_user(req, f'Стандартный вывод: {result.stdout}')
#            mad.message_user(req, f'Ошибки: {result.stderr}')

        obj.mcfile = result_file
        mad.message_user(req, f'Время окончания расчета: {datetime.datetime.now()}', level=messages.WARNING)

        return obj.builded

def get_filenames_by_folder_name(folder):
    import numpy as np

    try:
        # Получаем все файлы в этой папке (и подпапках, если нужно)
        # folder.files — это менеджер связанных файлов
        files = folder.files.all()

        # Создаем список имен файлов
        filepath = [f.path for f in files]
        filenames = [Path(f.path).name for f in files]

        indices = np.argsort(filenames)[::-1] # массив отсортированных индексов массива filenames (сортировка индексов по убыванию имен файлов)
#        indices = np.argsort(filenames)        # массив отсортированных индексов массива filenames (сортировка индексов по возрастанию имен файлов)

        return [filepath[i] for i in indices]
    except:
        return []

gdal.UseExceptions()  # чтобы видеть ошибки GDAL
def reproject_to_match(src_file, target_file, match_file): # Перепроецирование и ресемплинг с помощью GDAL
    """
    Перепроецирует src_file так, чтобы он совпадал с match_file по проекции, размерам, разрешению и extent.
    """
    match_ds = gdal.Open(match_file)

    gt = match_ds.GetGeoTransform()
    width = int(match_ds.RasterXSize)
    height = int(match_ds.RasterYSize)
    xmin = gt[0]
    ymax = gt[3]
    xmax = gt[0] + width * gt[1] + height * gt[2]
    ymin = gt[3] + width * gt[4] + height * gt[5]

    print(f'Размер снимка X Y: {width} x {height}')
    print(f'Разрешение X Y: {gt[1]} - {gt[5]}')
    print(f'xmin={xmin}, ymin={ymin}, xmax={xmax}, ymax={ymax}')

    # Если нужно задать разрешение (например, 30x30 метров) xRes=30, yRes=30,
    # Если нужно задать границы (xmin, ymin, xmax, ymax) outputBounds=(... , ... , ... , ...),
    warp_options = gdal.WarpOptions(
        format='GTiff',
        targetAlignedPixels = True,
        xRes = gt[1],
        yRes = -gt[5],
        width = match_ds.RasterXSize,
        height = match_ds.RasterYSize,
        dstSRS = match_ds.GetProjection(),
        outputBounds = (xmin, ymin, xmax, ymax), # match_ds.GetGeoTransform(),
        resampleAlg='bilinear'                   # gdal.GRA_NearestNeighbour  метод ресемплинга (near, bilinear, cubic, lanczos)
    )
    gdal.Warp(target_file, src_file, options=warp_options)
    match_ds = None

def resamling_files_as_first(input_files, resampl):
    '''
    Ресемплинг файлов с помощью GDAL
    Делает едиными проекцию, размеры, разрешение и extent для всех файлов исходных данных
    '''
    ds_sample = gdal.Open(input_files[0])
    for i in range(1, len(input_files)): # Проверка файлов на соответствие и ресэмлинг
        if resampl:
            reproject_to_match(input_files[i], f'resample{i}.tif', input_files[0])
            input_files[i] = f'resample{i}.tif'
        else:
            ds2 = gdal.Open(input_files[i])
            # Проверяем совпадение размеров, проекции и геотрансформации
            if ds_sample.RasterXSize != ds2.RasterXSize or ds_sample.RasterYSize != ds2.RasterYSize:
                mad.message_user(req, f"Размеры растров не совпадают, включите 'Выполнить ресемплинг'", level=messages.ERROR)
                ds_sample = None
                ds2 = None
                return False
            if ds_sample.GetProjection() != ds2.GetProjection():
                mad.message_user(req, f"Проекции растров не совпадают, включите 'Выполнить ресемплинг'", level=messages.ERROR)
                ds_sample = None
                ds2 = None
                return False
            if ds_sample.GetGeoTransform() != ds2.GetGeoTransform():
                mad.message_user(req, f"Предупреждение: геотрансформации различаются, будет использована трансформация первого файла", level=messages.WARNING)
                ds2 = None
    return True


#   **********************************************************************************
#   *** Функция создания СИНТЕЗИРОВАННОГО композита из двух разновременных снимков ***
#   **********************************************************************************
def sintez_composite(input_files, bands1, bands2, out_path, driver_name='GTiff'):
    """
    Создаёт мультиканальный растр, объединяя указанные каналы из двух разных файлов.

    Параметры:
        input_files (str): массив путей к растрам
        bands1 (list[int]): список индексов каналов (1-базированная индексация) из первого растра
        bands2 (list[int]): список индексов каналов из второго растра
        out_path (str): путь для сохранения результата
        resampl (boolean): ресемплинг с помощью GDAL - единые проекция, размеры, разрешение и extent для всех файлов.
        driver_name (str): драйвер GDAL (по умолчанию 'GTiff')
    """

    # Открываем исходные растры
    ds1 = gdal.Open(input_files[0])
    ds2 = gdal.Open(input_files[1])
    print(input_files)

    # Определяем количество каналов в выходном растре
    num_bands = len(bands1) + len(bands2)

    # Тип данных – берем из первого указанного канала (можно улучшить)
    sample_band = ds1.GetRasterBand(bands1[0])
    data_type = sample_band.DataType

    # Создаём выходной растр
    driver = gdal.GetDriverByName(driver_name)
    out_ds = driver.Create(out_path, ds1.RasterXSize, ds1.RasterYSize, num_bands, gdal.GDT_Byte) # GDT_Byte / GDT_UInt8 = 1 (8-bit unsigned integer)
    out_ds.SetProjection(ds1.GetProjection())
    out_ds.SetGeoTransform(ds1.GetGeoTransform())

    # Последовательная запись каналов из первого файла
    for out_idx, band_idx in enumerate(bands1, start=1):
        src_band = ds1.GetRasterBand(band_idx)
        data = src_band.ReadAsArray()
        if data_type != gdal.GDT_Byte:
            data= normalize_to_255(data)
        out_band = out_ds.GetRasterBand(out_idx)
        out_band.WriteArray(data)
        # Копируем настройки NoData, если есть
        src_nodata = src_band.GetNoDataValue()
        if src_nodata is not None:
            out_band.SetNoDataValue(src_nodata)

    # Запись каналов из второго файла (продолжаем нумерацию)
    offset = len(bands1)
    for out_idx, band_idx in enumerate(bands2, start=1 + offset):
        src_band = ds2.GetRasterBand(band_idx)
        data = src_band.ReadAsArray()
        if data_type != gdal.GDT_Byte:
            data= normalize_to_255(data)
        out_band = out_ds.GetRasterBand(out_idx)
        out_band.WriteArray(data)
        src_nodata = src_band.GetNoDataValue()
        if src_nodata is not None:
            out_band.SetNoDataValue(src_nodata)

    # Закрываем все датасеты
    ds1 = None
    ds2 = None
    out_ds = None

    return True



#   *********************************************************************************************
#   *** Создание композита по изменениям в растительности NDVI из двух разновременных снимков ***
#   *********************************************************************************************
def ndvi_composite(input_files, bands, output_path, driver_name='GTiff'):
    # 1. Открытие разновременных снимков
    ds1 = gdal.Open(input_files[0])
    ds2 = gdal.Open(input_files[1])

    bnum1 = ds1.RasterCount
    bnum2 = ds2.RasterCount

    if bnum1 < 3 and bnum2 < 3:
        mad.message_user(req, f"Отсутствуют красный (3-й) и ближний ИК (4-й) каналы, ndvi будет расчитан по 1-му и 2-му каналам", level=messages.ERROR)
        bands=[1, 2]

    # Предполагаем, что каналы: 1 - Red, 2 - NIR (зависит от вашего композита)
    red1, nir1 = ds1.GetRasterBand(bands[0]).ReadAsArray(), ds1.GetRasterBand(bands[1]).ReadAsArray()
    red2, nir2 = ds2.GetRasterBand(bands[0]).ReadAsArray(), ds2.GetRasterBand(bands[1]).ReadAsArray()

    # 2. Безопасное деление через NumPy (избегаем деления на ноль)
    np.seterr(divide='ignore', invalid='ignore')
    ndvi1 = np.where((nir1 + red1) > 0, (nir1 - red1) / (nir1 + red1), np.nan)
    ndvi2 = np.where((nir2 + red2) > 0, (nir2 - red2) / (nir2 + red2), np.nan)

    # 3. Выявление изменений
    ndvi_diff = ndvi2 - ndvi1
    ndvi_diff = np.nan_to_num(ndvi_diff, nan=0.0, posinf=0.0, neginf=0.0)

    # 4. Сохранение результата (используем геопривязку от первого снимка)
    driver = gdal.GetDriverByName(driver_name)
    out_ds = driver.Create(output_path, ds1.RasterXSize, ds1.RasterYSize, 1, gdal.GDT_Byte) # gdal.GDT_Float32
    out_ds.SetGeoTransform(ds1.GetGeoTransform())
    out_ds.SetProjection(ds1.GetProjection())

    ndvi_diff = normalize_to_255(ndvi_diff)

    out_band = out_ds.GetRasterBand(1)
    out_band.WriteArray(ndvi_diff)
#    out_band.SetNoDataValue(np.nan)

#    img_min = ndvi_diff.min()
#    img_max = ndvi_diff.max()
#    print(img_min, img_max)

    out_band.FlushCache()
    out_ds.FlushCache()

    # Закрываем все датасеты
    ds1 = None
    ds2 = None
    out_ds = None

    return True


#   ****************************************************************************************************************************************
#   *** Функция создания МНОГОВРЕМЕННОГО композита из нескольких разновременных снимков с различными методами агреации значений пикселей ***
#   ****************************************************************************************************************************************
def multitemp_composite(input_files, output_file, method='median', block_size=512):
    """
    Создаёт мультивременной композит из списка входных растров.
    Параметры:
        input_files (list): список путей к входным растрам (одинакового размера и проекции).
        output_file (str): путь к выходному растру.
        method (str): метод агрегации: 'median', 'mean', 'max', 'min'.
    """

   # Открываем первый файл для получения метаданных
    ds_ref = gdal.Open(input_files[0], gdal.GA_ReadOnly)
    if ds_ref is None:
        mad.message_user(req, f"Не удалось открыть {input_files[0]}", level=messages.ERROR)
        return False

    cols = ds_ref.RasterXSize
    rows = ds_ref.RasterYSize
    bands = ds_ref.RasterCount
    projection = ds_ref.GetProjection()
    geotransform = ds_ref.GetGeoTransform()

    # Выбираем тип данных (можно задать вручную, здесь сохраняем как Float32)
    out_dtype = gdal.GDT_Byte # GDT_Float32 это тип значений пикселов одного банда выходного растра

    # Создаём выходной файл
#    driver = gdal.GetDriverByName('ECW')
#    compression = 10
#    out_ds = driver.Create(output_file, cols, rows, bands, out_dtype, options=[f"TARGET={compression}"])

    driver = gdal.GetDriverByName('GTiff')
    out_ds = driver.Create(output_file, cols, rows, bands, out_dtype, options=['COMPRESS=LZW'])
    out_ds.SetProjection(projection)
    out_ds.SetGeoTransform(geotransform)

    # Открываем все входные файлы
    datasets = [gdal.Open(f, gdal.GA_ReadOnly) for f in input_files]

    try:
        for band_idx in range(1, bands + 1):
            band_out = out_ds.GetRasterBand(band_idx)

            # Обрабатываем по блокам строк
            for row in range(0, rows, block_size):
                n_rows = min(block_size, rows - row)

                # Собираем данные из всех файлов для текущей полосы
                stack = []
                for ds in datasets:
                    band = ds.GetRasterBand(band_idx)
                    data = band.ReadAsArray(0, row, cols, n_rows).astype(np.float32)
                    stack.append(data)

                stack = np.array(stack)   # Стек: (n_files, n_rows, cols)

                # Агрегация по оси времени (первая ось)
                if method == 'median':
                    composite = np.median(stack, axis=0)
                elif method == 'mean':
                    composite = np.mean(stack, axis=0)
                elif method == 'max':
                    composite = np.max(stack, axis=0)
                elif method == 'min':
                    composite = np.min(stack, axis=0)
                else:
                    mad.message_user(req, f"Неподдерживаемый метод: {method}", level=messages.ERROR)

                # Запись блока
                band_out.WriteArray(composite, 0, row)

            # Очистка блока (необязательно)
            band_out.FlushCache()
    finally:
        # Закрываем все файлы
        for ds in datasets:
            ds = None
        out_ds = None
        ds_ref = None
        return True



# *****************************************************************************************************************************************************
# *** Функция создания различных типов РАЗНОСТНОГО композита из нескольких разновременных снимков с различными методами разностей значений пикселей ***
# *****************************************************************************************************************************************************
def differеnce_composite(input_files, output_path, bands=None, composite_type='range', block_size=512):
    """
    Расширенная версия с поддержкой многополосных файлов и разными типами композитов

    Параметры:
    input_files (list): Список входных файлов
    output_path (str): Путь для сохранения
    bands (list): Список полос для обработки (None - все полосы)
    composite_type (str): 'range', 'std', 'coefficient_of_variation', 'difference_sum'
    block_size (int): Размер блока
    """

    # Открываем первый файл для метаданных
    ds1 = gdal.Open(input_files[0])
    cols = ds1.RasterXSize
    rows = ds1.RasterYSize
    geotransform = ds1.GetGeoTransform()
    projection = ds1.GetProjection()

    if bands is None:
        bands = list(range(1, ds1.RasterCount + 1))

    # Проверяем, что все файлы имеют одинаковое количество полос
    for file_path in input_files:
        ds = gdal.Open(file_path)
        if ds.RasterCount != ds1.RasterCount:
            mad.message_user(req, f"Предупреждение: {file_path} имеет {ds.RasterCount} полос, ожидалось {ds1.RasterCount}", level=messages.WARNING)
        ds = None

    # Создаем выходной файл (столько же полос, сколько входных)
    driver = gdal.GetDriverByName('GTiff')
    out_ds = driver.Create(
        output_path, cols, rows, len(bands),
        gdal.GDT_Byte, # GDT_Float32,
        options=['COMPRESS=LZW', 'TILED=YES', 'BIGTIFF=IF_SAFER']
    )
    out_ds.SetGeoTransform(geotransform)
    out_ds.SetProjection(projection)

    # Настраиваем выходные полосы
    out_bands = []
    for i, band_num in enumerate(bands, 1):
        out_band = out_ds.GetRasterBand(i)
        out_band.SetNoDataValue(-9999)
        out_band.SetDescription(f"Band_{band_num}_{composite_type}")
        out_bands.append(out_band)

    # Вычисляем количество блоков
    num_blocks = (rows + block_size - 1) // block_size

    # Обрабатываем каждый блок
    for y_start in range(0, rows, block_size):
        y_end = min(y_start + block_size, rows)
        block_rows = y_end - y_start

        # Для каждой полосы обрабатываем отдельно
        for band_idx, band_num in enumerate(bands):
            # Читаем текущую полосу из всех файлов для этого блока
            block_stack = []

            for file_path in input_files:
                ds = gdal.Open(file_path)
                data = ds.GetRasterBand(band_num).ReadAsArray(
                    0, y_start, cols, block_rows
                ).astype(np.float32)

                nodata = ds.GetRasterBand(band_num).GetNoDataValue()
                if nodata is not None:
                    data = np.where(data == nodata, np.nan, data)

                block_stack.append(data)
                ds = None

            # Создаем 3D массив
            block_3d = np.stack(block_stack, axis=0)

            # Вычисляем нужную статистику
            if composite_type == 'range':                      # Размах по временному ряду
                # Размах (max - min)
                result = np.nanmax(block_3d, axis=0) - np.nanmin(block_3d, axis=0)
            elif composite_type == 'std':                      # Стандартное отклонение
                # Стандартное отклонение
                result = np.nanstd(block_3d, axis=0)
            elif composite_type == 'cov': # Показывает относительную изменчивость
                # Коэффициент вариации (std/mean) * 100
                mean_vals = np.nanmean(block_3d, axis=0)
                std_vals = np.nanstd(block_3d, axis=0)
                result = np.divide(std_vals, mean_vals,
                                  out=np.full_like(std_vals, np.nan),
                                  where=mean_vals > 0) * 100
            elif composite_type == 'sum':           # Сумма абсолютных разностей последовательных снимков
                total_diff = np.zeros((block_rows, cols), dtype=np.float32)
                for i in range(len(block_stack) - 1):
                    diff = np.abs(block_stack[i+1] - block_stack[i])
                    total_diff += np.nan_to_num(diff, nan=0)
                result = total_diff / (len(block_stack) - 1)   # Средняя абсолютная разность
            else:
                mad.message_user(req, f"Неизвестный тип композита: {composite_type}", level=messages.ERROR)
                ds1 = None
                return False

            # Заменяем NaN на NoData
            result = np.nan_to_num(result, nan=-9999)

            # Записываем блок
            out_bands[band_idx].WriteArray(result, 0, y_start)

        # Очищаем память
        del block_stack, block_3d, result

    out_ds.FlushCache()
    ds1 = None
    out_ds = None
#    mad.message_user(req, f"\nКомпозит типа '{composite_type}' сохранён в {output_path}", level=messages.SUCCESS)
    return True



# ************************************************************************************************************************************************
# *** Функция создания композита по ПОРОГОВОМУ значению из нескольких разновременных снимков с различными методами агрегации значений пикселей ***
# ************************************************************************************************************************************************
def threshold_composite(input_files, output_path,
    bands=[1, 2, 3],  # какие каналы использовать (1-based индексы)
    threshold=50,     # порог для изменений
    block_size=512,   # размер блока (512x512 пикселей)
    aggregation='max' # как объединять каналы: 'max', 'mean', 'sum'
):
    """
    Поблочное обнаружение изменений для многоканальных изображений
    
    Алгоритм:
    1. Разбивает изображение на блоки
    2. Для каждого блока читает все указанные каналы из обоих снимков
    3. Вычисляет разность по каждому каналу
    4. Агрегирует разности в одну карту изменений
    5. Применяет порог
    6. Записывает результат
    """
    
    # Открываем оба датасета
    ds1 = gdal.Open(input_files[0])
    ds2 = gdal.Open(input_files[1])
    
    if ds1 is None or ds2 is None:
        raise FileNotFoundError("Не удалось открыть одно из изображений")
    
    # Получаем информацию о размерах и проекции
    cols = ds1.RasterXSize
    rows = ds1.RasterYSize
    geotransform = ds1.GetGeoTransform()
    projection = ds1.GetProjection()
    
    # Проверяем, что размеры совпадают
    if ds2.RasterXSize != cols or ds2.RasterYSize != rows:
        mad.message_user(req, f"Размеры растров не совпадают, включите 'Выполнить ресемплинг'", level=messages.ERROR)
        ds1 = None
        ds2 = None
        return False
    
    # Проверяем, что каналы существуют
    n_bands = ds1.RasterCount
    for band in bands:
        if band > n_bands:
            mad.message_user(req, f"Канал {band} отсутствует (каналов всего {n_bands})", level=messages.ERROR)
            ds1 = None
            ds2 = None
            return False
    
    # Создаем выходной файл
    driver = gdal.GetDriverByName('GTiff')
    out_ds = driver.Create(
        output_path, cols, rows, 1, gdal.GDT_Byte  # 1 канал, 8-bit
    )
    out_ds.SetGeoTransform(geotransform)
    out_ds.SetProjection(projection)
    out_band = out_ds.GetRasterBand(1)
    '''
    print(f"Размер изображения: {rows} x {cols}")
    print(f"Обработка каналов: {bands}")
    print(f"Размер блока: {block_size}x{block_size}")
    print("Начинается поблочная обработка...")
    '''
    # Счетчики для прогресса
    total_blocks = ((rows + block_size - 1) // block_size) * ((cols + block_size - 1) // block_size)
    start_time = time.time()
    
    # Цикл по блокам
    for y in range(0, rows, block_size):
        # Вычисляем высоту текущего блока (последний может быть меньше)
        ysize = min(block_size, rows - y)
        
        for x in range(0, cols, block_size):
            xsize = min(block_size, cols - x)
            
            # --- 1. Читаем все каналы для первого изображения ---
            img1_block = []
            for band_idx in bands:
                band = ds1.GetRasterBand(band_idx)
                data = band.ReadAsArray(x, y, xsize, ysize).astype(np.float32)
                img1_block.append(data)
            
            # --- 2. Читаем все каналы для второго изображения ---
            img2_block = []
            for band_idx in bands:
                band = ds2.GetRasterBand(band_idx)
                data = band.ReadAsArray(x, y, xsize, ysize).astype(np.float32)
                img2_block.append(data)
            
            # --- 3. Вычисляем разности для всех каналов ---
            # Вариант A: Евклидово расстояние (эффективно, если каналы сравнимы)
            # Вариант B: Сумма абсолютных разностей
            # Вариант C: Максимальная разность по каналам
            
            if aggregation == 'euclidean':
                # Евклидово расстояние в пространстве каналов
                squared_diff_sum = np.zeros((ysize, xsize), dtype=np.float32)
                for band1, band2 in zip(img1_block, img2_block):
                    squared_diff_sum += (band1 - band2) ** 2
                diff_block = np.sqrt(squared_diff_sum)
                
            elif aggregation == 'sum':
                # Сумма абсолютных разностей (SAD)
                diff_block = np.zeros((ysize, xsize), dtype=np.float32)
                for band1, band2 in zip(img1_block, img2_block):
                    diff_block += np.abs(band1 - band2)
                    
            elif aggregation == 'max':
                # Максимальная разность по каналам (изменение в любом канале)
                diff_block = np.zeros((ysize, xsize), dtype=np.float32)
                for band1, band2 in zip(img1_block, img2_block):
                    diff_block = np.maximum(diff_block, np.abs(band1 - band2))
                    
            elif aggregation == 'mean':
                # Средняя абсолютная разность
                diff_block = np.zeros((ysize, xsize), dtype=np.float32)
                for band1, band2 in zip(img1_block, img2_block):
                    diff_block += np.abs(band1 - band2)
                diff_block /= len(bands)
            
            # --- 4. Применяем порог ---
           # change_block = np.zeros((ysize, xsize), dtype=np.uint8)
           # change_block[diff_block > threshold] = 255  # 255 для визуализации
            
            # --- 5. Записываем блок ---
            out_band.WriteArray(diff_block, x, y)

    out_ds.FlushCache()

    threshold = threshold_color_table(out_band, threshold)

    out_band.FlushCache()
    ds1 = None
    ds2 = None
    out_ds = None

    elapsed = time.time() - start_time
#    print(f"Обработка завершена за {elapsed:.2f} секунд")
#    print(f"Результат сохранен в: {output_path}")

    return True


def threshold_color_table(band, threshold):
    """
    Принимает band, делит значения по порогу (arr или 255)
    и накладывает индексированную цветовую палитру.
    """
    # 1. Бинаризация данных через NumPy
    arr = band.ReadAsArray()
#    arr = normalize_to_255(arr)
#    print(arr)

    if arr is None:
        raise RuntimeError("Не удалось прочитать массив данных из растра")
        return False

    if threshold == 0:
#        threshold = round(mean_std_threshold(arr))
        method = 'mean_std'
        threshold = round(calculate_mean_threshold(arr, method=method))
    print(f"threshold: {method} {threshold}")

    arr = np.where(arr > threshold, 255, arr).astype(np.uint8)

    # 2. Создание и настройка таблицы цветов
    color_table = gdal.ColorTable()
    color_table.SetColorEntry(0, (0, 0, 0, 255))      # 0 -> Черный
    color_table.SetColorEntry(255, (255, 0, 0, 255))  # 255 -> красный

    # Заполняем промежуточные индексы серым цветом
    for i in range(1, 255-1):
        color_table.SetColorEntry(i, (i, i, i, 255))

    '''
    # 2. Формируем color table как диапазоны "радуги" (значения от 0 до 255)
    # От синего к зеленому
    color_table.CreateColorRamp(0, (0, 0, 255), 64, (0, 255, 255))
    # От зеленого к желтому
    color_table.CreateColorRamp(64, (0, 255, 255), 128, (0, 255, 0))
    # От желтого к красному
    color_table.CreateColorRamp(128, (0, 255, 0), 192, (255, 255, 0))
    # От красного к фиолетовому
    color_table.CreateColorRamp(192, (255, 255, 0), 254, (255, 0, 255))
    '''
    # 3. Применяем палитру и тип интерпретации цвета
    band.SetRasterColorTable(color_table)
    band.SetRasterColorInterpretation(gdal.GCI_PaletteIndex)

    # Записываем измененный массив обратно в канал
    band.WriteArray(arr)

    return threshold

@staticmethod
def mean_std_threshold(data: np.ndarray, factor: float = 2.0) -> float:
    """
    Расчет порога по результату = среднее + factor * стандартное отклонение.
    """
    data = data[~np.isnan(data)]
    if len(data) == 0:
        return 0.0
        
    return float(np.mean(data) + factor * np.std(data))

def calculate_mean_threshold(data: np.ndarray, n_factor: float = 2.0, method='mean_std'):
    # ========================================================================
    # РАСЧЕТ ПОРОГА
    # ========================================================================

    # Базовые статистики
    mean_val = np.mean(data)
    median_val = np.median(data)
    std_val = np.std(data)
    mad_val = np.median(np.abs(data - median_val))
    percentile_90 = np.percentile(data, 90)
    percentile_95 = np.percentile(data, 95)

    # Расчет порога в зависимости от метода
    if method == 'mean_only':
        threshold = mean_val
    elif method == 'mean_std':
        threshold = mean_val + n_factor * std_val
    elif method == 'mean_median':
        threshold = mean_val + n_factor * abs(mean_val - median_val)
    elif method == 'mean_mad':
        threshold = mean_val + n_factor * mad_val
    elif method == 'mean_percentile':
        # Используем процентиль как меру разброса
        perc = min(95, max(80, 100 - (100 - n_factor * 10)))
        perc_val = np.percentile(data, perc)
        threshold = mean_val + 0.5 * (perc_val - mean_val)
    elif method == 'mean_trimmed':
        # Усеченное среднее (отбрасываем n_factor процентов)
        trim = min(n_factor * 5, 25)
        lower = np.percentile(data, trim)
        upper = np.percentile(data, 100 - trim)
        trimmed_data = data[(data >= lower) & (data <= upper)]
        if len(trimmed_data) > 0:
            threshold = np.mean(trimmed_data)
        else:
            threshold = mean_val
    elif method == 'mean_weighted':
        # Экспоненциальные веса (приоритет высоких значений)
        sorted_data = np.sort(data)
        n = len(sorted_data)
        weights = np.exp(np.linspace(0, 1, n) * n_factor)
        weighted_mean = np.average(sorted_data, weights=weights)
        threshold = weighted_mean
    elif method == 'mean_robust':
        # Робастная оценка методом Хубера
        def huber_mean(x, c=1.345):
            mu = np.median(x)
            for _ in range(10):
                residuals = x - mu
                w = np.where(np.abs(residuals) < c, 1, c / (np.abs(residuals) + 1e-10))
                mu_new = np.sum(w * x) / (np.sum(w) + 1e-10)
                if abs(mu_new - mu) < 1e-6:
                    break
                mu = mu_new
            return mu

        robust_mean = huber_mean(data)
        robust_std = np.std(data)
        threshold = robust_mean + n_factor * robust_std
    elif method == 'mean_bimodal':
        # Для бимодальных распределений
        try:
            from sklearn.mixture import GaussianMixture

            # Ресемплинг для ускорения
            if len(data) > 10000:
                sample = np.random.choice(data, 10000, replace=False)
            else:
                sample = data

            gmm = GaussianMixture(n_components=2, random_state=42)
            gmm.fit(sample.reshape(-1, 1))
            means = gmm.means_.flatten()
            stds = np.sqrt(gmm.covariances_).flatten()
            weights = gmm.weights_.flatten()

            # Порог = взвешенное среднее между классами
            threshold = np.average(means, weights=weights)

        except:
            # Если GMM не работает, используем mean_std
            threshold = mean_val + n_factor * std_val
    else:
        raise ValueError(f"Неизвестный метод: {method}")

    # Ограничиваем порог разумными пределами
    threshold = np.clip(threshold, np.percentile(data, 5), np.percentile(data, 99))

    # Статистика
    stats = {
        'method': method,
        'n_factor': n_factor,
        'threshold': threshold,
        'mean': mean_val,
        'median': median_val,
        'std': std_val,
        'mad': mad_val,
        'percentile_90': percentile_90,
        'percentile_95': percentile_95,
        'min': np.min(data),
        'max': np.max(data)
    }

    return threshold

def normalize_to_255(image):
    """
    Нормирует массив изображения в диапазон [0, 255] и приводит к типу uint8.
    GDT_Byte / GDT_UInt8 = 1 (8-bit unsigned integer)
    GDT_Int8 = 14 (8-bit signed integer)
    GDT_UInt16 = 2 (16-bit unsigned integer)
    GDT_Int16 = 3 (16-bit signed integer)
    GDT_UInt32 = 4 (32-bit unsigned integer)
    GDT_Int32 = 5 (32-bit signed integer)
    GDT_Float32 = 6 (32-bit floating point)
    GDT_Float64 = 7 (64-bit floating point)
    """
    # Переводим во float для точности вычислений
    img_float = image.astype(np.float32)

    img_min = img_float.min()
    img_max = img_float.max()

    # Защита от деления на ноль, если изображение одноцветное
    if img_max == img_min:
        return np.zeros_like(image, dtype=np.uint8)

    # Линейное масштабирование
    normalized = (img_float - img_min) * (255.0 / (img_max - img_min))

    # Округление до ближайшего целого и приведение к uint8
    return np.rint(normalized).astype(np.uint8)

def apply_autolevels_to_file(input_path, output_path,
                            lower_pct=2, upper_pct=98,
                            block_size=512, output_dtype=None,
                            stretch_mode='percentile'):
    """
    Применяет автоуровни (растяжку контраста) к существующему растровому файлу

    Parameters:
    input_path (str): Путь к входному файлу
    output_path (str): Путь для сохранения результата
    lower_pct (float): Нижний процентиль (по умолчанию 2)
    upper_pct (float): Верхний процентиль (по умолчанию 98)
    block_size (int): Размер блока для построчной обработки
    output_dtype (int): Тип выходных данных (None - сохраняет исходный тип)
    stretch_mode (str): 'percentile', 'minmax', 'std', 'adaptive'

    Returns:
    dict: Параметры автоуровней (min, max, lower, upper)
    """

    # Открываем входной файл
    ds_in = gdal.Open(input_path)
    if ds_in is None:
        mad.message_user(req, f"Не удалось открыть файл: {input_path}", level=messages.ERROR)
        return False

    cols = ds_in.RasterXSize
    rows = ds_in.RasterYSize
    bands = ds_in.RasterCount
    geotransform = ds_in.GetGeoTransform()
    projection = ds_in.GetProjection()

    # Определяем выходной тип данных
    if output_dtype is None:
        # Если не указан, используем исходный тип
        in_dtype = ds_in.GetRasterBand(1).DataType
        output_dtype = in_dtype
        # Но если исходный тип - float, конвертируем в Byte для визуализации
        if in_dtype in [gdal.GDT_Float32, gdal.GDT_Float64]:
            output_dtype = gdal.GDT_Byte

    # Определяем параметры для каждой полосы
    autolevels = []

    print(f"Анализ файла {input_path}...")
    for band_idx in range(1, bands + 1):
        band = ds_in.GetRasterBand(band_idx)
        nodata = band.GetNoDataValue()

        print(f"  Полоса {band_idx}: сбор статистики...")

        # Собираем значения для вычисления автоуровней
        all_values = []

        for y_start in range(0, rows, block_size):
            y_end = min(y_start + block_size, rows)
            block = band.ReadAsArray(0, y_start, cols, y_end - y_start)

            if nodata is not None:
                block = np.where(block == nodata, np.nan, block)

            valid = block[~np.isnan(block)]
            if len(valid) > 0:
                all_values.extend(valid)

        if len(all_values) == 0:
            print(f"    ВНИМАНИЕ: Нет данных для полосы {band_idx}")
            autolevels.append((0, 255))
            continue

        all_values = np.array(all_values)

        # Выбираем метод растяжки
        if stretch_mode == 'percentile':
            lower = np.percentile(all_values, lower_pct)
            upper = np.percentile(all_values, upper_pct)
        elif stretch_mode == 'minmax':
            lower = np.min(all_values)
            upper = np.max(all_values)
        elif stretch_mode == 'std':
            mean = np.mean(all_values)
            std = np.std(all_values)
            lower = mean - 2 * std
            upper = mean + 2 * std
        elif stretch_mode == 'adaptive':
            # Адаптивный выбор
            p2 = np.percentile(all_values, 2)
            p98 = np.percentile(all_values, 98)
            p50 = np.percentile(all_values, 50)
            # Если распределение сильно сжато, используем полный диапазон
            if (p98 - p2) < 0.01 * (np.max(all_values) - np.min(all_values)):
                lower = np.min(all_values)
                upper = np.max(all_values)
            else:
                lower = p2
                upper = p98
        else:
            mad.message_user(req, f'Неизвестный режим растяжки: "{stretch_mode}"', level=messages.ERROR)
            return False

        # Гарантируем минимальный диапазон
        if upper - lower < 1e-6:
            print(f"    ВНИМАНИЕ: слишком малый диапазон, расширяем")
            mean_val = np.mean(all_values)
            std_val = np.std(all_values)
            lower = max(mean_val - 3*std_val, np.min(all_values))
            upper = min(mean_val + 3*std_val, np.max(all_values))

            if upper - lower < 1e-6:
                lower = np.min(all_values)
                upper = np.max(all_values) + 1

        autolevels.append((lower, upper))

        print(f"    Полоса {band_idx}: min={np.min(all_values):.2f}, "
              f"max={np.max(all_values):.2f}, "
              f"stretch: {lower:.2f} - {upper:.2f}")

    # Создаем выходной файл
    driver = gdal.GetDriverByName('GTiff')
    out_ds = driver.Create(
        output_path, cols, rows, bands,
        output_dtype,
        options=['COMPRESS=LZW', 'TILED=YES']
    )
    out_ds.SetGeoTransform(geotransform)
    out_ds.SetProjection(projection)

    # Применяем автоуровни
    for band_idx, (lower, upper) in enumerate(autolevels, 1):
        in_band = ds_in.GetRasterBand(band_idx)
        out_band = out_ds.GetRasterBand(band_idx)
        nodata = in_band.GetNoDataValue()
        out_nodata = 0 if output_dtype == gdal.GDT_Byte else -9999
        out_band.SetNoDataValue(out_nodata)

        # Определяем выходной диапазон
        if output_dtype == gdal.GDT_Byte:
            target_min, target_max = 0, 255
        else:
            target_min, target_max = np.min(all_values), np.max(all_values)

        total_blocks = (rows + block_size - 1) // block_size

        for block_idx, y_start in enumerate(range(0, rows, block_size)):
            y_end = min(y_start + block_size, rows)
            block = in_band.ReadAsArray(0, y_start, cols, y_end - y_start).astype(np.float32)

            if nodata is not None:
                block = np.where(block == nodata, np.nan, block)

            # Применяем растяжку
            if upper > lower:
                stretched = (block - lower) / (upper - lower) * (target_max - target_min) + target_min
            else:
                stretched = np.full_like(block, (target_min + target_max) / 2)

            # Обрезаем до допустимого диапазона
            stretched = np.clip(stretched, target_min, target_max)

            # Заменяем NaN на NoData
            stretched = np.nan_to_num(stretched, nan=out_nodata)

            # Конвертируем в нужный тип
            if output_dtype == gdal.GDT_Byte:
                stretched = stretched.astype(np.uint8)
            elif output_dtype == gdal.GDT_UInt16:
                stretched = stretched.astype(np.uint16)
            elif output_dtype == gdal.GDT_Int16:
                stretched = stretched.astype(np.int16)

            # Записываем блок
            out_band.WriteArray(stretched, 0, y_start)

            if (block_idx + 1) % 10 == 0 or block_idx + 1 == total_blocks:
                print(f"  Полоса {band_idx}: блок {block_idx+1}/{total_blocks}")

    out_ds.FlushCache()
    out_ds = None
    ds_in = None

    mad.message_user(req, f'Выполнено автоконтрастирование композита методом "{stretch_mode}"', level=messages.SUCCESS)

    return True
