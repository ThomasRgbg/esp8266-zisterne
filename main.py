from machine import Pin, I2C, reset, RTC, unique_id, Timer
import time
import ntptime

import uasyncio
import gc
import micropython

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
        
class Watchdog:
    def __init__(self, interval):
        self.timer = Timer(0)
        self.timer.init(period=(interval*1000), mode=Timer.PERIODIC, callback=self.wdtcheck)
        self.feeded = True
        
    def wdtcheck(self, timer):
        if self.feeded:
            print("Watchdog feeded, all fine")
            self.feeded = False
        else:
            print("Watchdog hungry, lets do a reset in 5 sec")
            time.sleep(5)
            reset()
            
    def feed(self):
        self.feeded = True
        print("Feed Watchdog")

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
upperthresh_default = 80.0 #was 80
upperthresh = upperthresh_default

# Pump off:
lowerthresh_default = 87.0 #was 87
lowerthresh = lowerthresh_default

def set_thres_offeset(value):
    global lowerthresh
    global upperthresh
    lowerthresh = lowerthresh_default + int(value)
    upperthresh = upperthresh_default + int(value)
    print("new lowerthresh {0}".format(lowerthresh))
    print("new upperthresh {0}".format(upperthresh))
    
# Zero level (Minimum the pump can take)
zero_level = 240.0 

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
sc.register_action('waterlevel_offset', set_thres_offeset)

rtc = RTC()
wdt = Watchdog(interval = 120)
wdt.feed()

# logfile = open('logfile.txt', 'w')

wdt.feed()
count = 1
errcount = 0

#####
# Task definition
#####


async def housekeeping():
    global errcount
    count = 1

    lasttimestamp = rtc.datetime()
    while True:
        print("housekeeping()")
        timestamp = rtc.datetime()
        print("Timestamp: {0}".format(timestamp))
        print("Count: {0}".format(count))
        print("Error counter: {0}".format(errcount))
        
        wdt.feed()

        # Too many errors, e.g. could not connect to MQTT
        if errcount > 100:
            time.sleep(5)
            reset()

        if not wlan.isconnected():
            print("WLAN not connected")
            errcount += 25
            time.sleep(5)
            continue
        
        if (count % 10 == 0):
            updatetime(False)

        if (count % 600 == 0):
            updatetime(True)

        gc.collect()
        micropython.mem_info()

        count += 1
        await uasyncio.sleep_ms(60000)

async def handle_mqtt():
    global errcount
    while True:
        # Generic MQTT
        if sc.isconnected():
            print("handle_mqtt() - connected")
            for i in range(59):
                sc.mqtt.check_msg()
                await uasyncio.sleep_ms(1000)
            sc.publish_all()
        else:
            print("MQTT not connected - try to reconnect")
            sc.connect()
            errcount += 1
            await uasyncio.sleep_ms(19000)

        await uasyncio.sleep_ms(1000)

async def handle_lidar():
    global errcount
    count = 1
    while True:
        print("handle_lidar()")
        dist, min_dist, max_dist = lidar.read_avg_dist()
        waterlevel = zero_level - dist
        waterlevel_target = zero_level - upperthresh
        waterlevel_min = zero_level - max_dist
        waterlevel_max = zero_level - min_dist
        amp = lidar.read_amp()
        errorv = lidar.read_error()
        temp = lidar.read_temp()
        timestamp = rtc.datetime()
        print("Distance: {0}".format(dist))
        print("Min Distance: {0}".format(min_dist))
        print("Max Distance: {0}".format(max_dist))
        print("Level: {0}".format(waterlevel))
        print("Min Level: {0}".format(waterlevel_min))
        print("Max Level: {0}".format(waterlevel_max))
        print("Target Level: {0}".format(waterlevel_target))
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
#        if (logfile and (count % 10 == 0)) or (pumpe.state == 1):
#            updatetime(False)
#            print("Write logfile")
#            logfile.write("{0}, ({1}),({2})\n".format(timestamp, dist,pumpe.state))
#            logfile.flush()
        
        # After some hours, reallign things
        if (count % 100 == 0):
            # After some days, the TF Luna gets stuck with just one value
            print("periodic reset of Lidar")
            lidar.reset_sensor()
 
        if sc.isconnected():
            print("send to MQTT server")
            sc.mqtt.check_msg()
            sc.publish_generic('distance', dist)
            sc.publish_generic('min_distance', min_dist)
            sc.publish_generic('max_distance', max_dist)
            sc.publish_generic('waterlevel', waterlevel)
            sc.publish_generic('waterlevel_min', waterlevel_min)
            sc.publish_generic('waterlevel_max', waterlevel_max)
            sc.publish_generic('waterlevel_target', waterlevel_target)
            sc.publish_generic('pump', pumpe.state)

        # Get more data to MQTT to see whats ongoing if the pump is running
        if (pumpe.state == 1):
            await uasyncio.sleep_ms(2*1000)

        # Close to pump enable point, be carefull
        elif dist < lowerthresh:
            await uasyncio.sleep_ms(20*1000)
        # All good, lets take it slow. 
        else:
            await uasyncio.sleep_ms(100*1000)

        count += 1
        


####
# Main
####

updatetime(True)

main_loop = uasyncio.get_event_loop()

main_loop.create_task(housekeeping())
main_loop.create_task(handle_mqtt())
main_loop.create_task(handle_lidar())

main_loop.run_forever()
main_loop.close()


#mainloop()
