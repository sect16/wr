#!/usr/bin/env/python
# File name   : config.py
# Description : Global variables across modules for DarkPaw
# E-mail      : sect16@gmail.com
# Author      : Chin Pin Hon
# Date        : 2019/11/20

import cv2

FONT = cv2.FONT_HERSHEY_SIMPLEX

SPEAK_SPEED = 120
allow_speak = 1
VIDEO_OUT = 0
last_text = ''
ULTRA_PORT = 2257
SERVER_PORT = 2256  # Define port serial
PORT = 10223  # Define port serial
BUFFER_SIZE = 1024  # Define buffer size
MAX_CONTOUR_AREA = 5000
SPEED_BASE = 50
SPEED_FAST = 100
RADIUS = 0.6
MIN_TRACK_DISTANCE = 0.4
MAX_TRACK_DISTANCE = 0.5
servo = [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]
servo_init = [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]