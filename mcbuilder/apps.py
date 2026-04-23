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

        output_file = obj.mcfile  # "median_composite.tif"  # Файл результата
        print(f'Имя результирующего файла: {output_file}')

        create_median_composite(input_files, output_file)   # Создание медианного композита из нескольких разновременных снимков

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
        composite[np.isnan(compound)] = -9999
        
        # Записываем полосу
        out_band = out_ds.GetRasterBand(band)
        out_band.WriteArray(composite)
        out_band.SetNoDataValue(-9999)
    
    out_ds = None
    print(f"Композит сохранен в {output_file}")
