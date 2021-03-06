#!/usr/bin/env python3

import time

# Gas
from enviroplus import gas

# Climate
from bme280 import BME280
try:
    from smbus2 import SMBus
except ImportError:
    from smbus import SMBus

# Light
try:
    # Transitional fix for breaking change in LTR559
    from ltr559 import LTR559
    ltr559 = LTR559()
except ImportError:
    import ltr559

# Particulates
from pms5003 import PMS5003, ReadTimeoutError

# LCD
import ST7735
from PIL import Image, ImageDraw, ImageFont
from fonts.ttf import RobotoMedium as UserFont


class State:
    temperature = 0
    pressure = 0
    humidity = 0
    lux = 0
    prox = 0
    oxidising = 0
    nh3 = 0
    reducing = 0

    def parse(self, data):
        return round(data, 2)

    def toFahrenheit(self, celsius):
        return (celsius * 9/5) + 32

    def get_all_data(self):
        return {
            "temperature": {
                "data": self.parse(self.toFahrenheit(self.temperature)),
                "unit": "F"
            },
            "pressure": {
                "data": self.parse(self.pressure),
                "unit": "hPa"
            },
            "humidity": {
                "data": self.parse(self.humidity),
                "unit": "%"
            },
            "lux": {
                "data": self.parse(self.lux),
                "unit": "Lux"
            },
            "prox": {
                "data": self.parse(self.prox),
                "unit": "prox"
            },
            "oxidising": {
                "data": self.parse(self.oxidising),
                "unit": "kO"
            },
            "nh3": {
                "data": self.parse(self.nh3),
                "unit": "KO"
            },
            "reducing": {
                "data": self.parse(self.reducing),
                "unit": "KO"
            }
        }


class LCD:
    def __init__(self):
        self.lcd_init()
        self.set_frame()
        self.draw_canvas()
        self.text_settings()

    def get_state(self):
        return self.state

    def set_state(self, state):
        self.state = state

    def set_frame(self):
        self.WIDTH = self.disp.width
        self.HEIGHT = self.disp.height

    def draw_canvas(self):
        # New canvas to draw on.
        self.img = Image.new('RGB', (self.WIDTH, self.HEIGHT), color=(0, 0, 0))
        self.draw = ImageDraw.Draw(self.img)

    def text_settings(self):
        # Text settings.
        self.font_size = 21
        self.font = ImageFont.truetype(UserFont, self.font_size)
        self.text_colour = (255, 255, 255)
        self.back_colour = (0, 170, 170)

    def contnent(self, message):
        self.message = message
        self.size_x, self.size_y = self.draw.textsize(self.message, self.font)

    def text_position(self):
        self.x = (self.WIDTH - self.size_x) / 2
        self.y = (self.HEIGHT / 2) - (self.size_y / 2)

    def draw_display(self):
        self.draw.rectangle((0, 0, 160, 80), self.back_colour)
        self.draw.text((self.x, self.y), self.message,
                       font=self.font, fill=self.text_colour)
        self.disp.display(self.img)

    def lcd_init(self):
        self.disp = ST7735.ST7735(
            port=0,
            cs=1,
            dc=9,
            backlight=12,
            rotation=270,
            spi_speed_hz=10000000
        )

        # Initialize display.
        self.disp.begin()

    def stop(self):
        self.set_state(False)
        self.disp.set_backlight(0)

    def run(self):
        self.set_state(True)
        self.contnent('')
        self.text_position()
        self.draw_display()
        self.state


class Sensor(State):
    def __init__(self):
        bus = SMBus(1)
        self.bme280 = BME280(i2c_dev=bus)
        self.pms5003 = PMS5003()
        time.sleep(1)

    def start(self, callback):
        while True:
            # Climate
            self.temperature = self.bme280.get_temperature()
            self.pressure = self.bme280.get_pressure()
            self.humidity = self.bme280.get_humidity()
            time.sleep(1)

            # Light
            self.lux = ltr559.get_lux()
            self.prox = ltr559.get_proximity()
            time.sleep(1)

            # Gas
            gases = gas.read_all()
            self.oxidising = (gases.oxidising / 1000)
            self.nh3 = (gases.nh3 / 1000)
            self.reducing = (gases.reducing / 1000)
            time.sleep(1)

            # Callback all data in json format
            callback(self.get_all_data())
            time.sleep(1)


class Enviro:
    def __init__(self, callback):
        # Initialize sensor
        self.sensor = Sensor()
        # Initialize LCD
        self.lcd = LCD()
        # Sensor output callback method
        self.callback = callback

    def display_data(self, data):
        temp = data['temperature']
        hum = data['humidity']
        temp_data = "{temp} {unit}".format(temp=temp, unit=temp['unit'])
        humi_data = "{hum} {unit}".format(hum=hum, unit=hum['unit'])
        self.show_data = temp_data + '\n' + humi_data

        if self.lcd.get_state() == True:
            self.lcd.contnent(self.show_data)
            self.lcd.text_position()
            self.lcd.draw_display()

        self.callback(data)

    def start(self):
        self.lcd.run()
        self.sensor.start(self.display_data)
