
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

