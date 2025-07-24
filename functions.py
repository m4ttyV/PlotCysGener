import csv
import smbclient
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

class TrackRow:
    def __init__(self, coords, name, id):
        self.coords = coords
        self.name = name
        self.id = id
# Класс строк точек: X, Y, давление
class DotRow:
    def __init__(self, lon, lat, type_id, slp, datetime):
        self.lon = lon
        self.lat = lat
        self.type_id = type_id
        self.slp = slp
        self.datetime = datetime

class CSVRow:
    def __init__(self, id, datetime, lon, lat, slp):
        self.id = id
        self.datetime = datetime
        self.lon = lon
        self.lat = lat
        self.slp = slp

def ensure_remote_directory(host: str, share: str, path: str):
    parts = path.strip("/").split("/")
    unc = rf"\\{host}\{share}"
    for part in parts:
        unc = rf"{unc}\{part}"
        try:
            smbclient.listdir(unc)
        except Exception:
            smbclient.mkdir(unc)
            print(f"Создана директория: {unc}")

def upload_file_to_smb(local_file_path, file_date):
    local_file_path = local_file_path.replace('\\', '/')
    file_name = os.path.basename(local_file_path)
    dec = ""
    if ("d1" in local_file_path):
        dec = "1/"
    if ("d2" in local_file_path):
        dec = "2/"
    if ("d3" in local_file_path):
        dec = "3/"

    smb_path = f"/{file_date}//" + dec

    SMB_HOST = ""
    SMB_USERNAME = ""
    SMB_PASSWORD = ""
    SMB_SHARE = ""
    smbclient.register_session(
    server=SMB_HOST,
    username=SMB_USERNAME,
    password=SMB_PASSWORD)
    tmp = "bulletin"
    test_dir = rf"\\{SMB_HOST}\{SMB_SHARE}\{tmp}"
    remote_dir = rf"\\{SMB_HOST}\{SMB_SHARE}\{smb_path}"
    remote_file = rf"{remote_dir}\{file_name}"
    try:
        files = smbclient.listdir(test_dir)
        print("Соединение установлено, в папке найдено файлов:", len(files))
    except Exception as e:
        print("Не удалось подключиться к SMB-шаре:", e)
    ensure_remote_directory(SMB_HOST, SMB_SHARE, smb_path)
    try:
        with open(local_file_path, "rb") as src, \
            smbclient.open_file(remote_file, mode="wb") as dst:
            dst.write(src.read())
        print(f"Файл {file_name} успешно загружен в {smb_path}")
    except Exception as e:
        print(f"Ошибка при загрузке файла: {e}")


def marker_type():
    return 'o'

def stage_type_id_color(type_id):
        if type_id == 2:
            return 'red'
        elif type_id == 6:
            return 'green'
        elif type_id == 7:
            return 'orange'
        elif type_id == 11:
            return 'purple'
        elif type_id == 29:
            return 'brown'

def track_tc(bm, tracks, DotRow):#1
    for track in tracks:
        first_track_coord = True
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
                    if first_track_coord:
                        plt.text(x[0] - 300000, y[0] - 300000, str(track.name).replace(' (', '\n('), fontsize=12, weight = "bold", color=color)
                        first_track_coord = False


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
    for dot in dots:
        # vm_lons, vm_lats, dot_id, dot_slp, dot_type_id = dot.split(' ') # x, y, подпись id, давление, тип точки
        color = stage_type_id_color(dot.type_id)
        x, y = bm(float(dot.lon), float(dot.lat))
        if dot.slp:
            plt.text(x + 20000, y + 20000, str(dot.slp), fontsize=12, color=color)
        datetime_str = str(dot.datetime)
        if datetime_str.split(' ')[1] == "00:00:00":
            datetime_row = dot.datetime.strftime('%d.%m')
            plt.text(x + 20000, y + 20000, datetime_row, fontsize=12, color=color)
        # будет функция возвращающая тип маркера (и цвет и тп)
        bm.plot(x, y, marker='o', color=color, markersize=5,  markeredgecolor=color, markerfacecolor='white')



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
        color = 'red'
        x, y = bm(float(dot.lon), float(dot.lat))
        marker = marker_type()
        bm.plot(x, y, marker=marker, color=color, markersize=5,  markeredgecolor=color, markerfacecolor='white')
        if dot.slp:
            plt.text(x + 20000, y + 20000, str(dot.slp), fontsize=12, color=color)

def get_cis_property_view_month(date_start, date_end, cur):
    command = f"SELECT ST_X(coord), ST_Y(coord), cic_type_id, * FROM ciclones.cic_property_view_mon WHERE max_datetime >= '{date_start}' AND max_datetime <= '{date_end}' order by cic_id, datetime;"
    cur.execute(command)
    view_mon_rows = cur.fetchall()
    return view_mon_rows

def get_cis_track_view_month(date_start, date_end, cur):
    command = f"SELECT ST_AsText(track), cic_type_id, * FROM ciclones.cic_track_view_gs_full WHERE max_datetime >= '{date_start}' AND max_datetime <= '{date_end}' order by cic_id, max_datetime;"
    cur.execute(command)
    track_view_rows = cur.fetchall()
    return track_view_rows

def csv_gen(filename, csv_row): #id, datetime, lat, lon, slp
    with open(filename, 'w', newline='', encoding='utf-8-sig') as csvfile:
        writer = csv.writer(csvfile, delimiter=';')
        writer.writerow(["id", "datetime", "lat", "lon", "slp"])
        for row in csv_row:
            writer.writerow([
                str(row.id),
                str(row.datetime.strftime("%Y.%m.%d")),
                str(int(row.lat)), #широта
                str(int(row.lon)), #долгота
                str(int(row.slp))  #давление
            ])


def main(cys_type_zn, cys_type_az, cys_type_tc, start_date, period, save_path, is_slp,
         is_track_name, blanc_type):  # Циклон, Антициклон, Тропический циклон

    save_dir = save_path.rsplit('/', 1)[0]
    try:
        os.makedirs(save_dir)
    except:
        pass

    # Считываем карту и рисуем необходимую область
    os.environ['GDAL_DATA'] = os.path.join(f'{os.sep}'.join(sys.executable.split(os.sep)[:-1]), 'Library', 'share',
                                           'gdal')
    plt.figure(figsize=(20, 16))

    if blanc_type == "TC":
        bm = Basemap(projection='aeqd',  # Тропики
                     lon_0=140,
                     lat_0=45,
                     width=9000000,
                     height=9000000,
                     resolution='i', area_thresh=1000.)
    else:
        bm = Basemap(projection='merc', llcrnrlat=20, urcrnrlat=65, \
                     llcrnrlon=105, urcrnrlon=190, lat_ts=20, resolution='i')

    bm.drawparallels(np.arange(-80., 81., 5.))
    bm.drawmeridians(np.arange(-180., 181., 5.))
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
    start_date = datetime.strptime(start_date, "%Y-%m-%d")
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
        dt = int(datetime.strftime(dot[15], "%H"))
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

        element = DotRow(vm_lons, vm_lats, dot_id, dot_slp, datetime_dot)
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
    file_date = str(datetime.strftime(start_date, "%Y%m%d"))
    filepath = save_path + file_date
    if period == 0:
        filepath = filepath + "_month_"
    else:
        filepath = filepath + "_decade_"
    csv_filepath = filepath
    if cys_type_zn:
        filepath = filepath + "ZN"
    if cys_type_az:
        filepath = filepath + "AZ"
    if cys_type_tc:
        filepath = filepath + "TC"
    filepath += ".png"

    # Легенда
    x, y = bm(55, 60)
    x -= 700000
    bm.plot(x, y, marker='s', color="black", markersize=200, markeredgecolor="black",
            markerfacecolor='white')

    cis_subtype_name = {
        2: "T",
        6: "TD",
        7: "TS",
        11: "STS",
        29: "L"
    }
    for color_id in [2,6,7,11,29]:
        bm.plot(x, y, marker='o', color="black", markersize=5, markeredgecolor=stage_type_id_color(color_id), markerfacecolor='white')
        plt.text(x + 80000, y - 50000, cis_subtype_name[color_id], fontsize=12, weight="bold",
             color="black")
        y -= 200000

    # сохраняем файл
    plt.savefig(filepath, bbox_inches='tight', pad_inches=0.1)
    plt.close()
    upload_file_to_smb(filepath, str(datetime.strftime(start_date, "%Y.%m")))
    # Закрываем соединение
    cur.close()
    conn.close()

    # написание csv файлов
    if cys_type_az:
        csv_gen(f"{csv_filepath}AZ.csv", csv_dot_az)
        upload_file_to_smb(f"{csv_filepath}AZ.csv", str(datetime.strftime(start_date, "%Y.%m")))
    if cys_type_zn:
        csv_gen(f"{csv_filepath}ZN.csv", csv_dot_zn)
        upload_file_to_smb(f"{csv_filepath}ZN.csv", str(datetime.strftime(start_date, "%Y.%m")))
    if cys_type_tc:
        csv_gen(f"{csv_filepath}TC.csv", csv_dot_tc)
        upload_file_to_smb(f"{csv_filepath}TC.csv", str(datetime.strftime(start_date, "%Y.%m")))

# 1 - тропический циклон TC
# 2 -
# 3 - циклон ZN
# 4 - антициклон AZ