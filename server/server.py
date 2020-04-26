#!/usr/bin/env/python
# File name   : server.py
# Production  : RaspRover
# Website     : www.adeept.com
# E-mail      : support@adeept.com
# Author      : William
# Date        : 2019/02/23
import logging
import os
import socket
import subprocess
import threading
import time
import traceback

import psutil

import config
import findline
import fpv
import led
import move
import servo
import speak_dict
import ultra
from speak import speak

logger = logging.getLogger(__name__)

new_frame = 0
direction_command = 'no'
turn_command = 'no'
pos_input = 1
catch_input = 1
cir_input = 6

ultrasonicMode = 0
FindLineMode = 0
FindColorMode = 0

sport_mode_on = 0

addr = None
tcp_server_socket = None
tcp_server = None
HOST = ''
ADDR = (HOST, config.SERVER_PORT)
kill_event = threading.Event()
ultra_event = threading.Event()

server_address = ''
stream_audio_started = 0

led = led.Led()
fpv = fpv.Fpv()


def findline_thread():  # Line tracking mode
    while 1:
        while FindLineMode:
            findline.run()
        time.sleep(0.2)


def get_cpu_tempfunc():
    """ Return CPU temperature """
    result = 0
    mypath = "/sys/class/thermal/thermal_zone0/temp"
    with open(mypath, 'r') as mytmpfile:
        for line in mytmpfile:
            result = line

    result = float(result) / 1000
    result = round(result, 1)
    return str(result)


def get_gpu_tempfunc():
    """ Return GPU temperature as a character string"""
    res = os.popen('/opt/vc/bin/vcgencmd measure_temp').readline()
    return res.replace("temp=", "")


def get_cpu_use():
    """ Return CPU usage using psutil"""
    cpu_cent = psutil.cpu_percent()
    return str(cpu_cent)


def get_ram_info():
    """ Return RAM usage using psutil """
    ram_cent = psutil.virtual_memory()[2]
    return str(ram_cent)


def get_swap_info():
    """ Return swap memory  usage using psutil """
    swap_cent = psutil.swap_memory()[3]
    return str(swap_cent)


def info_get():
    global cpu_t, cpu_u, gpu_t, ram_info
    while 1:
        cpu_t = get_cpu_tempfunc()
        cpu_u = get_cpu_use()
        ram_info = get_ram_info()
        time.sleep(3)


def info_send_client():
    logger.info('Starting info thread.')
    SERVER_IP = addr[0]
    SERVER_ADDR = (SERVER_IP, config.INFO_PORT)
    Info_Socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)  # Set connection value for socket
    Info_Socket.connect(SERVER_ADDR)
    logger.debug(SERVER_ADDR)
    while 1:
        try:
            Info_Socket.send((get_cpu_tempfunc() + ' ' + get_cpu_use() + ' ' + get_ram_info()).encode())
            time.sleep(1)
        except:
            pass


def ultra_send_client(event):
    global ultra_event
    logger.info('Starting ultrasonic thread.')
    ultra_IP = addr[0]
    ultra_ADDR = (ultra_IP, config.ULTRA_PORT)
    ultra_Socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)  # Set connection value for socket
    ultra_Socket.connect(ultra_ADDR)
    logger.debug(ultra_ADDR)
    while event.is_set() and ultrasonicMode:
        try:
            if not FindColorMode:
                ultra_Socket.send(str(round(ultra.checkdist(), 2)).encode())
                time.sleep(0.5)
                continue
            fpv.UltraData(round(ultra.checkdist(), 2))
            time.sleep(0.2)
        except:
            logger.error('Exception: %s', traceback.format_exc())
            break
    time.sleep(0.5)
    ultra_event.clear()


def ap_thread():
    logger.info('Starting AP thread.')
    os.system("sudo create_ap wlan0 eth0 AdeeptCar 12345678")


def run():
    global direction_command, turn_command, pos_input, catch_input, cir_input, ultrasonicMode, FindLineMode, FindColorMode, sport_mode_on
    move.setup()
    findline.setup()

    info_threading = threading.Thread(target=info_send_client)  # Define a thread for FPV and OpenCV
    info_threading.setDaemon(True)  # 'True' means it is a front thread,it would close when the mainloop() closes
    info_threading.start()  # Thread starts

    findline_threading = threading.Thread(target=findline_thread)  # Define a thread for FPV and OpenCV
    findline_threading.setDaemon(True)  # 'True' means it is a front thread,it would close when the mainloop() closes
    findline_threading.start()  # Thread starts

    ws_R = 0
    ws_G = 0
    ws_B = 0

    Y_pitch = 0
    Y_pitch_MAX = 200
    Y_pitch_MIN = -200

    while not kill_event.is_set():
        data = ''
        data = str(tcp_server_socket.recv(config.BUFFER_SIZE).decode())
        if not data:
            continue
        elif 'sport_mode_on' == data:
            sport_mode_on = 1
            tcp_server_socket.send(('sport_mode_on').encode())

        elif 'sport_mode_off' == data:
            sport_mode_on = 0
            tcp_server_socket.send(('sport_mode_off').encode())

        elif 'forward' == data:
            direction_command = 'forward'
            if sport_mode_on:
                move.move(config.SPEED_FAST, direction_command, turn_command, config.RADIUS)
            else:
                move.move(config.SPEED_BASE, direction_command, turn_command, config.RADIUS)
        elif 'backward' == data:
            direction_command = 'backward'
            if sport_mode_on:
                move.move(config.SPEED_FAST, direction_command, turn_command, config.RADIUS)
            else:
                move.move(config.SPEED_BASE, direction_command, turn_command, config.RADIUS)
        elif 'DS' in data:
            direction_command = 'no'
            if sport_mode_on:
                move.move(config.SPEED_FAST, direction_command, turn_command, config.RADIUS)
            else:
                move.move(config.SPEED_BASE, direction_command, turn_command, config.RADIUS)

        elif 'left' == data:
            turn_command = 'left'
            if sport_mode_on:
                move.move(config.SPEED_FAST, direction_command, turn_command, config.RADIUS)
            else:
                move.move(config.SPEED_BASE, direction_command, turn_command, config.RADIUS)
        elif 'right' == data:
            turn_command = 'right'
            if sport_mode_on:
                move.move(config.SPEED_FAST, direction_command, turn_command, config.RADIUS)
            else:
                move.move(config.SPEED_BASE, direction_command, turn_command, config.RADIUS)
        elif 'TS' in data:
            turn_command = 'no'
            move.move(config.SPEED_FAST, direction_command, turn_command, config.RADIUS)

        elif 'headup' == data:
            servo.camera_ang('lookup', 'no')
        elif 'headdown' == data:
            servo.camera_ang('lookdown', 'no')
        elif 'headhome' == data:
            servo.camera_ang('home', 'no')
            time.sleep(0.2)
            servo.clean_all()

        elif 'wsR' in data:
            try:
                set_R = data.split()
                ws_R = int(set_R[1])
                led.colorWipe([ws_G, ws_R, ws_B])
            except:
                pass
        elif 'wsG' in data:
            try:
                set_G = data.split()
                ws_G = int(set_G[1])
                led.colorWipe([ws_G, ws_R, ws_B])
            except:
                pass
        elif 'wsB' in data:
            try:
                set_B = data.split()
                ws_B = int(set_B[1])
                led.colorWipe([ws_G, ws_R, ws_B])
            except:
                pass

        elif 'FindColor' == data:
            fpv.FindColor(1)
            FindColorMode = 1
            ultrasonicMode = 1
            tcp_server_socket.send(('FindColor').encode())

        elif 'WatchDog' == data:
            fpv.WatchDog(1)
            tcp_server_socket.send(('WatchDog').encode())

        elif 'Ultrasonic' == data:
            ultrasonicMode = 1
            tcp_server_socket.send(('Ultrasonic').encode())
            ultra_event.set()
            ultra_threading = threading.Thread(target=ultra_send_client, args=([ultra_event]), daemon=True)
            ultra_threading.start()  # Thread starts

        elif 'Ultrasonic_end' == data:
            ultrasonicMode = 0
            ultra_event.clear()
            tcp_server_socket.send(('Ultrasonic_end').encode())

        elif 'FindLine' == data:
            FindLineMode = 1
            tcp_server_socket.send(('FindLine').encode())

        elif 'func_end' == data:
            fpv.FindColor(0)
            fpv.WatchDog(0)
            FindLineMode = 0
            FindColorMode = 0
            tcp_server_socket.send(('func_end').encode())
            move.motorStop()

        elif 'stream_audio' == data:
            global server_address, stream_audio_started
            if stream_audio_started == 0:
                logger.info('Audio streaming server starting...')
                subprocess.Popen([str(
                    'cvlc -vvv alsa://hw:1,0 :live-caching=50 --sout "#standard{access=http,mux=ogg,dst=' + server_address + ':3030}"')],
                    shell=True)
                stream_audio_started = 1
            else:
                logger.info('Audio streaming server already started.')
            tcp_server_socket.send('stream_audio'.encode())
        elif 'start_video' == data:
            config.VIDEO_OUT = 1
            tcp_server_socket.send('start_video'.encode())
        elif 'stop_video' == data:
            config.VIDEO_OUT = 0
            tcp_server_socket.send('stop_video'.encode())
        elif 'disconnect' == data:
            tcp_server_socket.send('disconnect'.encode())
            disconnect()
        else:
            logger.info('Speaking command received')
            speak(data)
            pass


def main():
    global kill_event, ADDR
    kill_event.clear()
    try:
        led.colorWipe([255, 16, 0])
    except:
        logger.warning('Use "sudo pip3 install rpi_ws281x" to install WS_281x package')
        pass
    while 1:
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("1.1.1.1", 80))
            global server_address
            server_address = s.getsockname()[0]
            s.close()
            logger.info('Server listening on: %s:%s', server_address, config.SERVER_PORT)
        except:
            ap_threading = threading.Thread(target=ap_thread)  # Define a thread for data receiving
            ap_threading.setDaemon(True)  # 'True' means it is a front thread,it would close when the mainloop() closes
            ap_threading.start()  # Thread starts
            led.colorWipe([0, 16, 50])
            time.sleep(1)
            led.colorWipe([0, 16, 100])
            time.sleep(1)
            led.colorWipe([0, 16, 150])
            time.sleep(1)
            led.colorWipe([0, 16, 200])
            time.sleep(1)
            led.colorWipe([0, 16, 255])
            time.sleep(1)
            led.colorWipe([35, 255, 35])
        try:
            global tcp_server_socket, tcp_server
            global addr
            tcp_server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            tcp_server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            tcp_server.bind(ADDR)
            tcp_server.listen(5)  # Start server,waiting for client
            logger.info('Waiting for connection...')
            speak(speak_dict.hello)
            tcp_server_socket, addr = tcp_server.accept()
            logger.info('Connected from %s', addr)
            speak(speak_dict.connect)
            global fpv
            fps_threading = threading.Thread(target=fpv.fpv_capture_thread, args=(addr[0], kill_event),
                                             daemon=True)  # Define a thread for FPV and OpenCV
            fps_threading.start()  # Thread starts
            break
        except:
            led.colorWipe([0, 0, 0])

        try:
            led.colorWipe([0, 80, 255])
        except:
            logger.error('Exception while waiting for connection: %s', traceback.format_exc())
            kill_event.set()
            led.colorWipe([0, 0, 0])
            pass

    try:
        run()
    except:
        logger.error('Run exception, terminate and restart main(). %s', traceback.format_exc())
        disconnect()
        main()


def disconnect():
    logger.info('Disconnecting and termination threads.')
    speak(speak_dict.disconnect)
    global tcp_server_socket, tcp_server, kill_event
    kill_event.set()
    led.colorWipe([0, 0, 0])
    servo.clean_all()
    move.destroy()
    time.sleep(2)
    tcp_server.close()
    tcp_server_socket.close()
    main()


if __name__ == "__main__":
    main()
