#!/usr/bin/env/python
# E-mail      : sect16@gmail.com
# Author      : Chin Pin Hon
# Date        : 14.01.2020

"""
This file contains constants and global variables.
"""

import cv2

TITLE = 'Mini Robot'
COLOR_SWT_ACT = '#4CAF50'
COLOR_BTN_ACT = '#00E676'
COLOR_BG = '#000000'  # Set background color
COLOR_TEXT = '#E1F5FE'  # Set text color
COLOR_BTN = '#0277BD'  # Set button color
COLOR_GREY = '#A7A7A7'
LABEL_BG = '#F44336'
# color_line = '#01579B'  # Set line color
# color_can = '#212121'  # Set canvas color
# color_oval = '#2196F3'  # Set oval color
COLOR_BTN_RED = '#FF6D00'
FONT = cv2.FONT_HERSHEY_SIMPLEX
MAX_CONTOUR_AREA = 5000

# Configuration
INFO_PORT = 2256  # Define port serial
MAX_INFO_RETRY = 10
SERVER_PORT = 10223  # Define port serial
BUFFER_SIZE = 1024
ULTRA_PORT = 2257  # Define port serial
ULTRA_SENSOR = 1
VIDEO_PORT = 5555
VIDEO_TIMEOUT = 10000
VIDEO_WIDTH = 640
VIDEO_HEIGHT = 480
POWER_MODULE = False
CAMERA_MODULE = True

ultra_data = 0

SPEED_BASE = 70
SPEED_FAST = 100
RADIUS = 0.6

guiTuple = (
    "btn_down.place(x=400, y=230)",
    "btn_home.place(x=250, y=230)",
    "btn_sport.place(x=250, y=195)",
    "canvas_ultra.place(x=30, y=145)",
    "btn_find_line.place(x=285, y=465)",
    "btn_ultra.place(x=30, y=465)",
    "canvas_ultra.place(x=30, y=145)")