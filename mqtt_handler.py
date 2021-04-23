
import machine
import time

from ubinascii import hexlify
from umqtt.robust import MQTTClient
 
class MQTTHandler:
    def __init__(self, name, server):
        self.mqtt = MQTTClient(hexlify(machine.unique_id()), server)
        self.name = name
        self.actions = {}
        self.connect()
        self.mqtt.set_callback(self.handle_mqtt_msgs)

    def connect(self):
        if self.isconnected():
            self.mqtt.disconnect()
        try:
            self.mqtt.connect()
        except OSError:
            print("MQTT could not connect")
            return False
                
        time.sleep(3)
        if self.isconnected():
            self.resubscribe_all()
            return True
        else:
            # Some delay to avoid system getting blocked in a endless loop in case of 
            # connection problems, unstable wifi etc.
            time.sleep(5)
            return False
        
    def isconnected(self):
        try:
            self.mqtt.ping()
        except OSError:
            print("MQTT not connected - Ping not successfull")
            return False
        except AttributeError:
            print("MQTT not connected - Ping not available")
            return False
        
        return True

    def publish_generic(self, name, value):
        print("Publish {0} = {1}".format(name, value))
        self.mqtt.publish(self.name + b'/' + bytes(name, 'ascii'), str(value))

    def handle_mqtt_msgs(self, topic, msg):
        print("Received MQTT message: {0}:{1}".format(topic,msg))
        if topic in self.actions:
            print("Found registered function {0}".format(self.actions[topic]))
            self.actions[topic](msg)

    def register_action(self, topicname, cbfunction):
        topic = self.name + b'/' + bytes(topicname, 'ascii')
        print("Register topic {0} for {1}".format(topic, cbfunction))
        if self.isconnected():
            print('register_action: MQTT not connected, only store locally for .resubscribe_all()')
            self.mqtt.subscribe(topic)
        self.actions[topic] = cbfunction
        
    def resubscribe_all(self):
        for topic in self.actions:
            self.mqtt.subscribe(topic)
