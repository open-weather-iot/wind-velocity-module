# MÓDULO DE VELOCIDADE DO VENTO
O módulo de velocidade do vento faz parte do projeto de estação meteorológica no âmbito da disciplina de Laboratorio Experimental de Campus Inteligente (IE321K).

O sistema de velocidade de vento usa o chip HMC5883L que contem um sensor magnético de baixo campo, um ADC de 12-bits, e interface de comunicação I2C que facilita a leitura do mesmo. Este chip tem o endereço em decimal: 60 (0x3C).

Este sistema fica dentro de uma placa impressa que facilita a comunicação com qualquer outro microcontrolador que possua comunicação I2C e trabalhe com 3.3V de alimentação.

Nesta caso foi escolhido o microcontrolador Raspberry Pi Pico e o lenguagem MicroPython.

## Diagrama de blocos
O seguinte diagrama apresenta as conexões dos subsistemas eletrónicos do modulo de velocidade do vento.

<img src="img/diagrama_de_blocos_MVV.png">

## Libraria do sensor HMC5883L
Esta libraria deve se guardar no mesmo Raspberry Pi Pico com o nome de hmc5883l.py

```py
# Author: peppe8o
# https://peppe8o.com
#
# G-271 HMC5883L library to use magnetometer with Raspberry PI Pico (MicroPython)
# Ported from gvalkov/micropython-esp8266-hmc5883l code (ESP8266) -> https://github.com/gvalkov/micropython-esp8266-hmc5883l
# X and Y calibration offsets added

import math
import machine
from ustruct import pack
from array import array

class HMC5883L:
    __gain__ = {
        '0.88': (0 << 5, 0.73),
        '1.3':  (1 << 5, 0.92),
        '1.9':  (2 << 5, 1.22),
        '2.5':  (3 << 5, 1.52),
        '4.0':  (4 << 5, 2.27),
        '4.7':  (5 << 5, 2.56),
        '5.6':  (6 << 5, 3.03),
        '8.1':  (7 << 5, 4.35)
    }
    
    # Correction to be set after calibration
    xs=1
    xb=-9.76001
    ys=1.014486
    yb=52.79199
    
    def __init__(self, scl=15, sda=14, address=0x1e, gauss='1.9', declination=(0, 0)):
        self.i2c = i2c = machine.SoftI2C(scl=machine.Pin(scl), sda=machine.Pin(sda), freq=15000)
        # Initialize sensor.
        i2c.start()

        # Configuration register A:
        #   0bx11xxxxx  -> 8 samples averaged per measurement
        #   0bxxx100xx  -> 15 Hz, rate at which data is written to output registers
        #   0bxxxxxx00  -> Normal measurement mode
        i2c.writeto_mem(0x1e, 0x00, pack('B', 0b111000))

        # Configuration register B:
        reg_value, self.gain = self.__gain__[gauss]
        i2c.writeto_mem(0x1e, 0x01, pack('B', reg_value))

        # Set mode register to continuous mode.
        i2c.writeto_mem(0x1e, 0x02, pack('B', 0x00))
        i2c.stop()

        # Convert declination (tuple of degrees and minutes) to radians.
        self.declination = (declination[0] + declination[1] / 60) * math.pi / 180

        # Reserve some memory for the raw xyz measurements.
        self.data = array('B', [0] * 6)

    def read(self):
        data = self.data
        gain = self.gain
        
        self.i2c.readfrom_mem_into(0x1e, 0x03, data)
        
        x = (data[0] << 8) | data[1]
        y = (data[4] << 8) | data[5]
        z = (data[2] << 8) | data[3]
        
        x = x - (1 << 16) if x & (1 << 15) else x
        y = y - (1 << 16) if y & (1 << 15) else y
        z = z - (1 << 16) if z & (1 << 15) else z

        x = x * gain
        y = y * gain
        z = z * gain
        
        # Apply calibration corrections
        x = x * self.xs + self.xb
        y = y * self.ys + self.yb

        return x, y, z

    def heading(self, x, y):
        heading_rad = math.atan2(y, x)
        heading_rad += self.declination

        # Correct reverse heading.
        if heading_rad < 0:
            heading_rad += 2 * math.pi

        # Compensate for wrapping.
        elif heading_rad > 2 * math.pi:
            heading_rad -= 2 * math.pi

        # Convert from radians to degrees.
        heading = heading_rad * 180 / math.pi
        degrees = math.floor(heading)
        minutes = round((heading - degrees) * 60)
        return degrees, minutes

    def format_result(self, x, y, z):         
        degrees, minutes = self.heading(x, y)
        return 'X: {:.4f}, Y: {:.4f}, Z: {:.4f}, Heading: {}° {}′ '.format(x, y, z, degrees, minutes), degrees

```

## Script para medição de velocidade do vento
Script com comentarios explicando o codigo do programa a detalhe

```py

from hmc5883l import HMC5883L
from time import sleep
import time
import math

sensor = HMC5883L()


TO_RAD = math.pi/180
TO_KMH = 3.6
degrees = 0
slp = 0.35 # valor minimo de delay (referencial para uma leitura não muito rapida)
dt = 0
distHaste = 0.29 # distancia da haste em metros

while True:
    temp = degrees
    tA = time.ticks_ms() 	# mide o tempo antes de iniciar a leitura do sensor
    
    # Leitura do sensor
    x, y, z = sensor.read() # le o posição do sensor em relacao ao campo magnetico do sistema
    degrees, minutes = sensor.heading(x, y) # calcula a posição em graus
    dTheta = degrees-temp 	# calcula a diferencia de posição
    
    # Tolerancia de giro em contra
    if dTheta < -90:
           dTheta = (degrees+360)-temp
    
    # Calculo de velocidade do giro em km/h
    w = (dTheta)*dt 		# calculo da velocidade angular
    cosTheta = math.cos(dTheta * TO_RAD)
    windSpeedMS = w*abs(cosTheta)*distHaste 		# conversão de velocidade angular a lineal 
    windSpeedKMH = int(windSpeedMS*TO_KMH*10)/10 	# conversão de ms/s a km/h, e trabalhando com um decimal de precisão

    print(windSpeedKMH)

    tZ = time.ticks_ms() # mide o tempo ao final de tudo o codigo
    dt = (tZ - tA)/1000  # encontra tempo de execucao
    #print(dt)
    
    # Minimo valor de leitura (referencial)
    if dt < slp:
        sleep(slp)
        tZ = time.ticks_ms() # mide o tempo ao final de tudo o codigo
        dt = (tZ - tA)/1000
        #print(dt)



```
