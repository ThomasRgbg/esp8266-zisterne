from machine import Pin, I2C, reset, RTC
import time
import ntptime

from umqtt.robust import MQTTClient
 

class Luna:
    def __init__(self):
        # Hardcoded values, since simple device
        self.i2c = I2C(scl=Pin(4), sda=Pin(2), freq=100000)
        self.addr = 0x10
        self.reset_sensor()

    def sensor_present(self):
        if self.i2c.readfrom_mem(self.addr, 0x0a, 1) == b'\x08':
            return True
        else:
            return False

    def read_distance(self):
        val = self.i2c.readfrom_mem(self.addr, 0x00, 2)
        return(int.from_bytes(val, 'little'))

    def read_avg_dist(self):
        dist = 0
        for i in range(40):
            val = self.read_distance()
            # print(val)
            dist += val
            time.sleep(0.25)
        dist = dist / 40
        return dist

    def read_amp(self):
        val = self.i2c.readfrom_mem(self.addr, 0x02, 2)
        return(int.from_bytes(val, 'little'))

    def read_error(self):
        val = self.i2c.readfrom_mem(self.addr, 0x08, 2)
        return(int.from_bytes(val, 'little'))

    def read_temp(self):
        val = self.i2c.readfrom_mem(self.addr, 0x04, 2)
        return(int.from_bytes(val, 'little'))

    #def enable_sensor():
    #    self.i2c.writeto_mem(self.addr, 0x28, b'\x00')

    def reset_sensor(self):
        self.i2c.writeto_mem(self.addr, 0x21, b'\x02')
        time.sleep(5)
        self.i2c.writeto_mem(self.addr, 0x26, b'\x02')

    def print_loop(self):
        while True:
            print("----")
            print(self.read_distance())
            print(self.read_amp())
            print(self.read_temp())
            time.sleep(2)

class Pumpe:
    def __init__(self):
        self.pin=Pin(5,Pin.OUT)
        self.pin.value(0)

    def on(self):
        self.pin.value(1)

    def off(self):
        self.pin.value(0)

    def state(self):
        return self.pin.value()

class SensorClient:
    def __init__(self, sensor, client_id, server):
        self.sensor = sensor
        self.client = MQTTClient(client_id, server)
        self.name = 'myhome'
        self.client.connect()

    def publish_distance(self, dist):
        # dist = self.sensor.read_avg_dist()
        self.client.publish(self.name + '/zisterne/distance', str(dist))

    def publish_pump(self, state):
        # dist = self.sensor.read_avg_dist()
        self.client.publish(self.name + '/zisterne/pump', str(state))


def updatetime(force):
    if (rtc.datetime()[0] < 2020) or (force is True):
        if wlan.isconnected():
            print("try to set RTC")
            try:
                ntptime.settime()
            except:  
                print("Some error around time setting, likely timeout")
    else:
        print("RTC time looks already reasonable: {0}".format(rtc.datetime()))

def connect_mqtt():
    print("try to connect to MQTT server")
    try:  
        sc_try = SensorClient(lidar, '53242d8c-2ffa-4a92-b684-3da73483cd47', '192.168.0.13')
    except:
        sc_try = None
    
    return sc_try


#### 
# Threshold values 
####

# Pump on:
upperthresh = 80.0

# Pump off:
lowerthresh = 95.0

####
# Main
####

# time to connect WLAN, since marginal reception
time.sleep(5)

pumpe = Pumpe()
lidar = Luna()
rtc = RTC()
logfile = open('logfile.txt', 'w')


def mainloop():
    count=1
    sc = connect_mqtt()
    while True:
        dist = lidar.read_avg_dist()
        amp = lidar.read_amp()
        errorv = lidar.read_error()
        temp = lidar.read_temp()
        timestamp = rtc.datetime()
        print("Distance: {0}".format(dist))
        print("Amplification Value: {0}".format(amp))
        print("Error Value: {0}".format(errorv))
        print("Temperature: {0}".format(temp))
        print("Timestamp: {0}".format(timestamp))
        print("Pumpe: {0}".format(pumpe.state()))
        print("Count: {0}".format(count))

        if dist > lowerthresh:
            print("Dist: {0} > lowerthresh {1} -> Pumpe off".format(dist,lowerthresh))
            pumpe.off()

        elif dist < upperthresh:
            print("Dist: {0} < upperthresh {1} -> Pumpe on".format(dist,upperthresh))
            pumpe.on()

        else: 
            print("lowerthresh {0} < Dist: {1} < upperthresh {2} -> don't change anything".format(lowerthresh,dist,upperthresh))

        # On device logging for debugging
        if (logfile and (count % 10 == 1)) or (pumpe.state() == 1):
            updatetime(False)
            print("Write logfile")
            logfile.write("{0}, ({1}),({2})\n".format(timestamp, dist,pumpe.state()))
            logfile.flush()

        # After some days, the TF Luna gets stuck with just one value
        if (count % 100 == 1):
            print("periodic reset of Lidar")
            lidar.reset_sensor()
            updatetime(True) 

        if sc is not None:
            print("send to MQTT server")
            sc.publish_distance(dist)
            sc.publish_pump(pumpe.state())
        else:
            print("MQTT not connected")
            sc = connect_mqtt()

        # Get more data to MQTT to see whats ongoing if the pump is running
        if (pumpe.state() == 1):
            time.sleep(10)
        else:
            time.sleep(110) 

        count += 1

mainloop()
