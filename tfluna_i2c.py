import time
 
class Luna:
    def __init__(self, i2c):
        self.i2c = i2c
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
