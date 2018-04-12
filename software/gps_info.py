#!/usr/bin/env python
# -*- coding: utf-8 -*-
# gps_info.py
# Taken from Alex Stolz' camera module code
# $ sudo pip install pynmea2
# https://blog.retep.org/2012/06/18/getting-gps-to-work-on-a-raspberry-pi/
# $ sudo lsusb
# $ tail -n 200 /var/log/syslog | grep USB | grep tty
# $ sudo apt-get install gpsd gpsd-clients python-gps
# $ sudo gpsd /dev/ttyACM0 -F /var/run/gpsd.sock
# $ cgps -s
# $ sudo apt-get install ntp # to set clock using gps
# $ gps ntp
# $ sudo service ntp restart
# $ ntpq -p

import logging
import os
import time
import serial
import pynmea2
from serial.tools import list_ports
from shared_memory import *
import config
import utility

device = None
baudrate = None

def set_to_flight_mode(uart, baudrate):
    """Sets the Neo 6M GPS module to flight mode for high altitude
    operation.Based on the work described in
    https://ukhas.org.uk/guides:ublox6.

    Args:
        uart (str): The path of the GPS UART.

        baudrate (int): The GPS baudrate (4800 or 9600)."""
    logging.debug('Sending flight mode commands to GPS at %s \
                with baud rate %d.' % (uart, baudrate))
    # Command sequence taken from https://ukhas.org.uk/guides:ublox6
    flight_command = [
        0xB5, 0x62, 0x06, 0x24, 0x24, 0x00, 0xFF, 0xFF,
        0x06, 0x03, 0x00, 0x00, 0x00, 0x00, 0x10, 0x27, 0x00, 0x00,
        0x05, 0x00, 0xFA, 0x00, 0xFA, 0x00, 0x64, 0x00, 0x2C, 0x01,
        0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
        0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x16, 0xDC]
    expected_response = [
        0xB5,  # header
        0x62,  # header
        0x05,  # class
        0x01,  # id
        0x02,  # length
        0x00,  #
        flight_command[2],  # ACK class
        flight_command[3]   # ACK id
    ]
    # Checksum must be appended because lists are immutable
    chk_a = 0
    chk_b = 0
    for i in range(2, 8):
        chk_a += expected_response[i]  # CK_A
        chk_b += chk_a  # CK_B
    expected_response.append(chk_a)
    expected_response.append(chk_b)
    with serial.Serial(uart, baudrate, timeout=3) as ser:
        for byte in flight_command:
            ser.write(chr(byte))
            logging.debug('GPS Command %02x HEX to %s.' % (byte, uart))
        ack = ser.read(10)  # read up to ten bytes
    ack = [ord(c) for c in ack]
    status = cmp(ack, expected_response)
    if status:
        logging.info('SUCCESS: GPS set to flight mode')
    else:
        logging.error('ERROR: Setting GPS to flight mode failed.')
    return status


def get_info(uart, baudrate):
    """Tries to fetch and parse a new $GPRMC or $GPGGA from the GPS.

    Args:
        uart (str): The path of the GPS UART.

        baudrate (int): The GPS baudrate (4800 or 9600).

    Returns:
        msg: a pynmea2 message object

        date: a pynmea2 date object
    """
    with serial.Serial(uart, baudrate, timeout=1) as ser:
        date = None
        while True:
            line = ser.readline()
            logging.debug('NMEA: %s' % line.strip())
            # gps_logger(line.rstrip())
            if line.startswith("$GPRMC"):
                msg = pynmea2.parse(line)
                date = msg.datestamp
            elif line.startswith("$GPGGA"):
                msg = pynmea2.parse(line)
                logging.debug('GPS data: time=%s lat=%s long=%s alt=%s'
                              % (msg.timestamp, msg.lat, msg.lon,
                                 msg.altitude))
                return msg, date


def update_gps_info(timestamp, altitude, latitude, longitude):
    """This function continuously updates the shared memory variables
    for GPS data and is meant to run as a child process.

    It stops once the shared memory variable continue_gps gets False.

    Args:
        timestamp, altitude, latitude, longitude - shared memory variables
    """
    while continue_gps.value:
        gps_data, datestamp = get_info(config.GPS_SERIAL_PORT,
                                       config.GPS_SERIAL_PORT_BAUDRATE)
        try:
            if datestamp is not None:
                timestamp.value = datestamp.strftime("%Y-%m-%dT") \
                    + str(gps_data.timestamp) + "Z"
            else:
                timestamp.value = str(gps_data.timestamp)
            try:
                # os.system("sudo date --set '%s' > /dev/null 2>&1" %
                os.system("sudo date --set '%s' > /dev/null" %
                          timestamp.value)
                logging.debug('System time updated from GPS.')
            except Exception as msg_time:
                logging.error('Could not set the system time.')
                logging.exception(msg_time)
        except Exception as msg:
            timestamp.value = "01-01-1970T00:00:00Z"
            logging.exception(msg)
        try:
            altitude.value = gps_data.altitude
            altitude_outdated.value = 0
        except Exception as msg:
            altitude_outdated.value = 1
            logging.exception(msg)
        try:
            latitude.value = float(gps_data.lat) / 100
            latitude_outdated.value = 0
        except Exception as msg:
            latitude_outdated.value = 1
            logging.exception(msg)
        try:
            longitude.value = float(gps_data.lon) / 100
            longitude_outdated.value = 0
        except Exception as msg:
            longitude_outdated.value = 1
            logging.exception(msg)
        time.sleep(config.GPS_POLLTIME)
    return


if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG)
    utility.check_and_initialize_USB()
    gps_handler = logging.FileHandler(config.USB_DIR + 'gps.csv')
    # gps_handler.setFormatter(formatter)
    gps_logger = logging.getLogger('gps')
    gps_logger.setLevel(logging.DEBUG)
    gps_logger.addHandler(gps_handler)
    uart = config.GPS_SERIAL_PORT
    baudrate = config.GPS_SERIAL_PORT_BAUDRATE
    logging.info('GPS found at %s with %i baud' % (uart, baudrate))
    logging.info('Trying to read current position.')
    msg, date = get_info(uart, baudrate)
    logging.info('Trying to set GPS to flight mode.')
    set_to_flight_mode(uart, baudrate)
    # Initialize GPS subprocess or thread
    p = mp.Process(target=update_gps_info,
                   args=(timestamp, altitude, latitude, longitude))
    p.start()
    # Wait for valid GPS position and time, and sync time
    logging.info('Waiting for valid initial GPS position.')
    while longitude_outdated.value > 0 or latitude_outdated.value > 0:
        time.sleep(1)
    logging.info('Now reading GPS info from shared memory.')
    for i in range(10):
        logging.info('GPS: lat=%f %s, long=%f %s, alt=%fm, timestamp: %s' %
                     (latitude.value, latitude_direction.value,
                      longitude.value, longitude_direction.value,
                      altitude.value, timestamp.value))
        time.sleep(1)
    continue_gps.value = 0
    time.sleep(1)
    p.terminate()
    p.join()
    logging.info('Goodbye.')

