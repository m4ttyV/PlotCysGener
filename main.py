import psycopg2
from shapely.wkt import loads
import numpy as np
import geopandas as gpd
import os
import sys
import argparse
from dateutil.relativedelta import relativedelta
from datetime import datetime, timedelta

from mpl_toolkits.basemap import Basemap
import matplotlib.pyplot as plt


def get_cis_property_view_month(date_start, date_end, cur):
    command = f"SELECT ST_X(coord), ST_Y(coord), cic_type_id FROM ciclones.cic_property_view_mon WHERE max_datetime >= '{date_start}' AND max_datetime <= '{date_end}'"
    cur.execute(command)
    view_mon_rows = cur.fetchall()
    return view_mon_rows

def get_cis_track_view_month(date_start, date_end, cur):
    command = f"SELECT ST_AsText(track), cic_type_id FROM ciclones.cic_track_view_gs_full WHERE max_datetime >= '{date_start}' AND max_datetime <= '{date_end}'"
    cur.execute(command)
    track_view_rows = cur.fetchall()
    return track_view_rows

# 1 - тропический циклон
# 2 -
# 3 - циклон
# 4 - антициклон

def main(cys_type_zn, cys_type_az, cys_type_tc, start_date, period, save_path): #Циклон, Антициклон, Тропический циклон

    os.environ['GDAL_DATA'] = os.path.join(f'{os.sep}'.join(sys.executable.split(os.sep)[:-1]), 'Library', 'share', 'gdal')
    map = gpd.read_file('map/ne_110m_coastline.shp')
    # bm = Basemap(
    #             llcrnrlat=20, urcrnrlat=70, \
    #             llcrnrlon=105, urcrnrlon=200, \
    #             resolution='c', projection='tmerc', lon_0=170, lat_0=50)
    bm = Basemap(width=8000000,height=6500000,
                rsphere=(6378137.00,6356752.3142),\
                resolution='l',area_thresh=1000.,projection='lcc',\
                lat_1=80.,lat_2=55,lat_0=45,lon_0=+150.)
                # lat_1=20., lat_2=55, lat_0=45, lon_0=+150.)
    bm.drawparallels(np.arange(-80.,81.,5.))
    bm.drawmeridians(np.arange(-180.,181.,5.))
    bm.readshapefile('map/ne_110m_coastline', 'coastline')
    with open('confing.conf', 'r') as f:
        db_conf = f.read().splitlines()
    DB_HOST = ""
    DB_PORT = ""
    DB_NAME = ""
    DB_USER = ""
    DB_PASSWORD = ""
    for row in db_conf:
        if DB_HOST == "":
            DB_HOST = row
            continue
        if DB_PORT == "":
            DB_PORT = row
            continue
        if DB_NAME == "":
            DB_NAME = row
            continue
        if DB_USER == "":
            DB_USER = row
            continue
        if DB_PASSWORD == "":
            DB_PASSWORD = row
            break

    # Подключение к базе данных
    conn = psycopg2.connect(
        host=DB_HOST,
        port=DB_PORT,
        database=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD
    )

    # Создаем курсор для выполнения запросов
    cur = conn.cursor()
    view_mon_rows = list()
    track_view_rows = list()
    # dt = "2015-05-01"
    # start_date = datetime.strptime(dt, "%Y-%m-%d")
    end_date = None
    start_date =  datetime.strptime(start_date, "%Y-%m-%d")
    if period == 0:
        end_date = start_date + relativedelta(months=1)
    else:
        end_date = start_date + timedelta(days=10)

    # Вызываем функции
    view_mon_rows = get_cis_property_view_month(start_date, end_date, cur)
    track_view_rows = get_cis_track_view_month(start_date, end_date, cur)

    for track in track_view_rows:
        if track[0] is None:
            continue
        line = loads(track[0])
        lons, lats = zip(*list(line.coords))  # Разбираем координаты
        type = track[1]

        if not cys_type_zn:
            if type == 3:
                continue
        if not cys_type_az:
            if type == 4:
                continue
        if not cys_type_tc:
            if type == 1:
                continue

        x, y = bm(lons, lats)
        color = 'red'  # Цвет по умолчанию
        if type == 3:
            color = 'blue'
        if type == 1:
            color = 'yellow'
        bm.plot(x, y, marker=None, color=color, linewidth=1)

    for dot in view_mon_rows:
        # Предположим, что dot - это кортеж или список с нужными данными, например, (lon, lat, type)
        vm_lons = dot[0]  # Долгота
        vm_lats = dot[1]  # Широта
        type = dot[2]  # Тип (например, "Циклон" или другое)

        if not cys_type_zn:
            if type == 3:
                continue
        if not cys_type_az:
            if type == 4:
                continue
        if not cys_type_tc:
            if type == 1:
                continue

        color = 'red'  # Цвет по умолчанию
        if type == 3:
            color = 'blue'
        if type == 1:
            color = 'yellow'
        # Преобразуем долготу и широту в координаты карты
        x, y = bm(vm_lons, vm_lats)
        # Отображаем точку на карте
        bm.plot(x, y, marker='o', color=color, markersize=5)

    filepath = save_path + str(datetime.strftime(start_date,"%Y%m%d"))
    if period == "0":
        filepath = filepath + "_month_"
    else:
        filepath = filepath + "_decade_"
    if cys_type_zn:
        filepath = filepath + "Zn"
    if cys_type_az:
        filepath = filepath + "Az"
    if cys_type_tc:
        filepath = filepath + "Tc"

    filepath = filepath + ".jpg"
    plt.savefig(filepath)
    # Закрываем соединение
    cur.close()
    conn.close()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Программа для анализа данных скорости ветра в файлах NetCDF.")
    parser.add_argument(
        "--startdate", "-sd",
        # required=False,
        # default="2015-05-01",
        required=True,
        help="Дата начала периода в формате yyyy-mm-dd",
    )
    parser.add_argument(
        "--period", "-p",
        required=False,
        default=0,
        help="Тип периода (0 - месяц, 1 - декада"
    )
    parser.add_argument(
        "--cyclone", "-zn",
        required=False,
        type=float,
        default=1,
        help="Нужен ли циклон (1 или 0)"
    )
    parser.add_argument(
        "--anticyclone", "-az",
        required=False,
        type=float,
        default=1,
        help="Нужен ли антициклон (1 или 0)"
    )
    parser.add_argument(
        "--tropicalcyclone", "-tc",
        required=False,
        type=float,
        default=1,
        help="Нужен ли тропический циклон (1 или 0)"
    )
    parser.add_argument(
        "--pathtosave", "-pts",
        required=False,
        default="./",
        help="Путь куда сохранять"
    )
    # Парсим аргументы
    args = parser.parse_args()
    cis_type_zn = True
    cis_type_az = True
    cis_type_tc = True
    if args.cyclone == 0:
        cis_type_zn = False

    if args.anticyclone == 0:
        cis_type_az = False

    if args.tropicalcyclone == 0:
        cis_type_tc = False

    main(cis_type_zn, cis_type_az, cis_type_tc, args.startdate, args.period, args.pathtosave)