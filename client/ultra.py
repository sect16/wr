# E-mail      : sect16@gmail.com
# Author      : Chin Pin Hon
# Date        : 14.01.2020

"""
This function contains the ultrasonic data tcp server thread..
"""

import logging
import traceback
import coloredlogs
from socket import *
import config
import gui
import functions

# Create a logger object.
logger = logging.getLogger(__name__)
coloredlogs.install(level='DEBUG',
                    fmt='%(asctime)s.%(msecs)03d %(levelname)7s %(thread)5d --- [%(threadName)16s] %(funcName)-39s: %(message)s')


def ultra_server_thread(event):
    """
    Creates a TCP server and listen on port.
    :param event: Event flag to signal termination.
    """
    logger.debug('Thread started')
    ultra_addr = ('', config.ULTRA_PORT)
    ultra_sock = socket(AF_INET, SOCK_STREAM)
    ultra_sock.setsockopt(SOL_SOCKET, SO_REUSEADDR, 1)
    ultra_sock.bind(ultra_addr)
    ultra_sock.listen(5)  # Start server, waiting for client
    gui.ultrasonic_mode = 1
    ultra_sock, addr = ultra_sock.accept()
    logger.info('Ultrasonic port connected')
    while event.is_set():
        try:
            config.ultra_data = str(ultra_sock.recv(config.BUFFER_SIZE).decode())
            config.ultra_data = float(config.ultra_data)
            if float(config.ultra_data) < 3:
                logger.debug('Ultrasonic data received (%s)', config.ultra_data)
                gui.canvas_ultra.create_rectangle(0, 0, (352 - int(float(config.ultra_data) * 352 / 3)), 30,
                                                  fill='#448AFF', width=0)
                gui.canvas_ultra.create_text((90, 11), text='Ultrasonic Output: %sm' % config.ultra_data,
                                             fill=config.COLOR_TEXT)
        except:
            logger.error('Ultrasonic exception: %s', traceback.format_exc())
            functions.ultra_event.clear()
            pass
    gui.canvas_ultra.create_rectangle(0, 0, 352, 30, fill='#FFFFFF', width=0)
    gui.canvas_ultra.create_text((90, 11), text='Ultrasonic OFF', fill='#000000')
    gui.ultrasonic_mode = 0
    logger.debug('Thread stopped')
