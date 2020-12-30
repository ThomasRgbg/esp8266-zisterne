# esp8266-zisterne
Tank level control with an ESP8266 and the TF Luna LIDAR module

An other partly failed hobby project. :)

This is based on the Olimex  ESP8266-EVB, but any other ESP8266 board plus some relais might also work. 

I'm using a TF Luna LIDAR module to check the level in a rain water buffer tank. If the level is to high (so the distance to the sensor to small), the relay is switched on to pump the water. Pretty basic, but additionally the level is transmitted via MQTT. Which is then used by InfluxDB+Grafana to draw some charts. However, this is partly failed, because:

* In a tank burried in the dirt in the garden there is pretty bad wifi reception. 
* Normally a ultrasonic sensor is the preferred way of measuring water levels. However I came across the cheap TF Luna, which gives centimeter resolution via I2C. And allows to put all in a relative closed enclosure, so less humidity issues when mounting inside of the tank. 
* However, rain water is mostly transparent, so the Laser of the Lidar passes through the water surface and gives all kind of funny readings. 
* Of course I realized this own when all was mounted. Instead of changing the sensor and further crawling in and out of the tank, I got many balls from a childrens ball pool, which now swim in the tank an give some better surface to measure. 

So as usual, all just for educational purposes. 
