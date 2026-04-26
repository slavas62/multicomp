from django.apps import AppConfig

from osgeo import gdal, gdal_array
from django.utils.html import format_html

import numpy as np
import glob
import os

class McbuilderConfig(AppConfig):
    name = 'mcbuilder'
    verbose_name = 'Создание МВК'

    def mvc_build(self, obj):
        outdir = "media/composite/"

       # Пример создания медианного композита
        input_files = get_filenames_by_folder_name(obj.files_folder)
        print(f'Исходные файлы из папки {obj.files_folder}: {input_files}')

        output_folder = obj.files_folder.name  # Папка результата

#       *** Создание СИНТЕЗИРОВАННОГО композита из двух разновременных снимков ***
        if obj.method.name == 'Синтезированный композит':
        # Пример использования:
        # Берём канал 3 из первого файла (красный)
        # и каналы 2,1 из второго файла (зелёный и синий)
            output_file = output_folder + '_sintez_composite.tif'  # "{имя папки}_{метод создания}.tif"  # Файл результата
            composite_from_bands(
                path1 = input_files[0], bands1=[3],
                path2 = input_files[1], bands2=[2, 1],
                out_path = outdir + output_file,
                resampl = obj.resampl
            )
#       *** Создание МНОГОВРЕМЕННОГО композита из нескольких разновременных снимков с различными методами агреации ***
        elif obj.method.name == 'Многовременной композит':
            method = 'median' # метод агрегации: 'median', 'mean', 'max', 'min'.
            output_file = output_folder + '_' + method + '_composite.tif'  # "{имя папки}_{метод создания}.tif"  # Файл результата
            create_multitemporal_composite(
                input_files,
                outdir + output_file,
                method
            )
        else:
            raise ValueError(f"*** Этот метод пока не поддерживается: {obj.method.name} ***")
#            ModelAdmin.message_user(request, f"Этот метод пока не поддерживается: {obj.method.name}", level=messages.ERROR)

        '''
#       *** Создание МЕДИАННОГО композита из нескольких разновременных снимков (частный случай многовременного композита) ***
        if obj.method.name == 'Медианный композит':
            output_file = output_folder + '_median_composite.tif'  # "{имя папки}_{метод создания}.tif"  # Файл результата
            create_median_composite(
                input_files,
                outdir + output_file
            )
        '''

        obj.mcfile = output_file
        obj.builded = True
        return obj.builded

def get_filenames_by_folder_name(folder):
    try:
        # Получаем все файлы в этой папке (и подпапках, если нужно)
        # folder.files — это менеджер связанных файлов
        files = folder.files.all()
#        path_files = files[0].path
#        print(f'Полный путь к файлам: {path_files}')

        # Создаем список имен файлов
        filenames = [f.path for f in files]
        return filenames
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
def composite_from_bands(path1, bands1, path2, bands2, out_path, resampl, driver_name='GTiff'):
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
        raise ValueError("Размеры растров не совпадают")
    if ds1.GetProjection() != ds2.GetProjection():
        raise ValueError("Проекции растров не совпадают")
    geotransform = ds1.GetGeoTransform()
    if geotransform != ds2.GetGeoTransform():
        print("Предупреждение: геотрансформации различаются, будет использована трансформация первого файла")

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

    print(f"Синтезированный растр сохранён: {out_path}")



def create_multitemporal_composite(input_files, output_file, method='median'):
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
        raise IOError(f"Не удалось открыть {input_files[0]}")

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



def create_median_composite(input_files, output_file):
    """
    Создание медианного композита из нескольких разновременных снимков

    Параметры:
    input_files (list): Список путей к входным файлам
    output_file (str): Путь для сохранения композита
    """

    # Открываем первый файл для получения параметров
    ds = gdal.Open(input_files[0])
    cols = ds.RasterXSize
    rows = ds.RasterYSize
    bands = ds.RasterCount
    geotransform = ds.GetGeoTransform()
    projection = ds.GetProjection()
    ds = None

    # Создаем выходной файл
    driver = gdal.GetDriverByName('GTiff')
    out_ds = driver.Create(output_file, cols, rows, bands, gdal.GDT_Float32)
    out_ds.SetGeoTransform(geotransform)
    out_ds.SetProjection(projection)

    # Обрабатываем каждую полосу
    for band in range(1, bands + 1):
        print(f"Обработка полосы {band}...")

        # Создаем 3D массив для всех временных срезов
        time_series = []

        for file in input_files:
            ds = gdal.Open(file)
            data = ds.GetRasterBand(band).ReadAsArray().astype(np.float32)

            # Заменяем NoData значения на NaN
            data[data == ds.GetRasterBand(band).GetNoDataValue()] = np.nan
            time_series.append(data)
            ds = None

        # Стек временных срезов
        stack = np.stack(time_series, axis=0)

        # Вычисляем медиану по временной оси
        composite = np.nanmedian(stack, axis=0)

        # Заменяем NaN на NoData значение
        composite[np.isnan(composite)] = -9999

        # Записываем полосу
        out_band = out_ds.GetRasterBand(band)
        out_band.WriteArray(composite)
        out_band.SetNoDataValue(-9999)

    out_ds = None
    print(f"Композит сохранен в {output_file}")
