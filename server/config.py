#!/usr/bin/env/python
# File name   : config.py
# Description : Global variables across modules for DarkPaw
# E-mail      : sect16@gmail.com
# Author      : Chin Pin Hon
# Date        : 2019/11/20

import time

import cv2

FONT = cv2.FONT_HERSHEY_SIMPLEX
FONT_SIZE = 0.5

SPEAK_SPEED = 150
allow_speak = True
VIDEO_OUT = False
last_text = list([int(time.time()), ""])

LISTENER_MAX_ERROR = 10
LISTENER_TIMEOUT = 30
SPEAK_DELAY = 1
INFO_PORT = 2256  # Define port serial
SERVER_PORT = 10223  # Define port serial
BUFFER_SIZE = 1024  # Define buffer size
MAX_CONTOUR_AREA = 5000
VIDEO_PORT = 5555
RESOLUTION = [640, 480]
AUDIO_PORT = 3030
FRAME_RATE = 32
CAM_ANGLE = 25

# Hardware configuration
POWER_MODULE = False
SERVO_MODULE = True
CAMERA_MODULE = True

SPEED_BASE = 50
SPEED_FAST = 100
RADIUS = 0.6
ULTRA_PORT = 2257
MIN_TRACK_DISTANCE = 0.4
MAX_TRACK_DISTANCE = 0.5
servo = [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]
servo_init = [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]
