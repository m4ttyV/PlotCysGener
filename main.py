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

def track_tc(bm, tracks): #1
    for track in tracks:
        line = loads(track)
        lons, lats = zip(*list(line.coords))  # Разбираем координаты
        x, y = bm(lons, lats)
        color = 'yellow'
        bm.plot(x, y, marker=None, color=color, linewidth=1)

def track_zn(bm, tracks): #3
    for track in tracks:
        line = loads(track)
        lons, lats = zip(*list(line.coords))  # Разбираем координаты
        x, y = bm(lons, lats)
        color = 'blue'
        bm.plot(x, y, marker=None, color=color, linewidth=1)

def track_az(bm, tracks): #4
    for track in tracks:
        line = loads(track)
        lons, lats = zip(*list(line.coords))  # Разбираем координаты
        x, y = bm(lons, lats)
        subtitle_dot = list(line.coords)[0]
        #по полученной точке рисовать
        # plt.text(x, y, , fontsize=12, color=color)
        color = 'red'
        bm.plot(x, y, marker=None, color=color, linewidth=1)

def stage_type_id_color(type_id):
        if type_id == 2:
            return 'red'
        elif type_id == 7:
            return 'orange'
        elif type_id == 6:
            return 'green'
        elif type_id == 11:
            return 'purple'
        elif type_id == 29:
            return 'brown'

def dot_tc(bm, dots):
    count = 0
    for dot in dots:
        vm_lons, vm_lats, dot_id, dot_slp, dot_type_id = dot.split(' ') #x, y, подпись id, давление, тип точки
        color = stage_type_id_color(dot_type_id)
        x, y = bm(float(vm_lons), float(vm_lats))
        # будет функция возвращающая тип маркера (и цвет и тп)
        bm.plot(x, y, marker='o', color=color, markersize=5)
        if count == 0:
            x += 20000
            y += 20000
            plt.text(x, y, str(dot_id), fontsize=12, color=color)
            #Пишем имя троп циклона
        count += 1

def dot_zn(bm, dots):
    count = 0
    for dot in dots:
        vm_lons, vm_lats, dot_id, dot_slp = dot.split(' ')
        color = 'blue'
        x, y = bm(float(vm_lons), float(vm_lats))
        bm.plot(x, y, marker='o', color=color, markersize=5)
        if count == 0:
            x += 20000
            y += 20000
            plt.text(x, y, str(dot_id), fontsize=12, color=color)
        count += 1

def dot_az(bm, dots):
    count = 0
    for dot in dots:
        vm_lons, vm_lats, dot_id, dot_slp = dot.split(' ')
        color = 'red'
        x, y = bm(float(vm_lons), float(vm_lats))
        bm.plot(x, y, marker='o', color=color, markersize=5)
        if count == 0:
            x += 20000
            y += 20000
            plt.text(x, y, str(dot_id), fontsize=12, color=color)
        count += 1

def get_cis_property_view_month(date_start, date_end, cur):
    command = f"SELECT ST_X(coord), ST_Y(coord), cic_type_id, * FROM ciclones.cic_property_view_mon WHERE max_datetime >= '{date_start}' AND max_datetime <= '{date_end}'"
    # command = f"SELECT ST_X(coord), ST_Y(coord), cic_type_id FROM ciclones.cic_property_view_mon WHERE max_datetime >= '{date_start}' AND max_datetime <= '{date_end}'"
    cur.execute(command)
    view_mon_rows = cur.fetchall()
    return view_mon_rows

def get_cis_track_view_month(date_start, date_end, cur):
    command = f"SELECT ST_AsText(track), cic_type_id, * FROM ciclones.cic_track_view_gs_full WHERE max_datetime >= '{date_start}' AND max_datetime <= '{date_end}'"
    cur.execute(command)
    track_view_rows = cur.fetchall()
    return track_view_rows

# 1 - тропический циклон
# 2 -
# 3 - циклон
# 4 - антициклон

def main(cys_type_zn, cys_type_az, cys_type_tc, start_date, period, save_path): #Циклон, Антициклон, Тропический циклон
    # Считываем карту и рисуем необходимую область
    os.environ['GDAL_DATA'] = os.path.join(f'{os.sep}'.join(sys.executable.split(os.sep)[:-1]), 'Library', 'share', 'gdal')
    gpd.read_file('map/ne_110m_coastline.shp')
    plt.figure(figsize=(20, 16))
    # bm = Basemap(width=8000000,height=6500000,
    #             rsphere=(6378137.00,6356752.3142),\
    #             resolution='h',area_thresh=1000.,projection='lcc',\
    #             lat_1=-10.,lat_2=55,lat_0=45,lon_0=+150.)
    #             # lat_1=20., lat_2=55, lat_0=45, lon_0=+150.)
    blanc_type = "None"
    if blanc_type == "TC":
        bm = Basemap(projection='aeqd', # Тропики
                  lon_0=140,
                  lat_0=45,
                  width=9000000,
                  height=9000000,
                 resolution='i',area_thresh=1000.)
    else:
        bm = Basemap(projection='merc', llcrnrlat=20, urcrnrlat=70, \
                    llcrnrlon=100, urcrnrlon=200, lat_ts=20, resolution='i')

    bm.drawparallels(np.arange(-80.,81.,5.))
    bm.drawmeridians(np.arange(-180.,181.,5.))
    bm.drawcoastlines()
    #bm.readshapefile('map/ne_110m_coastline', 'coastline')

    # Считываем параметры БД
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

    end_date = None
    start_date =  datetime.strptime(start_date, "%Y-%m-%d")
    if period == 0:
        end_date = start_date + relativedelta(months=1)
    else:
        if start_date.day >= 21:
            end_date = start_date + relativedelta(months=1) - timedelta(days=start_date.day)
        else:
            end_date = start_date + timedelta(days=10)

    # формируем и заранее создаем необходимые списки
    view_mon_rows = get_cis_property_view_month(start_date, end_date, cur)
    track_view_rows = get_cis_track_view_month(start_date, end_date, cur)
    track_view_tc = list()
    track_view_zn = list()
    track_view_az = list()

    mon_view_tc = list()
    mon_view_zn = list()
    mon_view_az = list()

    # формируем списки линий по типам циклонов
    for track in track_view_rows:
        type = track[1]
        row = track[0]
        if type == 1:
            if cys_type_tc:
                if row is None:
                    continue
                track_view_tc.append(row)
        if type == 3:
             if cys_type_zn:
                if row is None:
                    continue
                track_view_zn.append(row)
        if type == 4:
            if cys_type_az:
                if row is None:
                    continue
                track_view_az.append(row)

    # формируем списки точек по типам циклонов
    for dot in view_mon_rows:
        vm_lons = dot[0]
        vm_lats = dot[1]
        dot_id = str(dot[3])[-2:]
        dot_slp = dot[18]
        dot_stage_type_id = None
        if dot[13]:
            dot_stage_type_id = dot[13]
        type = dot[2]
        if cys_type_tc:
            if type == 1:
                mon_view_tc.append(f"{vm_lons} {vm_lats} {dot_id} {dot_slp} {dot_stage_type_id}")
        if cys_type_zn:
            if type == 3:
                mon_view_zn.append(f"{vm_lons} {vm_lats} {dot_id} {dot_slp}")
        if cys_type_az:
            if type == 4:
                mon_view_az.append(f"{vm_lons} {vm_lats} {dot_id} {dot_slp}")


    # построение линий
    track_tc(bm, track_view_tc)
    track_zn(bm, track_view_zn)
    track_az(bm, track_view_az)


    # построение точек
    dot_tc(bm, mon_view_tc)
    dot_zn(bm, mon_view_zn)
    dot_az(bm, mon_view_az)

    # формирование имени файла и пути
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
    filepath = filepath + ".png"

    # сохраняем файл
    plt.savefig(filepath, bbox_inches='tight', pad_inches=0.1)
    # Закрываем соединение
    cur.close()
    conn.close()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Программа для анализа данных скорости ветра в файлах NetCDF.")
    parser.add_argument(
        "--startdate", "-sd",
        required=False,
        default="2024-08-01",
        # required=True,
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

    # Передаем аргументы
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