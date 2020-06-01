#!/usr/bin/env python3
# File name   : servo.py
# Description : Control Motor
# Product     : RaspRover
# Website     : www.adeept.com
# E-mail      : support@adeept.com
# Author      : William
# Date        : 2019/02/23
from __future__ import division

import logging
import time

import Adafruit_PCA9685

import config

logger = logging.getLogger(__name__)
pca = Adafruit_PCA9685.PCA9685()
pca.set_pwm_freq(50)

'''
Change to reverse servo
'''
SERVO_INVERT = True
LOOK_MAX = 500
LOOK_MIN = 100

position = 300


def ctrl_range(raw, max_genout, min_genout):
    if raw > max_genout:
        raw_output = max_genout
    elif raw < min_genout:
        raw_output = min_genout
    else:
        raw_output = raw
    return int(raw_output)


def camera_ang(direction, ang='no'):
    """
    This function set the camera vertical angle servo. If 'no' is passed as angle it will use an increment
    constant value CAM_ANGLE defined in the config.
    Setting direction abs will set servo position to the ang param.
    :param direction: Camera movement direction. Possible values: lookup, lookdown, home, abs
    :param ang: Number of steps to move servo.
    """
    global position
    logger.debug('Servo received: %s %s', direction, ang)
    if not isinstance(ang, int):
        ang = config.CAM_ANGLE
    if direction == 'lookdown':
        if SERVO_INVERT:
            position += ang
        else:
            position -= ang
    elif direction == 'lookup':
        if SERVO_INVERT:
            position -= ang
        else:
            position += ang
    elif direction == 'home':
        position = 300
    elif direction == 'abs':
        position = ang
    else:
        logger.error('Invalid direction. Valid options (lookup, lookdown, home, abs).')
    position = ctrl_range(position, LOOK_MAX, LOOK_MIN)
    set_pwm(0, position)


def clean_all():
    logger.info('Reset all servos')
    pca.set_all_pwm(0, 0)


def set_pwm(servo, pos):
    logger.debug("Set PWM on servo [%s], position [%s])", servo, pos)
    if config.SERVO_MODULE:
        pca.set_pwm(servo, 0, pos)


if __name__ == '__main__':
    camera_ang('lookup')
    time.sleep(1)
    camera_ang('lookup')
    time.sleep(1)
    camera_ang('lookup')
    time.sleep(1)
    camera_ang('lookup')
    time.sleep(1)
    camera_ang('lookdown')
    time.sleep(1)
    camera_ang('lookdown')
    time.sleep(1)
    camera_ang('home')
    time.sleep(1)
    '''
    camera_ang('home', 0)
    time.sleep(0.4)
    clean_all()
    while 1:
        a=input('press any key')
        print(camera_ang('lookup', 0))
        pass
    '''
