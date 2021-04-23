from machine import Pin, I2C, reset, RTC, unique_id
import time
import ntptime

from mqtt_handler import MQTTHandler

from tfluna_i2c import Luna 


class Pumpe:
    def __init__(self):
        self.pin=Pin(5,Pin.OUT)
        self.pin.value(0)

    def on(self):
        print("Set GPIO on")
        self.pin.value(1)

    def off(self):
        print("Set GPIO off")
        self.pin.value(0)

    @property
    def state(self):
        return self.pin.value()

    @state.setter
    def state(self, value):
        print("Setting pump to {0}".format(value))
        if int(value) == 1:
            self.on()
        else:
            self.off()

    def set_state(self, value):
        self.state = int(value)

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

#### 
# Threshold values 
####

# Pump on:
upperthresh = 80.0

# Pump off:
lowerthresh = 95.0 # was 95.0

####
# Main
####

# time to connect WLAN, since marginal reception
time.sleep(5)


pumpe = Pumpe()

i2c = I2C(scl=Pin(4), sda=Pin(2), freq=100000)
lidar = Luna(i2c)

sc = MQTTHandler(b'pentling/zisterne', '192.168.0.13')
sc.register_action('pump_enable', pumpe.set_state)

rtc = RTC()

logfile = open('logfile.txt', 'w')

def mainloop():
    count = 1
    errcount = 0

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
        print("Pumpe: {0}".format(pumpe.state))
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
        if (logfile and (count % 10 == 0)) or (pumpe.state == 1):
            updatetime(False)
            print("Write logfile")
            logfile.write("{0}, ({1}),({2})\n".format(timestamp, dist,pumpe.state))
            logfile.flush()
        
        # After some hours, reallign things
        if (count % 100 == 0):
            # After some days, the TF Luna gets stuck with just one value
            print("periodic reset of Lidar")
            lidar.reset_sensor()
            # Force time sync to avoid to large drift
            updatetime(True) 

        if sc.isconnected():
            print("send to MQTT server")
            sc.mqtt.check_msg()
            sc.publish_generic('distance', dist)
            sc.publish_generic('pump', pumpe.state)
        else:
            print("MQTT not connected - try to reconnect")
            sc.connect()
            errcount += 1
            continue

        # Get more data to MQTT to see whats ongoing if the pump is running
        if (pumpe.state == 1):
            time.sleep(2)
        else:
            time.sleep(110)

        # Too many errors, e.g. could not connect to MQTT
        if errcount > 20:
            reset()

        count += 1

mainloop()
