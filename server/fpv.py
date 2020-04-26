#!/usr/bin/env/python3
# File name   : server.py
# Description : for FPV video and OpenCV functions
# Website     : www.adeept.com
# E-mail      : support@adeept.com
# Author      : William(Based on Adrian Rosebrock's OpenCV code on pyimagesearch.com)
# Date        : 2019/02/23

import argparse
import base64
import datetime
import logging
from collections import deque

import cv2
import imutils
import numpy
import picamera
import zmq
from picamera.array import PiRGBArray

import config
import led
import move
import pid
import servo
import speak_dict
from speak import speak

logger = logging.getLogger(__name__)
pid = pid.Pid()
pid.SetKp(0.5)
pid.SetKd(0)
pid.SetKi(0)

context = zmq.Context()
footage_socket_client = None

Y_lock = 0
X_lock = 0
tor = 17
FindColorMode = 0
WatchDogMode = 0
UltraData = 0.45

led = led.Led()


class Fpv:
    def __init__(self):
        self.frame_num = 0
        self.fps = 0
        self.colorUpper = (44, 255, 255)
        self.colorLower = (24, 100, 100)

    def SetIP(self, invar):
        self.IP = invar

    def FindColor(self, invar):
        global FindColorMode, UltraData
        UltraData = 0.45
        FindColorMode = invar
        if not FindColorMode:
            servo.camera_ang('home', 0)

    def WatchDog(self, invar):
        global WatchDogMode
        WatchDogMode = invar

    def UltraData(self, invar):
        global UltraData
        UltraData = invar

    def fpv_capture_thread(self, client_ip_address, event):
        global PORT, footage_socket_client
        ap = argparse.ArgumentParser()  # OpenCV initialization
        ap.add_argument("-b", "--buffer", type=int, default=64,
                        help="max buffer size")
        args = vars(ap.parse_args())
        pts = deque(maxlen=args["buffer"])

        camera = picamera.PiCamera()
        camera.resolution = config.RESOLUTION
        camera.framerate = 20
        rawCapture = PiRGBArray(camera, size=config.RESOLUTION)

        avg = None
        motionCounter = 0
        # time.sleep(4)
        last_motion_captured = datetime.datetime.now()

        for frame in camera.capture_continuous(rawCapture, format="bgr", use_video_port=True):
            if event.is_set():
                logger.info('Kill event received, terminating FPV thread.')
                break
            frame_image = frame.array
            cv2.line(frame_image, (300, 240), (340, 240), (128, 255, 128), 1)
            cv2.line(frame_image, (320, 220), (320, 260), (128, 255, 128), 1)
            timestamp = datetime.datetime.now()

            if FindColorMode:
                ####>>>OpenCV Start<<<####
                hsv = cv2.cvtColor(frame_image, cv2.COLOR_BGR2HSV)
                mask = cv2.inRange(hsv, self.colorLower, self.colorUpper)
                mask = cv2.erode(mask, None, iterations=2)
                mask = cv2.dilate(mask, None, iterations=2)
                cnts = cv2.findContours(mask.copy(), cv2.RETR_EXTERNAL,
                                        cv2.CHAIN_APPROX_SIMPLE)[-2]
                center = None
                if len(cnts) > 0:
                    cv2.putText(frame_image, 'Target Detected', (40, 60), config.FONT, 0.5, (255, 255, 255), 1,
                                cv2.LINE_AA)
                    c = max(cnts, key=cv2.contourArea)
                    ((x, y), radius) = cv2.minEnclosingCircle(c)
                    M = cv2.moments(c)
                    center = (int(M["m10"] / M["m00"]), int(M["m01"] / M["m00"]))
                    X = int(x)
                    Y = int(y)
                    if radius > 10:
                        cv2.rectangle(frame_image, (int(x - radius), int(y + radius)),
                                      (int(x + radius), int(y - radius)), (255, 255, 255), 1)
                    logger.debug('Target input frame position X: %d Y: %d', X, Y)
                    if Y < (240 - tor):
                        error = (240 - Y) / 5
                        outv = int(round((pid.GenOut(error)), 0))
                        servo.camera_ang('lookup', outv)
                        Y_lock = 0
                    elif Y > (240 + tor):
                        error = (Y - 240) / 5
                        outv = int(round((pid.GenOut(error)), 0))
                        servo.camera_ang('lookdown', outv)
                        Y_lock = 0
                    else:
                        Y_lock = 1

                    if X < (320 - tor * 3):
                        move.move(config.SPEED_BASE, 'no', 'left', config.RADIUS)
                        # time.sleep(0.1)
                        # move.motorStop()
                        X_lock = 0
                    elif X > (330 + tor * 3):
                        move.move(config.SPEED_BASE, 'no', 'right', config.RADIUS)
                        # time.sleep(0.1)
                        # move.motorStop()
                        X_lock = 0
                    else:
                        move.motorStop()
                        X_lock = 1

                    if X_lock == 1 and Y_lock == 1:
                        if UltraData > config.MAX_TRACK_DISTANCE:
                            move.move(config.SPEED_BASE, 'forward', 'no', config.RADIUS)
                        elif UltraData < config.MIN_TRACK_DISTANCE:
                            move.move(config.SPEED_BASE, 'backward', 'no', config.RADIUS)
                            logger.debug('Ultrasonic input data: %s', UltraData)
                        else:
                            move.motorStop()


                else:
                    cv2.putText(frame_image, 'Target Detecting', (40, 60), config.FONT, 0.5, (255, 255, 255), 1, cv2.LINE_AA)
                    move.motorStop()

                for i in range(1, len(pts)):
                    if pts[i - 1] is None or pts[i] is None:
                        continue
                    thickness = int(numpy.sqrt(args["buffer"] / float(i + 1)) * 2.5)
                    cv2.line(frame_image, pts[i - 1], pts[i], (0, 0, 255), thickness)
                ####>>>OpenCV Ends<<<####

            if WatchDogMode:
                gray = cv2.cvtColor(frame_image, cv2.COLOR_BGR2GRAY)
                gray = cv2.GaussianBlur(gray, (21, 21), 0)

                if avg is None:
                    logger.info("Starting background model for watchdog...")
                    avg = gray.copy().astype("float")
                    rawCapture.truncate(0)
                    continue

                cv2.accumulateWeighted(gray, avg, 0.5)
                frameDelta = cv2.absdiff(gray, cv2.convertScaleAbs(avg))

                # threshold the delta image, dilate the thresholded image to fill
                # in holes, then find contours on thresholded image
                thresh = cv2.threshold(frameDelta, 5, 255,
                                       cv2.THRESH_BINARY)[1]
                thresh = cv2.dilate(thresh, None, iterations=2)
                cnts = cv2.findContours(thresh.copy(), cv2.RETR_EXTERNAL,
                                        cv2.CHAIN_APPROX_SIMPLE)
                cnts = imutils.grab_contours(cnts)
                # loop over the contours
                for c in cnts:
                    # if the contour is too small, ignore it
                    if cv2.contourArea(c) < config.MAX_CONTOUR_AREA:
                        logger.debug('Contour too small (%s), ignoring...', cv2.contourArea(c))
                        continue
                    else:
                        speak(speak_dict.bark)

                    # compute the bounding box for the contour, draw it on the frame,
                    # and update the text
                    (x, y, w, h) = cv2.boundingRect(c)
                    cv2.rectangle(frame_image, (x, y), (x + w, y + h), (128, 255, 0), 1)
                    text = "Occupied"
                    motionCounter += 1
                    logger.info('Motion frame counter: %s', motionCounter)
                    led.colorWipe([255, 16, 0])
                    last_motion_captured = timestamp
                '''
                if (timestamp - last_motion_captured).seconds >= 0.5:
                    led.colorWipe(Color(255,255,0))
                '''
                if (timestamp - last_motion_captured).seconds >= 0.5:
                    logger.debug('No motion detected.')
                    led.colorWipe([255, 255, 0])

            if config.VIDEO_OUT == 1:
                if footage_socket_client is None:
                    logger.info('Initializing ZMQ client...')
                    init_client(client_ip_address)
                encoded, buffer = cv2.imencode('.jpg', frame_image)
                jpg_as_text = base64.b64encode(buffer)
                # logger.debug('Sending footage using ZMQ')
                footage_socket_client.send(jpg_as_text)
            elif config.VIDEO_OUT == 0 and footage_socket_client is not None:
                logger.info('Terminating ZMQ client.')
                footage_socket_client.close()
                footage_socket_client = None
            rawCapture.truncate(0)
        logger.debug('Stopping thread')
        camera.close()


def init_client(client_ip_address):
    global footage_socket_client
    logger.debug('Capture connection (%s:%s)', client_ip_address, config.FPV_PORT)
    footage_socket_client = context.socket(zmq.PUB)
    footage_socket_client.setsockopt(zmq.LINGER, 0)
    footage_socket_client.setsockopt(zmq.BACKLOG, 0)
    footage_socket_client.connect('tcp://%s:%d' % (client_ip_address, config.FPV_PORT))


if __name__ == '__main__':
    fpv = Fpv()
    while 1:
        fpv.fpv_capture_thread('127.0.0.1')
        pass
