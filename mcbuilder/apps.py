from django.apps import AppConfig

from osgeo import gdal, gdal_array
from django.contrib import messages
from django.utils.html import format_html

import numpy as np
import glob
import os

import datetime

from pathlib import Path

class McbuilderConfig(AppConfig):
    name = 'mcbuilder'
    verbose_name = 'Создание МВК'

    def ready(self):              # Импортируем сигналы, чтобы они зарегистрировались
        import mcbuilder.signals  # noqa: F401

    def mvc_build(self, modeladmin, request, obj):
        outdir = os.environ.get('GEOSERVER_OUTDIR_MULTICOMP', 'media/composite/')
        modeladmin.message_user(request, f'Время начала расчета: {datetime.datetime.now()}', level=messages.WARNING)
        print(f'Время начала расчета: {datetime.datetime.now()}')
        print(f'Директория результата: {outdir}')

        input_files = get_filenames_by_folder_name(obj.files_folder)
        print(f'Исходные файлы из папки {obj.files_folder}: {input_files}')

        source_folder = obj.files_folder.name  # Папка результата

#       *** Создание СИНТЕЗИРОВАННОГО композита из двух разновременных снимков ***
        if obj.method.name == 'Синтезированный композит':
        # Пример использования:
        # Берём самый яркий 2-ой канал (зеленый) из первого файла, снятого последним
        # и каналы 3,1  (красный и синий) из второго файла, снятого ранее
            output_file = obj.author.username + '_' + source_folder + '_sintez_composite.tif'  # "{имя папки}_{метод создания}.tif"  # Файл результата
            created = composite_from_bands(
                modeladmin,
                request,
                path1 = input_files[0], bands1=[2], # это будет красный канал в результирующем файле
                path2 = input_files[1], bands2=[3, 1],
                out_path = outdir + output_file,
                resampl = obj.resampl
            )
#       *** Создание МНОГОВРЕМЕННОГО композита из нескольких разновременных снимков с различными методами агреации ***
        elif obj.method.name == 'Многовременной композит':
            agmet = obj.agregat # метод агрегации: 'median', 'mean', 'max', 'min'.
            output_file = obj.author.username + '_' + source_folder + '_' + agmet + '_composite.tif'  # "{имя папки}_{метод создания}.tif"  # Файл результата
            created = create_multitemporal_composite(
                modeladmin,
                request,
                input_files,
                outdir + output_file,
                agmet
            )
        else:
#            raise ValueError(f"*** Этот метод пока не поддерживается: {obj.method.name} ***")
            modeladmin.message_user(request, f"Этот метод пока не поддерживается: {obj.method.name}", level=messages.ERROR)
            obj.builded = False
            return obj.builded

        obj.builded = created

        if created:
            obj.mcfile = output_file
            modeladmin.message_user(request, f'Время окончания расчета: {datetime.datetime.now()}', level=messages.WARNING)
            print(f'Время окончания расчета: {datetime.datetime.now()}')

        return obj.builded

def get_filenames_by_folder_name(folder):
    import numpy as np

    try:
        # Получаем все файлы в этой папке (и подпапках, если нужно)
        # folder.files — это менеджер связанных файлов
        files = folder.files.all()
#        path_files = files[0].path
#        print(f'Полный путь к файлам: {path_files}')

        # Создаем список имен файлов
        filepath = [f.path for f in files]
        filenames = [Path(f.path).name for f in files]

        indices = np.argsort(filenames)[::-1] # массив отсортированных индексов массива filenames (сортировка индексов по убыванию имен файлов)

        return [filepath[i] for i in indices]
    except folder.DoesNotExist:
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

    # Если нужно задать разрешение (например, 30x30 метров)
    # xRes=30, yRes=30,
    # Если нужно задать границы (xmin, ymin, xmax, ymax)
    # outputBounds=(... , ... , ... , ...),
    warp_options = gdal.WarpOptions(
        format='GTiff',
        targetAlignedPixels = True,
        xRes = gt[1],
        yRes = -gt[5],
#        width = match_ds.RasterXSize,
#        height = match_ds.RasterYSize,
        dstSRS = match_ds.GetProjection(),
        outputBounds = (xmin, ymin, xmax, ymax), # match_ds.GetGeoTransform(),
        resampleAlg='bilinear'                   # gdal.GRA_NearestNeighbour  метод ресемплинга (near, bilinear, cubic, lanczos)
    )
    gdal.Warp(target_file, src_file, options=warp_options)
    match_ds = None



# *** Синтезированный композит по трем каналам из разных снимков ***
def composite_from_bands(modeladmin, request, path1, bands1, path2, bands2, out_path, resampl, driver_name='GTiff'):
    """
    Создаёт мультиканальный растр, объединяя указанные каналы из двух разных файлов.

    Параметры:
        path1 (str): путь к первому растру
        bands1 (list[int]): список индексов каналов (1-базированная индексация) из первого растра
        path2 (str): путь ко второму растру
        bands2 (list[int]): список индексов каналов из второго растра
        out_path (str): путь для сохранения результата
        resampl (boolean): ресемплинг с помощью GDAL - единые проекция, размеры, разрешение и extent для всех файлов.
        driver_name (str): драйвер GDAL (по умолчанию 'GTiff')
    """
    # Открываем исходные растры
    if resampl:
        reproject_to_match(path1, 'resample1.tif', path1)
        reproject_to_match(path2, 'resample2.tif', path1)
        ds1 = gdal.Open('resample1.tif')
        ds2 = gdal.Open('resample2.tif')
    else:
        ds1 = gdal.Open(path1)
        ds2 = gdal.Open(path2)

    if ds1 is None or ds2 is None:
        raise RuntimeError("Не удалось открыть один из файлов")

    # Проверяем совпадение размеров, проекции и геотрансформации
    if ds1.RasterXSize != ds2.RasterXSize or ds1.RasterYSize != ds2.RasterYSize:
#        raise ValueError("Размеры растров не совпадают")
        modeladmin.message_user(request, f"Размеры растров не совпадают", level=messages.ERROR)
        return False

    if ds1.GetProjection() != ds2.GetProjection():
#        raise ValueError("Проекции растров не совпадают")
        modeladmin.message_user(request, f"Проекции растров не совпадают", level=messages.ERROR)
        return False

    geotransform = ds1.GetGeoTransform()
    if geotransform != ds2.GetGeoTransform():
#        print("Предупреждение: геотрансформации различаются, будет использована трансформация первого файла")
        modeladmin.message_user(request, f"Предупреждение: геотрансформации различаются, будет использована трансформация первого файла", level=messages.WARNING)

    # Определяем количество каналов в выходном растре
    num_bands = len(bands1) + len(bands2)
    # Тип данных – берем из первого указанного канала (можно улучшить)
    sample_band = ds1.GetRasterBand(bands1[0])
    data_type = sample_band.DataType

    # Создаём выходной растр
    driver = gdal.GetDriverByName(driver_name)
    out_ds = driver.Create(out_path, ds1.RasterXSize, ds1.RasterYSize, num_bands, data_type)
    out_ds.SetProjection(ds1.GetProjection())
    out_ds.SetGeoTransform(geotransform)

    # Последовательная запись каналов из первого файла
    for out_idx, band_idx in enumerate(bands1, start=1):
        src_band = ds1.GetRasterBand(band_idx)
        data = src_band.ReadAsArray()
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


def create_multitemporal_composite(modeladmin, request, input_files, output_file, method='median'):
    """
    Создаёт мультивременной композит из списка входных растров.

    Параметры:
        input_files (list): список путей к входным растрам (одинакового размера и проекции).
        output_file (str): путь к выходному растру.
        method (str): метод агрегации: 'median', 'mean', 'max', 'min'.
    """
    if not input_files:
        raise ValueError("Список входных файлов пуст")

    # Открываем первый файл для получения метаданных
    ds_ref = gdal.Open(input_files[0], gdal.GA_ReadOnly)
    if ds_ref is None:
#        raise IOError(f"Не удалось открыть {input_files[0]}")
        modeladmin.message_user(request, f"Не удалось открыть {input_files[0]}", level=messages.ERROR)
        return False

    cols = ds_ref.RasterXSize
    rows = ds_ref.RasterYSize
    bands = ds_ref.RasterCount
    projection = ds_ref.GetProjection()
    geotransform = ds_ref.GetGeoTransform()

    # Выбираем тип данных (можно задать вручную, здесь сохраняем как Float32)
    out_dtype = gdal.GDT_Float32

    # Создаём выходной файл
    driver = gdal.GetDriverByName('GTiff')
    out_ds = driver.Create(output_file, cols, rows, bands, out_dtype, options=['COMPRESS=LZW'])
    out_ds.SetProjection(projection)
    out_ds.SetGeoTransform(geotransform)

    # Определим размер блока для построчной обработки (можно настроить под размер файла)
    block_size = 256  # строк за раз

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

                # Стек: (n_files, n_rows, cols)
                stack = np.array(stack)

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
                    raise ValueError(f"Неподдерживаемый метод: {method}")

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
