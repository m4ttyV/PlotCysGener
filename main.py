import csv

import psycopg2
from shapely.wkt import loads
import numpy as np
import os
import sys
import argparse
from dateutil.relativedelta import relativedelta
from datetime import datetime, timedelta

from mpl_toolkits.basemap import Basemap
import matplotlib.pyplot as plt

# Класс строк линий, скорее всего не пригодится
class TrackRow:
    def __init__(self, coords, name, id):
        self.coords = coords
        self.name = name
        self.id = id

# Класс строк точек: X, Y, давление
class DotRow:
    def __init__(self, lon, lat, type_id, slp):
        self.lon = lon
        self.lat = lat
        self.type_id = type_id
        self.slp = slp

class CSVRow:
    def __init__(self, id, datetime, lon, lat, slp):
        self.id = id
        self.datetime = datetime
        self.lon = lon
        self.lat = lat
        self.slp = slp

def marker_type():
    return 'o'

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

def track_tc(bm, tracks, DotRow): #1
    for track in tracks:
        line = loads(track.coords)
        coords = list(line.coords)

        paired_coords = [(coords[i], coords[i + 1]) for i in range(len(coords) - 1)]
        for pair in paired_coords:
            first_coord, second_coord = pair
            first_coord_lon, first_coord_lat = first_coord
            for dot in DotRow:
                if dot.lon == first_coord_lon and dot.lat == first_coord_lat:
                    color = stage_type_id_color(dot.type_id)
                    lons, lats = zip(*list(pair))  # Разбираем координаты
                    x, y = bm(lons, lats)
                    bm.plot(x, y, marker=None, color=color, linewidth=2)
                    plt.text(x[0] + 20000, y[0] + 20000, str(track.name).replace(' (', '\n('), fontsize=20, weight = "bold", color=color)


        lons, lats = zip(*list(line.coords))  # Разбираем координаты
        x, y = bm(lons, lats)
        # color = 'black'
        # bm.plot(x, y, marker=None, color=color, linewidth=1)
        # plt.text(x[1] + 20000, y[1] + 20000, str(track.name).replace(' (', '\n('), fontsize=12, color='black')

def track_zn(bm, tracks):
    for track in tracks:
        line = loads(track.coords)
        lons, lats = zip(*list(line.coords))  # Разбираем координаты
        x, y = bm(lons, lats)
        color = 'darkblue'
        bm.plot(x, y, marker=None, color=color, linewidth=2)
        plt.text(x[0] + 20000, y[0] + 20000, str(track.id).replace(' (', '\n('), fontsize=20, weight = "bold", color=color)


def track_az(bm, tracks):
    for track in tracks:
        line = loads(track.coords)
        lons, lats = zip(*list(line.coords))  # Разбираем координаты
        x, y = bm(lons, lats)
        color = 'red'
        bm.plot(x, y, marker=None, color=color, linewidth=2)
        plt.text(x[0] + 20000, y[0] + 20000, str(track.id).replace(' (', '\n('), fontsize=20, weight = "bold", color=color)


def dot_tc(bm, dots):
    prev_dot_id = -1
    for dot in dots:
        # vm_lons, vm_lats, dot_id, dot_slp, dot_type_id = dot.split(' ') # x, y, подпись id, давление, тип точки
        color = stage_type_id_color(dot.type_id)
        x, y = bm(float(dot.lon), float(dot.lat))
        if dot.slp:
            plt.text(x + 20000, y + 20000, str(dot.slp), fontsize=12, color=color)
        # будет функция возвращающая тип маркера (и цвет и тп)
        bm.plot(x, y, marker='o', color=color, markersize=5,  markeredgecolor=color, markerfacecolor='white')

        # if tmp in label_dots:
        #     x += 20000
        #     y += 20000
        #     plt.text(x, y, str(dot_id), fontsize=12, color=color)
        #
        # if prev_dot_id != dot_id:
        #     x += 20000
        #     y += 20000
        #     plt.text(x, y, str(dot_id), fontsize=12, color=color)
        # prev_dot_id = dot_id

def dot_zn(bm, dots):
    for dot in dots:
        color = 'blue'
        x, y = bm(float(dot.lon), float(dot.lat))
        marker = marker_type()
        bm.plot(x, y, marker=marker, color=color, markersize=5,  markeredgecolor=color, markerfacecolor='white')
        if dot.slp:
            plt.text(x + 20000, y + 20000, str(dot.slp), fontsize=12, color=color)

def dot_az(bm, dots):
    prev_dot_id = -1
    for dot in dots:
        # vm_lons, vm_lats, dot_id, dot_slp = dot.split(' ')
        color = 'red'
        x, y = bm(float(dot.lon), float(dot.lat))
        marker = marker_type()
        bm.plot(x, y, marker=marker, color=color, markersize=5,  markeredgecolor=color, markerfacecolor='white')
        if dot.slp:
            plt.text(x + 20000, y + 20000, str(dot.slp), fontsize=12, color=color)

        # if f"({vm_lons}, {vm_lats})" in label_dots:
        #     x += 20000
        #     y += 20000
        #     plt.text(x, y, str(dot_id), fontsize=12, color=color)
        #
        # if prev_dot_id != dot_id:
        #     x += 20000
        #     y += 20000
        #     plt.text(x, y, str(dot_id), fontsize=12, color=color)
        # prev_dot_id = dot_id

def get_cis_property_view_month(date_start, date_end, cur):
    command = f"SELECT ST_X(coord), ST_Y(coord), cic_type_id, * FROM ciclones.cic_property_view_mon WHERE max_datetime >= '{date_start}' AND max_datetime <= '{date_end}' order by cic_id, max_datetime;"
    cur.execute(command)
    view_mon_rows = cur.fetchall()
    return view_mon_rows

def get_cis_track_view_month(date_start, date_end, cur):
    command = f"SELECT ST_AsText(track), cic_type_id, * FROM ciclones.cic_track_view_gs_full WHERE max_datetime >= '{date_start}' AND max_datetime <= '{date_end}' order by cic_id, max_datetime;"
    cur.execute(command)
    track_view_rows = cur.fetchall()
    return track_view_rows

def csv_gen(filename, csv_row): #id, datetime, lon, lat, slp
    with open(filename, 'w', newline='', encoding='utf-8-sig') as csvfile:
        writer = csv.writer(csvfile, delimiter=';')
        writer.writerow(["id", "datetime", "lon", "lat", "slp"])
        for row in csv_row:
            writer.writerow([
                str(row.id),
                str(row.datetime.strftime("%Y.%m.%d")),
                str(int(row.lon)),
                str(int(row.lat)),
                str(int(row.slp))
            ])


# 1 - тропический циклон TC
# 2 -
# 3 - циклон ZN
# 4 - антициклон AZ

def main(cys_type_zn, cys_type_az, cys_type_tc, start_date, period, save_path, is_slp, is_track_name): #Циклон, Антициклон, Тропический циклон

    try:
        os.makedirs(save_path)
    except:
        pass
        # Считываем карту и рисуем необходимую область

    os.environ['GDAL_DATA'] = os.path.join(f'{os.sep}'.join(sys.executable.split(os.sep)[:-1]), 'Library', 'share', 'gdal')
    plt.figure(figsize=(20, 16))
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

    csv_dot_tc = list()
    csv_dot_zn = list()
    csv_dot_az = list()

    label_dot_dict = dict()

    # формируем списки линий по типам циклонов
    for track in track_view_rows:
        track_type = track[1]
        track_id = ""
        if is_track_name:
            track_id = str(track[2])[-2:]
        row = track[0]
        # Проверяем нужны ли подписи имен линий и если нужны передаем и их
        if is_track_name:
            if track[3] != None:
                name = track[3]
            else:
                name = ""
            element = TrackRow(row, name, track_id)
        else:
            element = TrackRow(row, "", track_id)

        if track_type == 1:
            if cys_type_tc:
                if row is None:
                    continue
                track_view_tc.append(element)
        if track_type == 3:
             if cys_type_zn:
                if row is None:
                    continue
                track_view_zn.append(element)
        if track_type == 4:
            if cys_type_az:
                if row is None:
                    continue
                track_view_az.append(element)

    # формируем списки точек по типам циклонов
    for dot in view_mon_rows:
        vm_lons = dot[0]
        vm_lats = dot[1]
        dt = int(datetime.strftime(dot[15],"%H"))
        datetime_dot = dot[15]
        dot_type = dot[2]
        track_id = str(dot[4])[-2:]
        # Проверяем нужно ли подписать давление и если нужно то передаем его значение по условию
        dot_slp = ""
        if dt == 0 and is_slp:
            dot_slp = dot[18]

        dot_id = None
        if dot[13]:
            dot_id = dot[13]

        element = DotRow(vm_lons, vm_lats, dot_id, dot_slp)
        dot_slp = dot[18]
        csv_element = CSVRow(track_id, datetime_dot, vm_lons, vm_lats, dot_slp)
        if cys_type_tc:
            if dot_type == 1:
                mon_view_tc.append(element)
                csv_dot_tc.append(csv_element)
        if cys_type_zn:
            if dot_type == 3:
                mon_view_zn.append(element)
                csv_dot_zn.append(csv_element)
        if cys_type_az:
            if dot_type == 4:
                mon_view_az.append(element)
                csv_dot_az.append(csv_element)

    # построение линий
    track_tc(bm, track_view_tc, mon_view_tc)
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
    csv_filepath = filepath
    if cys_type_zn:
        filepath = filepath + "Zn"
    if cys_type_az:
        filepath = filepath + "Az"
    if cys_type_tc:
        filepath = filepath + "Tc"
    filepath += ".png"

    # сохраняем файл
    plt.savefig(filepath, bbox_inches='tight', pad_inches=0.1)
    # Закрываем соединение
    cur.close()
    conn.close()

    # написание csv файлов
    csv_gen(f"{csv_filepath}AZ.csv", csv_dot_az)
    csv_gen(f"{csv_filepath}ZN.csv", csv_dot_zn)
    csv_gen(f"{csv_filepath}TC.csv", csv_dot_tc)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Программа для анализа данных скорости ветра в файлах NetCDF.")
    parser.add_argument(
        "--startdate", "-sd",
        required=False,
        default="2025-01-01",
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
        default=0,
        help="Нужен ли тропический циклон (1 или 0)"
    )
    parser.add_argument(
        "--pathtosave", "-pts",
        required=False,
        default="./",
        help="Путь куда сохранять"
    )
    parser.add_argument(
        "--dots_slp", "-slp",
        required=False,
        type=float,
        default=0,
        help="Нужно ли давление точек"
    )
    parser.add_argument(
        "--track_name", "-tn",
        required=False,
        type=float,
        default=1,
        help="Нужны ли имена линий"
    )
    # Передаем аргументы
    args = parser.parse_args()
    cis_type_zn = True
    cis_type_az = True
    cis_type_tc = True
    is_slp = True
    is_track_name = True

    if args.cyclone == 0:
        cis_type_zn = False

    if args.anticyclone == 0:
        cis_type_az = False

    if args.tropicalcyclone == 0:
        cis_type_tc = False

    if args.dots_slp == 0:
        is_slp = False

    if args.track_name == 0:
        is_track_name = False

    main(cis_type_zn, cis_type_az, cis_type_tc, args.startdate, args.period, args.pathtosave, is_slp, is_track_name)