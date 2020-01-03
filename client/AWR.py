#!/usr/bin/python
# -*- coding: UTF-8 -*-
# File name   : client.py
# Description : client  
# E-mail      : sect16@gmail.com
# Author      : Chin Pin Hon
# Date        : 03/01/2020
# 
import cv2
import zmq
import base64
import numpy as np
from socket import *
import time
import threading
import tkinter as tk
import traceback
import coloredlogs, logging

# Create a logger object.
logger = logging.getLogger(__name__)
coloredlogs.install(level='DEBUG',
                    fmt='%(asctime)s.%(msecs)03d %(levelname)7s %(thread)5d --- [%(threadName)16s] %(funcName)-39s: %(message)s')
logger.info('Starting python...')

# Flags
move_forward_status = 0
move_backward_status = 0
move_left_status = 0
move_right_status = 0
funcMode = 0
sport_mode_on = 0
ultrasonic_mode = 0

# Variables
frame_num = 0
fps = 0
cpu_temp = 0
cpu_use = 0
ram_use = 0
addr = 0

tcp_client_socket = None
fpv_event = threading.Event()
connect_event = threading.Event()
footage_socket = None
font = None
root = tk.Tk()  # Define a window named root
ultra_data = 'Ultrasonic OFF'

# Configuration
BUFFER_SIZE = 1024
SERVER_PORT = 10223  # Define port serial
VIDEO_PORT = 5555
INFO_PORT = 2256  # Define port serial
ULTRA_PORT = 2257  # Define port serial


def get_fps_thread(arg, event):
    logger.debug('Thread started')
    global frame_num, fps
    while event.is_set():
        time.sleep(1)
        fps = frame_num
        frame_num = 0
    logger.debug('Thread stopped')


def open_cv_thread(arg, event):
    logger.debug('Thread started')
    global frame_num, ultrasonic_mode
    while event.is_set():
        try:
            frame = footage_socket.recv_string()
            img = base64.b64decode(frame)
            npimg = np.frombuffer(img, dtype=np.uint8)
            source = cv2.imdecode(npimg, 1)
            cv2.putText(source, ('PC FPS: %s' % fps), (40, 20), font, 0.5, (255, 255, 255), 1, cv2.LINE_AA)
            cv2.putText(source, ('CPU Temperature: %s' % cpu_temp), (370, 350), font, 0.5, (128, 255, 128), 1,
                        cv2.LINE_AA)
            cv2.putText(source, ('CPU Usage: %s' % cpu_use), (370, 380), font, 0.5, (128, 255, 128), 1, cv2.LINE_AA)
            cv2.putText(source, ('RAM Usage: %s' % ram_use), (370, 410), font, 0.5, (128, 255, 128), 1, cv2.LINE_AA)
            if ultrasonic_mode == 1:
                cv2.line(source, (320, 240), (260, 300), (255, 255, 255), 1)
                cv2.line(source, (210, 300), (260, 300), (255, 255, 255), 1)
                cv2.putText(source, ('%sm' % ultra_data), (210, 290), font, 0.5, (255, 255, 255), 1, cv2.LINE_AA)
            # cv2.putText(source,('%sm'%ultra_data),(210,290), font, 0.5,(255,255,255),1,cv2.LINE_AA)
            cv2.imshow("Stream", source)
            frame_num += 1
            cv2.waitKey(1)
        except:
            logger.error('Thread exception: %s', traceback.format_exc())
            time.sleep(0.5)
            break
    cv2.destroyAllWindows()
    logger.debug('Thread stopped')
    btn_FPV.config(bg=color_btn)


def replace_num(initial, new_num):  # Call this function to replace data in '.txt' file
    newline = ""
    str_num = str(new_num)
    with open("ip.txt", "r") as f:
        for line in f.readlines():
            if line.find(initial) == 0:
                line = initial + "%s" % str_num
            newline += line
    with open("ip.txt", "w") as f:
        f.writelines(newline)  # Call this function to replace data in '.txt' file


def num_import(initial):  # Call this function to import data from '.txt' file
    with open("ip.txt") as f:
        for line in f.readlines():
            if line.find(initial) == 0:
                r = line
    begin = len(list(initial))
    snum = r[begin:]
    n = snum
    return n


def call_sport_mode(event):
    global sport_mode_on
    if sport_mode_on:
        tcp_client_socket.send('SportModeOff'.encode())
    else:
        tcp_client_socket.send('SportModeOn'.encode())


def call_forward(event):  # When this function is called,client commands the car to move forward
    global move_forward_status
    if move_forward_status == 0:
        tcp_client_socket.send('forward'.encode())
        move_forward_status = 1


def call_back(event):  # When this function is called,client commands the car to move backward
    global move_backward_status
    if move_backward_status == 0:
        tcp_client_socket.send('backward'.encode())
        move_backward_status = 1


def call_stop(event):  # When this function is called,client commands the car to stop moving
    global move_forward_status, move_backward_status, move_left_status, move_right_status
    move_forward_status = 0
    move_backward_status = 0
    tcp_client_socket.send('DS'.encode())


def call_turn_stop(event):  # When this function is called,client commands the car to stop moving
    global move_forward_status, move_backward_status, move_left_status, move_right_status
    move_left_status = 0
    move_right_status = 0
    tcp_client_socket.send('TS'.encode())


def call_left(event):  # When this function is called,client commands the car to turn left
    global move_left_status
    if move_left_status == 0:
        tcp_client_socket.send('left'.encode())
        move_left_status = 1


def call_right(event):  # When this function is called,client commands the car to turn right
    global move_right_status
    if move_right_status == 0:
        tcp_client_socket.send('right'.encode())
        move_right_status = 1


def call_head_up(event):
    tcp_client_socket.send('headup'.encode())


def call_head_down(event):
    tcp_client_socket.send('headdown'.encode())


def call_head_home(event):
    tcp_client_socket.send('headhome'.encode())


def call_ultra(event):
    global ultrasonic_mode
    if funcMode == 0:
        tcp_client_socket.send('Ultrasonic'.encode())
        ultrasonic_mode = 1
    else:
        tcp_client_socket.send('func_end'.encode())


def call_find_color(event):
    if funcMode == 0:
        tcp_client_socket.send('FindColor'.encode())
    else:
        tcp_client_socket.send('func_end'.encode())


def call_watchdog(event):
    if funcMode == 0:
        tcp_client_socket.send('WatchDog'.encode())
    else:
        tcp_client_socket.send('func_end'.encode())


def call_find_line(event):
    if funcMode == 0:
        tcp_client_socket.send('FindLine'.encode())
    else:
        tcp_client_socket.send('func_end'.encode())


def call_fpv(event):
    global footage_socket, font, VIDEO_PORT, fpv_event, connect_event
    if str(btn_FPV['state']) == 'normal':
        btn_FPV['state'] = 'disabled'
    if not fpv_event.is_set():
        logger.info('Starting FPV')
        if connect_event.is_set():
            fpv_event.set()
            fps_threading = threading.Thread(target=get_fps_thread, args=(0, fpv_event), daemon=True)
            fps_threading.start()
            context = zmq.Context()
            footage_socket = context.socket(zmq.SUB)
            footage_socket.bind('tcp://*:%d' % VIDEO_PORT)
            footage_socket.setsockopt_string(zmq.SUBSCRIBE, np.unicode(''))
            font = cv2.FONT_HERSHEY_SIMPLEX
            # Define a thread for FPV and OpenCV
            video_threading = threading.Thread(target=open_cv_thread, args=(0, fpv_event), daemon=True)
            video_threading.start()
            btn_FPV.config(bg='#00E676')
            btn_FPV['state'] = 'normal'
        else:
            logger.info('Cannot start FPV when not connected')
    elif fpv_event.is_set():
        logger.info('Stopping FPV')
        fpv_event.clear()
        cv2.destroyAllWindows()
        btn_FPV.config(bg=color_btn)
        btn_FPV['state'] = 'normal'


def all_btn_red():
    btn_ultra.config(bg='#FF6D00', fg='#000000')
    btn_find_color.config(bg='#FF6D00', fg='#000000')
    btn_watchdog.config(bg='#FF6D00', fg='#000000')


def all_btn_normal():
    btn_ultra.config(bg=color_btn, fg=color_text)
    btn_find_color.config(bg=color_btn, fg=color_text)
    btn_watchdog.config(bg=color_btn, fg=color_text)
    funcMode = 0


def status_receive_thread(arg, event):
    logger.debug('Thread started')
    global funcMode, ultrasonic_mode, canvas_rec, canvas_text, sport_mode_on, tcp_client_socket, BUFFER_SIZE
    while event.is_set():
        try:
            status_data = (tcp_client_socket.recv(BUFFER_SIZE)).decode()
            if not status_data:
                continue
            elif 'SportModeOn' in status_data:
                sport_mode_on = 1
                btn_sport.config(bg='#00E676')
            elif 'SportModeOff' in status_data:
                sport_mode_on = 0
                btn_sport.config(bg='#F44336')
            elif 'FindColor' in status_data:
                funcMode = 1
                all_btn_red()
                btn_find_color.config(bg='#00E676')
            elif 'Ultrasonic' in status_data:
                funcMode = 1
                all_btn_red()
                btn_ultra.config(bg='#00E676')
            elif 'WatchDog' in status_data:
                funcMode = 1
                all_btn_red()
                btn_watchdog.config(bg='#00E676')
            elif 'FindLine' in status_data:
                funcMode = 1
                all_btn_red()
                btn_find_line.config(bg='#00E676')
            elif 'func_end' in status_data:
                all_btn_normal()
                ultrasonic_mode = 0
                canvas_rec = canvas_ultra.create_rectangle(0, 0, 352, 30, fill=color_btn, width=0)
                canvas_text = canvas_ultra.create_text((90, 11), text='Ultrasonic OFF', fill=color_text)
            time.sleep(0.5)
        except:
            disconnect()
            logger.error('Thread exception: %s', traceback.format_exc())
    logger.debug('Thread stopped')


def stat_receive_thread(arg, event):
    logger.debug('Thread started')
    global cpu_temp, cpu_use, ram_use, connect_event, INFO_PORT
    addr = ('', INFO_PORT)
    info_sock = socket(AF_INET, SOCK_STREAM)
    info_sock.setsockopt(SOL_SOCKET, SO_REUSEADDR, 1)
    info_sock.bind(addr)
    info_sock.listen(5)  # Start server,waiting for client
    info_sock, addr = info_sock.accept()
    logger.info('Info port connected')
    while event.is_set():
        try:
            info_data = str(info_sock.recv(BUFFER_SIZE).decode())
            info_get = info_data.split()
            if info_get.__len__() == 3:
                cpu_temp, cpu_use, ram_use = info_get
                logger.debug('cpu_tem:%s, cpu_use:%s, ram_use:%s' % (cpu_temp, cpu_use, ram_use))
                label_cpu_temp.config(text='CPU Temp: %s℃' % cpu_temp)
                label_cpu_use.config(text='CPU Usage: %s' % cpu_use)
                label_ram_use.config(text='RAM Usage: %s' % ram_use)
                retries = 0
            elif retries >= 10:
                logger.error('Maximum retires reached (%d), disconnecting', retries)
                disconnect()
            else:
                logger.warning('Invalid info_data received from server: "%s"', info_data)
                label_cpu_temp.config(text='CPU Temp: -')
                label_cpu_use.config(text='CPU Usage: -')
                label_ram_use.config(text='RAM Usage: -')
                retries = retries + 1
        except:
            logger.error('Connection error, disconnecting')
            disconnect()
            logger.error('Thread exception: %s', traceback.format_exc())
    logger.debug('Thread stopped')


def ultra_receive(arg, event):
    logger.debug('Thread started')
    global ultra_data, canvas_text, canvas_rec, ULTRA_PORT, BUFFER_SIZE
    ultra_addr = ('', ULTRA_PORT)
    ultra_sock = socket(AF_INET, SOCK_STREAM)
    ultra_sock.setsockopt(SOL_SOCKET, SO_REUSEADDR, 1)
    ultra_sock.bind(ultra_addr)
    ultra_sock.listen(5)  # Start server,waiting for client
    ultra_sock, addr = ultra_sock.accept()
    canvas_text = canvas_ultra.create_text((90, 11), text='Ultrasonic OFF', fill=color_text)
    while event.is_set():
        try:
            ultra_data = str(ultra_sock.recv(BUFFER_SIZE).decode())
            ultra_data = float(ultra_data)
            if float(ultra_data) < 3:
                logger.debug('Ultrasonic data received (%s)', ultra_data)
                canvas_ultra.delete(canvas_text)
                canvas_ultra.delete(canvas_rec)
                # canvas_rec=canvas_ultra.create_rectangle(0,0,int(float(ultra_data)/145*3),30,fill = '#FFFFFF')
                canvas_rec = canvas_ultra.create_rectangle(0, 0, (352 - int(float(ultra_data) * 352 / 3)), 30,
                                                           fill='#448AFF', width=0)
                canvas_text = canvas_ultra.create_text((90, 11), text='Ultrasonic Output: %sm' % ultra_data,
                                                       fill=color_text)
        except:
            logger.error('Ultrasonic exception: %s', traceback.format_exc())
            pass
    logger.debug('Thread stopped')


def connect():  # Call this function to connect with the server
    global connect_event, addr, tcp_client_socket, BUFFER_SIZE, SERVER_PORT
    if str(btn_connect['state']) == 'normal':
        btn_connect['state'] = 'disabled'
    if not connect_event.is_set():
        logger.info('Connecting to server')
        ip_address = e1.get()  # Get the IP address from Entry
        if ip_address == '':  # If no input IP address in Entry,import a default IP
            ip_address = num_import('IP:')
            label_ip_1.config(text='Connecting')
            label_ip_1.config(bg='#FF8F00')
            label_ip_2.config(text='Default: %s' % ip_address)
            pass
        server_ip = ip_address
        addr = (server_ip, SERVER_PORT)
        tcp_client_socket = socket(AF_INET, SOCK_STREAM)  # Set connection value for socket
        try:
            for i in range(1, 6):  # Try 5 times if disconnected
                if not connect_event.is_set():
                    logger.info("Connecting to server @ %s:%d..." % (server_ip, SERVER_PORT))
                    tcp_client_socket.connect(addr)  # Connection with the server
                    logger.info("Connected successfully")
                    label_ip_2.config(text='IP: %s' % ip_address)
                    label_ip_1.config(text='Connected')
                    label_ip_1.config(bg='#558B2F')
                    replace_num('IP:', ip_address)
                    e1.config(state='disabled')
                    btn_connect.config(state='normal')
                    btn_connect.config(text='Disconnect')
                    connect_event.set()  # Set to start threads
                    status_threading = threading.Thread(target=status_receive_thread, args=(0, connect_event),
                                                        daemon=True)
                    status_threading.start()
                    info_threading = threading.Thread(target=stat_receive_thread, args=(0, connect_event), daemon=True)
                    info_threading.start()
                    ultra_threading = threading.Thread(target=ultra_receive, args=(0, connect_event), daemon=True)
                    ultra_threading.start()
                    break
                else:
                    logger.error("Cannot connect to server")
                    label_ip_1.config(text='Try %d/5 time(s)' % i)
                    label_ip_1.config(bg='#EF6C00')
                    logger.info('Try %d/5 time(s)' % i)
                    time.sleep(1)
                    continue
        except:
            logger.error('Unable to connect: %s', traceback.format_exc())
        if not connect_event.is_set():
            label_ip_1.config(text='Disconnected')
            label_ip_1.config(bg='#F44336')
            btn_connect.config(state='normal')
    elif connect_event.is_set():
        disconnect()


def disconnect():
    logger.info('Disconnecting from server')
    global fpv_event, connect_event, tcp_client_socket
    fpv_event.clear()  # Clear to kill threads
    if connect_event.is_set():
        try:
            tcp_client_socket.send('disconnect'.encode())
        except:
            logger.error('Unable to send disconnect to server, quit anyway')
        connect_event.clear()
        time.sleep(1)
        tcp_client_socket.close()  # Close socket or it may not connect with the server again
    else:
        connect_event.clear()
    btn_connect.config(text='Connect', fg=color_text, bg=color_btn)
    btn_connect.config(state='normal')
    label_ip_1.config(text='Disconnected', fg=color_text, bg='#F44336')
    all_btn_normal()


def set_R(event):
    time.sleep(0.03)
    tcp_client_socket.send(('wsR %s' % var_R.get()).encode())


def set_G(event):
    time.sleep(0.03)
    tcp_client_socket.send(('wsG %s' % var_G.get()).encode())


def set_B(event):
    time.sleep(0.03)
    tcp_client_socket.send(('wsB %s' % var_B.get()).encode())


def loop():  # GUI
    global tcp_client_socket, root, e1, label_ip_1, label_ip_2, color_btn, color_text, btn_connect, label_cpu_temp, label_cpu_use, label_ram_use, canvas_ultra, color_text, var_R, var_B, var_G, btn_ultra, btn_find_color, btn_watchdog, btn_find_line, btn_audio, btn_quit, e2, btn_sport, e2, btn_FPV  # The value of tcpClicSock changes in the function loop(),would also changes in global so the other functions could use it.
    color_bg = '#000000'  # Set background color
    color_text = '#E1F5FE'  # Set text color
    color_btn = '#0277BD'  # Set button color
    color_line = '#01579B'  # Set line color
    color_can = '#212121'  # Set canvas color
    color_oval = '#2196F3'  # Set oval color
    target_color = '#FF6D00'
    root.title('AWR')  # Main window title
    root.geometry('565x510')  # Main window size, middle of the English letter x.
    root.config(bg=color_bg)  # Set the background color of root window

    label_cpu_temp = tk.Label(root, width=18, text='CPU Temp:', fg=color_text, bg='#212121')
    label_cpu_use = tk.Label(root, width=18, text='CPU Usage:', fg=color_text, bg='#212121')
    label_ram_use = tk.Label(root, width=18, text='RAM Usage:', fg=color_text, bg='#212121')
    label_ip_0 = tk.Label(root, width=18, text='Status', fg=color_text, bg=color_btn)
    label_ip_1 = tk.Label(root, width=18, text='Disconnected', fg=color_text, bg='#F44336')
    label_ip_2 = tk.Label(root, width=18, text='Use default IP', fg=color_text, bg=color_btn)
    label_ip_3 = tk.Label(root, width=10, text='IP Address:', fg=color_text, bg='#000000')
    label_open_cv = tk.Label(root, width=28, text='OpenCV Status', fg=color_text, bg=color_btn)
    label_cpu_temp.place(x=400, y=15)  # Define a Label and put it in position
    label_cpu_use.place(x=400, y=45)  # Define a Label and put it in position
    label_ram_use.place(x=400, y=75)  # Define a Label and put it in position
    label_ip_0.place(x=30, y=110)  # Define a Label and put it in position
    label_ip_1.place(x=400, y=110)  # Define a Label and put it in position
    label_ip_2.place(x=400, y=145)  # Define a Label and put it in position
    label_ip_3.place(x=175, y=15)  # Define a Label and put it in position
    label_open_cv.place(x=180, y=110)  # Define a Label and put it in position

    e1 = tk.Entry(root, show=None, width=16, bg="#37474F", fg='#eceff1')
    e2 = tk.Entry(root, show=None, width=71, bg="#37474F", fg='#eceff1')
    e1.place(x=180, y=40)  # Define a Entry and put it in position
    e2.place(x=30, y=300)  # Define a Label and put it in position

    btn_connect = tk.Button(root, width=8, height=2, text='Connect', fg=color_text, bg=color_btn, command=connect,
                            relief='ridge')
    btn0 = tk.Button(root, width=8, text='Forward', fg=color_text, bg=color_btn, relief='ridge')
    btn1 = tk.Button(root, width=8, text='Backward', fg=color_text, bg=color_btn, relief='ridge')
    btn2 = tk.Button(root, width=8, text='Left', fg=color_text, bg=color_btn, relief='ridge')
    btn3 = tk.Button(root, width=8, text='Right', fg=color_text, bg=color_btn, relief='ridge')
    btn_up = tk.Button(root, width=8, text='Up', fg=color_text, bg=color_btn, relief='ridge')
    btn_down = tk.Button(root, width=8, text='Down', fg=color_text, bg=color_btn, relief='ridge')
    btn_sport = tk.Button(root, width=8, text='GT', bg='#F44336', fg='#FFFFFF', relief='ridge')
    btn_home = tk.Button(root, width=8, text='Home', fg=color_text, bg=color_btn, relief='ridge')
    btn_FPV = tk.Button(root, width=8, text='Video', fg=color_text, bg=color_btn, relief='ridge')
    btn_e2 = tk.Button(root, width=10, text='Send', fg=color_text, bg=color_btn, relief='ridge')

    btn_connect.place(x=315, y=15)  # Define a Button and put it in position
    btn0.place(x=100, y=195)
    btn1.place(x=100, y=230)
    btn2.place(x=30, y=230)
    btn3.place(x=170, y=230)
    btn_up.place(x=400, y=195)
    btn_down.place(x=400, y=230)
    btn_home.place(x=250, y=230)
    btn_FPV.place(x=315, y=60)  # Define a Button and put it in position
    btn_e2.place(x=470, y=300)  # Define a Button and put it in position
    btn_sport.place(x=250, y=195)

    canvas_ultra = tk.Canvas(root, bg=color_btn, height=23, width=352, highlightthickness=0)
    canvas_ultra.place(x=30, y=145)

    ################################
    # canvas_rec=canvas_ultra.create_rectangle(0,0,340,30,fill = '#FFFFFF',width=0)
    # canvas_text=canvas_ultra.create_text((90,11),text='Ultrasonic Output: 0.75m',fill=color_text)
    ################################

    var_R = tk.StringVar()
    var_R.set(0)

    scale_R = tk.Scale(root, label=None, from_=0, to=255, orient=tk.HORIZONTAL, length=505, showvalue=1,
                       tickinterval=None, resolution=1, variable=var_R, troughcolor='#F44336', command=set_R,
                       fg=color_text, bg=color_bg, highlightthickness=0)
    scale_R.place(x=30, y=330)  # Define a Scale and put it in position

    var_G = tk.StringVar()
    var_G.set(0)

    scale_G = tk.Scale(root, label=None, from_=0, to=255, orient=tk.HORIZONTAL, length=505, showvalue=1,
                       tickinterval=None, resolution=1, variable=var_G, troughcolor='#00E676', command=set_G,
                       fg=color_text, bg=color_bg, highlightthickness=0)
    scale_G.place(x=30, y=360)  # Define a Scale and put it in position

    var_B = tk.StringVar()
    var_B.set(0)

    scale_B = tk.Scale(root, label=None, from_=0, to=255, orient=tk.HORIZONTAL, length=505, showvalue=1,
                       tickinterval=None, resolution=1, variable=var_B, troughcolor='#448AFF', command=set_B,
                       fg=color_text, bg=color_bg, highlightthickness=0)
    scale_B.place(x=30, y=390)  # Define a Scale and put it in position

    canvas_cover = tk.Canvas(root, bg=color_bg, height=30, width=510, highlightthickness=0)
    canvas_cover.place(x=30, y=420)

    btn_ultra = tk.Button(root, width=10, text='Ultrasonic', fg=color_text, bg=color_btn, relief='ridge')
    btn_ultra.place(x=30, y=445)
    btn_ultra.bind('<ButtonPress-1>', call_ultra)

    btn_find_color = tk.Button(root, width=10, text='FindColor', fg=color_text, bg=color_btn, relief='ridge')
    btn_find_color.place(x=115, y=445)
    btn_find_color.bind('<ButtonPress-1>', call_find_color)

    btn_watchdog = tk.Button(root, width=10, text='WatchDog', fg=color_text, bg=color_btn, relief='ridge')
    btn_watchdog.place(x=200, y=445)
    btn_watchdog.bind('<ButtonPress-1>', call_watchdog)

    btn_find_line = tk.Button(root, width=10, text='FindLine', fg=color_text, bg=color_btn, relief='ridge')
    btn_find_line.place(x=285, y=445)
    btn_find_line.bind('<ButtonPress-1>', call_find_line)

    btn_audio = tk.Button(root, width=10, text='Audio On', fg=color_text, bg=color_btn, relief='ridge')
    btn_audio.place(x=370, y=445)
    btn_audio.bind('<ButtonPress-1>', call_stream_audio)

    btn_quit = tk.Button(root, width=10, text='Quit', fg=color_text, bg=color_btn, relief='ridge')
    btn_quit.place(x=455, y=445)
    btn_quit.bind('<ButtonPress-1>', terminate)

    btn0.bind('<ButtonPress-1>', call_forward)
    btn1.bind('<ButtonPress-1>', call_back)
    btn2.bind('<ButtonPress-1>', call_left)
    btn3.bind('<ButtonPress-1>', call_right)
    btn_up.bind('<ButtonPress-1>', call_head_up)
    btn_down.bind('<ButtonPress-1>', call_head_down)
    btn_home.bind('<ButtonPress-1>', call_head_home)
    btn_FPV.bind('<ButtonRelease-1>', call_fpv)
    btn_e2.bind('<ButtonRelease-1>', send_command)
    btn_sport.bind('<ButtonPress-1>', call_sport_mode)
    btn0.bind('<ButtonRelease-1>', call_stop)
    btn1.bind('<ButtonRelease-1>', call_stop)
    btn2.bind('<ButtonRelease-1>', call_turn_stop)
    btn3.bind('<ButtonRelease-1>', call_turn_stop)
    root.bind_all('<KeyPress-Return>', send_command)
    root.bind_all('<Button-1>', focus)
    bind_keys()
    root.protocol("WM_DELETE_WINDOW", callback)
    root.mainloop()  # Run the mainloop()


# This method is used to get
# the name of the widget
# which currently has the focus
# by clicking Mouse Button-1
def focus(event):
    if str(root.focus_get()) == '.!entry2':
        unbind_keys()


def callback():
    terminate(0)
    pass


def terminate(event):
    global exit_flag, root
    exit_flag = 1
    disconnect()
    time.sleep(0.5)
    root.destroy()


def send_command(event):
    global tcp_client_socket, connect_event
    if str(e2.get()).encode() != '' and connect_event.is_set():
        tcp_client_socket.send(str(e2.get()).encode())
        e1.focus_set()
        e2.delete(0, 'end')
    bind_keys()


def call_stream_audio(event):
    tcp_client_socket.send('stream_audio'.encode())


def bind_keys():
    global root
    root.bind('<KeyPress-f>', call_sport_mode)
    root.bind('<KeyPress-i>', call_head_up)
    root.bind('<KeyPress-k>', call_head_down)
    root.bind('<KeyPress-h>', call_head_home)
    root.bind('<KeyPress-w>', call_forward)
    root.bind('<KeyPress-s>', call_back)
    root.bind('<KeyPress-a>', call_left)
    root.bind('<KeyPress-d>', call_right)

    root.bind('<KeyRelease-q>', call_turn_stop)
    root.bind('<KeyRelease-e>', call_turn_stop)

    root.bind('<KeyRelease-w>', call_stop)
    root.bind('<KeyRelease-s>', call_stop)
    root.bind('<KeyRelease-a>', call_turn_stop)
    root.bind('<KeyRelease-d>', call_turn_stop)

    root.bind('<KeyPress-z>', call_ultra)
    root.bind('<KeyPress-x>', call_find_color)
    root.bind('<KeyPress-c>', call_watchdog)
    root.bind('<KeyPress-v>', call_find_line)
    root.bind('<KeyPress-b>', call_stream_audio)
    logger.debug('Bind KeyPress')


def unbind_keys():
    global root
    root.unbind('<KeyPress-w>')
    root.unbind('<KeyPress-s>')
    root.unbind('<KeyPress-a>')
    root.unbind('<KeyPress-d>')

    root.unbind('<KeyRelease-w>')
    root.unbind('<KeyRelease-s>')
    root.unbind('<KeyRelease-a>')
    root.unbind('<KeyRelease-d>')

    root.unbind('<KeyPress-i>')
    root.unbind('<KeyPress-k>')
    root.unbind('<KeyPress-h>')
    root.unbind('<KeyPress-z>')
    root.unbind('<KeyPress-x>')
    root.unbind('<KeyPress-c>')
    root.unbind('<KeyPress-v>')
    root.unbind('<KeyPress-b>')
    logger.debug('Unbind KeyPress')


if __name__ == '__main__':
    loop()
