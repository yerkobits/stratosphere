#!/usr/bin/env python
# -*- coding: utf-8 -*-

# sensors.py
# Library for accessing the sensors of our probe
# tbd: super-robust error handling
# i2c docs e.g. from http://www.raspberry-projects.com/pi/programming-in-python/i2c-programming-in-python/using-the-i2c-interface-2

from subprocess import PIPE, Popen

from config import *
from w1thermsensor import W1ThermSensor

def get_temperature_cpu():
    """Returns the temperature of the Raspberry CPU in degree Celsius"""
    # Internal, see https://cae2100.wordpress.com/2012/12/29/reading-cpu-temps-using-python-for-raspberry-pi/
    process = Popen(['vcgencmd', 'measure_temp'], stdout=PIPE)
    output, _error = process.communicate()
    return float(output[output.index('=') + 1:output.rindex("'")])


def get_temperature_DS18B20(sensor_id=''):
    """Returns the temperature of the given DS18B20 sensor in degree Celsius"""
    sensor = W1ThermSensor(W1ThermSensor.THERM_SENSOR_DS18B20, sensor_id)
    return sensor.get_temperature()


def get_temperature_external():
    """Returns the temperature of the external HEL-712-U-0-12-00 sensor in degree Celsius"""
    # see  http://www.mouser.de/ProductDetail/Honeywell/HEL-712-U-0-12-00/?qs=%2Ffq2y7sSKcIJdgTbHPcmcA%3D%3D
    # calibrate & convert
    raw_temp = get_adc(SENSOR_ADC_CHANNEL_EXTERNAL_TEMPERATURE, gain=TBD)
    offset = 0.0
    coefficient = 1.0
    exponent = 1.0
    external_temperature = offset + coefficient * raw_temp ** exponent
    return external_temperature


def get_pressure():
    """Returns the pressure from the AP40N-200KG-Stick pressure sensor"""
    # see http://shop.pewatron.com/search/ap40r-200kg-stick-drucksensor.
    # for BMP180, see
    # https://github.com/adafruit/Adafruit_Python_BMP
    # and
    # http://www.cs.unca.edu/~brock/classes/Spring2014/csci320/labs/csci320/bmp180json.py
    # and
    # http://www.raspberrypi-spy.co.uk/2015/04/bmp180-i2c-digital-barometric-pressure-sensor/
    # I2C Slave Address 0x28 (not certain)
    # SENSOR_ID_PRESSURE
    return 0.0

def get_motion_sensor_status():
    '''Tests motions sensor'''
    '''Return 0 for False and 1 for True and a short string with orientation etc.'''
    # enable
    # read
    # reasonable
    return 0, "Readings as Text, including Compass"

def get_motion_data():
    """Returns all data from the 9 degrees of freedom sensor LSM9DS1"""
    # tbd: Poll rate, format of returned data
    # I2C (or SPI)
    # likely a separate thread with a high polling rate (but mind i2c collisions; maybe use second I2C interface just for this sensor)
    # see https://www.sparkfun.com/products/13284
    # https://cdn.sparkfun.com/assets/learn_tutorials/3/7/3/LSM9DS1_Datasheet.pdf
    # SENSOR_ID_MOTION
    return {}

def get_humidity():
    """Returns data from the HTU21D humidity sensors inside and outside the probe
    in percent (1 = 100 %, 0.1 = 10 %)"""
    # see http://www.exp-tech.de/sparkfun-feuchtesensor-breakout-htu21d
    # I2C
    # library in case we use Si7006-A20 Temperature and Humidity sensor instead:
    #     https://github.com/automote/Si7006
    # mind temperature compensation, heating, etc.
    # see also https://github.com/dalexgray/RaspberryPI_HTU21DF
    # SENSOR_ID_HUMIDITY
    return 0.0, 0.0

def get_adc(channel, gain=0):
    """Returns voltage at ADC, utility method for other methods"""
    # Analog via ADS1115 in the form of a https://www.adafruit.com/product/1085
    # datasheet at http://adafruit.com/datasheets/ads1115.pdf
    # Library at https://github.com/adafruit/Adafruit-Raspberry-Pi-Python-Code
    # see also https://learn.adafruit.com/raspberry-pi-analog-to-digital-converters
    # and https://learn.adafruit.com/raspberry-pi-analog-to-digital-converters/ads1015-slash-ads1115
    # SENSOR_ID_ADC
    return 0.0

def get_battery_status():
    """Returns  battery status information, like
    - Voltage in V
    - Current consumption (before DC-DC converters) in A
    - Battery temperature (DS18B20)"""
    # Voltage via simple voltage divider and MCP3204 ADC or directly via ADS1115 in the form of a https://www.adafruit.com/product/1085
    # Current via ACS712/714 + OpAmp + MCP3204 ADC or directly via ADS1115 in the form of a https://www.adafruit.com/product/1085
    # TBD calibration, see also https://cdn-learn.adafruit.com/downloads/pdf/calibrating-sensors.pdf
    raw_voltage = get_adc(SENSOR_ADC_CHANNEL_BATTERY_VOLTAGE, gain=0)
    # Simple Exponential Regression model for calibration
    voltage_offset = 0.0
    voltage_coefficient = 1.0
    voltage_exponent = 1.0
    battery_voltage = voltage_offset + voltage_coefficient * raw_voltage ** voltage_exponent

    raw_current = get_adc(SENSOR_ADC_CHANNEL_CURRENT, gain= TBD)
    current_offset = 0.0
    current_coefficient = 1.0
    current_exponent = 1.0
    discharge_current = current_offset + current_coefficient * raw_current ** current_exponent

    battery_temperature = get_temperature_DS18B20(sensor_id=SENSOR_ID_BATTERY_TEMP)

    return (battery_voltage, discharge_current, battery_temperature)