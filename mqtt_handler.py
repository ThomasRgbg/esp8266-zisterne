
import machine
import time

from ubinascii import hexlify
from umqtt.robust import MQTTClient
 
class MQTTHandler:
    def __init__(self, name, server):
        self.mqtt = MQTTClient(hexlify(machine.unique_id()), server)
        self.name = name
        self.actions = {}
        self.publishers = {}
        self.connect()
        self.mqtt.set_callback(self.handle_mqtt_msgs)
        self.publish_all_after_msg = True

    def connect(self):
        print('.connect() Check if MQTT is already connected')
        if self.isconnected():
            self.mqtt.disconnect()
        try:
            print('.connect() Not connected, so lets connect')
            self.mqtt.connect()
        except OSError:
            print(".connect() MQTT could not connect")
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
            print(".isconnected() MQTT not connected - Ping not successfull")
            return False
        except AttributeError:
            print(".isconnected() MQTT not connected - Ping not available")
            return False
        
        return True

    def publish_generic(self, name, value):
        topic = self.name + b'/' + bytes(name, 'ascii')
        print(".publish_generic() Publish: {0} = {1}".format(topic, value))
        self.mqtt.publish(topic, str(value))

    def handle_mqtt_msgs(self, topic, msg):
        print(".handle_mqtt_msgs() Received MQTT message: {0}:{1}".format(topic,msg))
        if topic in self.actions:
            print(".handle_mqtt_msgs() Found registered function {0}".format(self.actions[topic]))
            self.actions[topic](msg)
            if self.publish_all_after_msg:
                self.publish_all()

    def register_action(self, topicname, cbfunction):
        topic = self.name + b'/' + bytes(topicname, 'ascii')
        print(".register_action() Get topic {0} for {1}".format(topic, cbfunction))
        if self.isconnected():
            print('.register_action() MQTT connected, try to register')
            self.mqtt.subscribe(topic)
        self.actions[topic] = cbfunction
        
    def register_publisher(self, topicname, function):
        topic = self.name + b'/' + bytes(topicname, 'ascii')
        print(".register_publisher() Get topic {0} for {1}".format(topic, function))
        self.publishers[topic] = function
        
    def publish_all(self):
        for topic in self.publishers:
            value = self.publishers[topic]()
            print(".publish_all() Publish: {0} = {1}".format(topic, value))
            self.mqtt.publish(topic, str(value))
        
    def resubscribe_all(self):
        for topic in self.actions:
            self.mqtt.subscribe(topic)
