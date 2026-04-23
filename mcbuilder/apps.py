from django.apps import AppConfig

from osgeo import gdal, gdal_array

import numpy as np
import glob
import os


class McbuilderConfig(AppConfig):
    name = 'mcbuilder'
    verbose_name = 'Создание МВК'

    def mvc_build(self, obj):
        # Пример создания медианного композита
        input_files = get_filenames_by_folder_name(obj.files_folder)
        print(f'Исходные файлы из папки {obj.files_folder}: {input_files}')
        output_file = obj.files_folder.name + '_' + obj.mcfile + '.tif'  # "{имя папки}_{метод создания}.tif"  # Файл результата
        print(f'Имя результирующего файла: {output_file}')

        if obj.method.name == 'Медианный композит':          # Создание медианного композита из нескольких разновременных снимков
            create_median_composite(input_files, output_file)

        if obj.method.name == 'Синтезированный композит':    # Создание синтезированного композита из двух разновременных снимков
        # Пример использования:
        # Берём канал 3 из первого файла (красный)
        # и каналы 2,1 из второго файла (зелёный и синий)
            composite_from_bands(
                path1=input_files[0], bands1=[3],
                path2=input_files[1], bands2=[2, 1],
                out_path=output_file
            )

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
#        filenames = [f.original_filename for f in files]
        filenames = [f.path for f in files]
        return filenames
    except folder.DoesNotExist:
        return []

# Синтезированный композит по трем каналам из разных снимков
def composite_from_bands(path1, bands1, path2, bands2, out_path, driver_name='GTiff'):
    """
    Создаёт мультиканальный растр, объединяя указанные каналы из двух разных файлов.

    Параметры:
        path1 (str): путь к первому растру
        bands1 (list[int]): список индексов каналов (1-базированная индексация) из первого растра
        path2 (str): путь ко второму растру
        bands2 (list[int]): список индексов каналов из второго растра
        out_path (str): путь для сохранения результата
        driver_name (str): драйвер GDAL (по умолчанию 'GTiff')
    """
    # Открываем исходные растры
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
