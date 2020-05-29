#!/usr/bin/env/python
# File name   : server.py
# E-mail      : sect16@gmail.com
# Author      : Chin Pin Hon
# Date        : 29/11/2019

import logging
import os
import signal
import socket
import subprocess
import sys
import threading
import time
import traceback

import psutil

import camera as cam
import config
import findline
import led
import move
import power_module as pm
import servo
import speak_dict
import switch
import ultra
from speak import speak

logger = logging.getLogger(__name__)
# Socket connection sequence. Bind socket to port, create socket, get client address/port, get server address/port.
tcp_server = None
tcp_server_socket = None
client_address = None
server_address = None
led = led.Led()
if config.CAMERA_MODULE:
    camera = cam.Camera()
kill_event = threading.Event()
ultra_event = threading.Event()
findline_event = threading.Event()


def ap_thread():
    os.system("sudo create_ap wlan0 eth0 Wally bianbian")


def get_cpu_temp():
    """ Return CPU temperature """
    result = 0
    mypath = "/sys/class/thermal/thermal_zone0/temp"
    with open(mypath, 'r') as mytmpfile:
        for line in mytmpfile:
            result = line
    result = float(result) / 1000
    result = round(result, 1)
    return str(result)


def get_gpu_temp():
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


def thread_isAlive(*args):
    """
    This function searches for the thread name defined using threading.Thread.setName() function.
    :param args: Name of the thread. Can be multiple.
    :return: Returns a boolean indicating if any of the threads was found.
    """
    logger.debug('Checking for existence of threads: %s', args)
    for thread_name in args:
        logger.debug('Looking for thread: ' + thread_name)
        lst = threading.enumerate()
        for x in lst:
            if x.name == thread_name:
                logger.debug('Found %s is active.', x)
                return True
    logger.debug('No threads found.')
    return False


def info_get():
    global cpu_t, cpu_u, gpu_t, ram_info
    while 1:
        cpu_t = get_cpu_temp()
        cpu_u = get_cpu_use()
        ram_info = get_ram_info()
        time.sleep(3)


def ultra_send_client(event):
    logger.info('Thread started')
    ultra_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)  # Set connection value for socket
    ultra_socket.connect((client_address, config.ULTRA_PORT))
    logger.info('Connected to client address (\'%s\', %i)', client_address, config.ULTRA_PORT)
    while event.is_set():
        try:
            ultra_socket.send(str(round(ultra.checkdist(), 2)).encode())
            time.sleep(0.5)
            camera.UltraData(round(ultra.checkdist(), 2))
            time.sleep(0.2)
        except:
            logger.error('Exception: %s', traceback.format_exc())
            break
    time.sleep(0.5)
    ultra_event.clear()
    logger.info('Thread stopped')


def info_thread(event):
    logger.info('Thread started')
    info_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)  # Set connection value for socket
    info_socket.connect((client_address, config.INFO_PORT))
    logger.info('Connected to client address (\'%s\', %i)', client_address, config.INFO_PORT)
    if config.POWER_MODULE:
        ina219 = pm.PowerModule()
    while not event.is_set():
        try:
            if config.POWER_MODULE:
                power = ina219.read_ina219()
                info_socket.send((get_cpu_temp() + ' ' + get_cpu_use() + ' ' + get_ram_info() + ' {0:0.2f}V'.format(
                    power[0]) + ' {0:0.2f}mA'.format(power[1])).encode())
            else:
                info_socket.send((get_cpu_temp() + ' ' + get_cpu_use() + ' ' + get_ram_info() + ' - -').encode())
            pass
            time.sleep(1)
        except BrokenPipeError:
            pass
        except:
            logger.error('Exception: %s', traceback.format_exc())
            pass
    logger.info('Thread stopped')


def connect():
    global server_address, tcp_server_socket, tcp_server, client_address
    while True:
        try:
            tcp_server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            tcp_server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            tcp_server.bind(('', config.SERVER_PORT))
            # Start server,waiting for client
            tcp_server.listen(5)
            logger.info('Waiting for connection...')
            led.color_set('cyan')
            led.mode_set(1)
            tcp_server_socket, client_address = tcp_server.accept()
            server_address = tcp_server_socket.getsockname()[0]
            # Timeout in seconds
            tcp_server_socket.settimeout(config.LISTENER_TIMEOUT)
            logger.info('Connected from %s', client_address)
            client_address = client_address[0]
            break
        except KeyboardInterrupt:
            logger.error('Exception while waiting for connection: %s', traceback.format_exc())
            kill_event.set()
            led.colorWipe([0, 0, 0])
            sys.exit()
            pass
        except:
            logger.error('Exception while waiting for connection: %s', traceback.format_exc())
            kill_event.set()
            led.colorWipe([0, 0, 0])
            pass


def disconnect():
    """
    This function shutdown all threads and performs cleanup function ensuring all thread has exited gracefully.
    It is meant to be blocking and not threaded to ensure all threads has been terminated before continuing.
    """
    global tcp_server_socket, tcp_server, kill_event
    logger.info('Disconnecting and termination threads.')
    speak(speak_dict.disconnect)
    kill_event.set()
    led.colorWipe([0, 0, 0])
    switch.switch(1, 0)
    switch.switch(2, 0)
    switch.switch(3, 0)
    time.sleep(0.5)
    tcp_server.close()
    tcp_server_socket.close()
    servo.clean_all()
    move.destroy()
    logger.info('Waiting for threads to finish.')
    while thread_isAlive('led_thread', 'camera_thread', 'info_thread', 'stream_thread',
                         'speak_thread', 'ultra_thread',
                         'move_thread'):
        time.sleep(1)
    logger.info('All threads terminated.')


def listener_thread(event):
    logger.info('Starting listener thread...')
    global camera, tcp_server_socket
    ws_G = 0
    ws_R = 0
    ws_B = 0
    audio_pid = None
    error_count = 0
    direction_command = 'no'
    turn_command = 'no'

    while not event.is_set():
        try:
            data = str(tcp_server_socket.recv(config.BUFFER_SIZE).decode())
        except socket.timeout:
            logger.warning('Listener socket timed out')
            data = ''
        if error_count >= config.LISTENER_MAX_ERROR:
            logger.error('Maximum listener error count reached, terminating thread.')
            return
        if not data:
            error_count += 1
            logger.warning('NULL message or no KEEPALIVE message received, error count: %s/%s', error_count,
                           config.LISTENER_MAX_ERROR)
            continue
        elif '|ACK|' in data:
            logger.debug('ACK message received')
            continue
        else:
            logger.info('Received data on tcp socket: %s', data)
            error_count = 0
        if 'wsR' in data:
            try:
                set_R = data.split()
                ws_R = int(set_R[1])
                led.colorWipe([ws_G, ws_R, ws_B])
            except:
                logger.error('Exception: %s', traceback.format_exc())
                pass
        elif 'wsG' in data:
            try:
                set_G = data.split()
                ws_G = int(set_G[1])
                led.colorWipe([ws_G, ws_R, ws_B])
            except:
                logger.error('Exception: %s', traceback.format_exc())
                pass
        elif 'wsB' in data:
            try:
                set_B = data.split()
                ws_B = int(set_B[1])
                led.colorWipe([ws_G, ws_R, ws_B])
            except:
                logger.error('Exception: %s', traceback.format_exc())
                pass
        elif 'Ultrasonic' == data:
            tcp_server_socket.send(('Ultrasonic').encode())
            ultra_event.set()
            ultra_threading = threading.Thread(target=ultra_send_client, args=([ultra_event]), daemon=True)
            ultra_threading.setName('ultra_thread')
            ultra_threading.start()
        elif 'Ultrasonic_end' == data:
            ultra_event.clear()
            tcp_server_socket.send(('Ultrasonic_end').encode())
        elif 'stream_audio' == data:
            global server_address
            if audio_pid is None:
                logger.info('Audio streaming server starting...')
                audio_pid = subprocess.Popen([
                    'cvlc alsa://hw:2,0 :live-caching=50 --sout "#standard{access=http,mux=ogg,dst=' + server_address + ':' + str(
                        config.AUDIO_PORT) + '}"'],
                    shell=True, preexec_fn=os.setsid)
            else:
                logger.info('Audio streaming server already started.')
            tcp_server_socket.send('stream_audio'.encode())
        elif 'stream_audio_end' == data:
            if audio_pid is not None:
                try:
                    os.killpg(os.getpgid(audio_pid.pid), signal.SIGTERM)  # Send the signal to all the process groups
                    audio_pid = None
                except:
                    logger.error('Unable to kill audio stream.')
            tcp_server_socket.send('stream_audio_end'.encode())
        elif 'start_video' == data:
            config.VIDEO_OUT = True
            tcp_server_socket.send('start_video'.encode())
        elif 'stop_video' == data:
            config.VIDEO_OUT = False
            tcp_server_socket.send('stop_video'.encode())
        elif 'FindColor' == data:
            led.mode_set(1)
            camera.FindColor(1)
            tcp_server_socket.send('FindColor'.encode())
        elif 'WatchDog' == data:
            led.mode_set(1)
            camera.WatchDog(1)
            tcp_server_socket.send('WatchDog'.encode())
        elif 'Switch_1_on' == data:
            switch.switch(1, 1)
            tcp_server_socket.send('Switch_1_on'.encode())
        elif 'Switch_1_off' == data:
            switch.switch(1, 0)
            tcp_server_socket.send('Switch_1_off'.encode())
        elif 'Switch_2_on' == data:
            switch.switch(2, 1)
            tcp_server_socket.send('Switch_2_on'.encode())
        elif 'Switch_2_off' == data:
            switch.switch(2, 0)
            tcp_server_socket.send('Switch_2_off'.encode())
        elif 'Switch_3_on' == data:
            switch.switch(3, 1)
            tcp_server_socket.send('Switch_3_on'.encode())
        elif 'Switch_3_off' == data:
            switch.switch(3, 0)
            tcp_server_socket.send('Switch_3_off'.encode())
        elif 'disconnect' == data:
            tcp_server_socket.send('disconnect'.encode())
            return
        elif 'FindLine' == data:
            findline_event.set()
            findline_threading = threading.Thread(target=findline_thread, args=([findline_event]), daemon=True)
            findline_threading.setName('findline_thread')
            findline_threading.start()
            tcp_server_socket.send(('FindLine').encode())
        elif 'func_end' == data:
            led.mode_set(0)
            camera.FindColor(0)
            camera.WatchDog(0)
            findline_event.clear()
            tcp_server_socket.send(('func_end').encode())
            move.motorStop()
        elif 'sport_mode_on' == data:
            sport_mode = True
            tcp_server_socket.send(('sport_mode').encode())
        elif 'sport_mode_off' == data:
            sport_mode = False
            tcp_server_socket.send(('sport_mode_off').encode())
        elif 'forward' == data:
            direction_command = 'forward'
            if sport_mode:
                move.move(config.SPEED_FAST, direction_command, turn_command, config.RADIUS)
            else:
                move.move(config.SPEED_BASE, direction_command, turn_command, config.RADIUS)
        elif 'backward' == data:
            direction_command = 'backward'
            if sport_mode:
                move.move(config.SPEED_FAST, direction_command, turn_command, config.RADIUS)
            else:
                move.move(config.SPEED_BASE, direction_command, turn_command, config.RADIUS)
        elif 'DS' in data:
            direction_command = 'no'
            if sport_mode:
                move.move(config.SPEED_FAST, direction_command, turn_command, config.RADIUS)
            else:
                move.move(config.SPEED_BASE, direction_command, turn_command, config.RADIUS)
        elif 'left' == data:
            turn_command = 'left'
            if sport_mode:
                move.move(config.SPEED_FAST, direction_command, turn_command, config.RADIUS)
            else:
                move.move(config.SPEED_BASE, direction_command, turn_command, config.RADIUS)
        elif 'right' == data:
            turn_command = 'right'
            if sport_mode:
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
        elif 'headAngle' == data:
            angle = data.split()
            servo.camera_ang('abs', 300 - int(angle[1]))
        else:
            logger.info('Speaking command received')
            speak(data)
            pass


def findline_thread(event):  # Line tracking mode
    while event.is_set():
        findline.run()
        time.sleep(0.2)


def main():
    logger.info('Starting server.')
    global kill_event
    switch.switchSetup()
    switch.set_all_switch_off()
    kill_event.clear()
    try:
        led_threading = threading.Thread(target=led.led_thread, args=[kill_event], daemon=True)
        led_threading.setName('led_thread')
        led_threading.start()  # Thread starts
        led.color_set('blue')
    except:
        pass
    connect()
    speak(speak_dict.connect)

    try:
        led.mode_set(0)
        led.colorWipe([255, 255, 255])
    except:
        logger.error('Exception LED: %s', traceback.format_exc())
        pass
    try:
        if config.CAMERA_MODULE:
            global camera
            camera_thread = threading.Thread(target=camera.capture_thread, args=[kill_event], daemon=True)
            camera_thread.setName('camera_thread')
            camera_thread.start()
        info_threading = threading.Thread(target=info_thread, args=[kill_event], daemon=True)
        info_threading.setName('info_thread')
        info_threading.start()
        move.setup()
        listener_thread(kill_event)
    except:
        logger.error('Exception: %s', traceback.format_exc())
    disconnect()


if __name__ == "__main__":
    try:
        while True:
            main()
    except KeyboardInterrupt:
        pass
