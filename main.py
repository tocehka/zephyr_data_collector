import pygatt
from binascii import hexlify
import csv
from time import time, strftime, gmtime
from functools import partial
import sys
import os
import numpy as np

HEART_UUID = "00002a37-0000-1000-8000-00805f9b34fb"

adapter = pygatt.GATTToolBackend()

class WriterManager:
    def __init__(self, file_name, header=False):
        self.__file = open(file_name, 'w')
        if not header:
            self.__writer = csv.writer(self.__file)
        else:
            self.__writer = csv.DictWriter(self.__file, fieldnames=header)
            self.__writer.writeheader()    
    def write_row(self, row):
        self.__writer.writerow(row)
    def flush(self):
        self.__file.flush()
    def __del__(self):
        self.__file.close()
        
writer_class = WriterManager("stress_data_add.csv")
start_time = 0
first_time = True

def handle_data(handle, value, writer=None):
    try:
        if value == None:
            raise ValueError
        flags = value.pop(0)
        hr_format = (flags >> 0) & 1
        contact_status = (flags >> 1) & 3
        expended_present = (flags >> 3) & 1
        rr_present = (flags >> 4) & 1
        meas = {'hr': value.pop(0)}
        if hr_format:
            meas['hr'] += 256 * value.pop(0)
        if contact_status & 2:
            meas['sensor_contact'] = bool(contact_status & 1)
        if expended_present:
            e = value.pop(0)
            e += 256 * value.pop(0)
            meas['energy_expended'] = e
            meas['rr'] = []
        if rr_present:
            rr = []
        while len(value) > 0:
            rr_val = value.pop(0)
            rr_val += 256 * value.pop(0)
            rr_val /= 1000.
            rr.append(rr_val)
            meas['rr'] = rr
        meas_data = {}
        global first_time
        global start_time
        if first_time:
            start_time = time()
            first_time = False
        print(f"Recieved at {time() - start_time}")
        if "rr" in meas:
            meas_data = {"hr": meas["hr"], "rr": np.mean(meas["rr"]), "stress": 0,\
                            "time": strftime("%H:%M:%S", gmtime(time() - start_time)),\
                            "real_time": strftime("%H:%M:%S")}
        else:
            meas_data = {"hr": meas["hr"], "rr": 0, "stress": 0,\
                            "time": strftime("%H:%M:%S", gmtime(time() - start_time)),\
                            "real_time": strftime("%H:%M:%S")}
        writer.write_row(list(meas_data.values()))
        print(meas_data)
        
    except ValueError:
        print("/nNothing to return/n")

def main(handle_data):
    writer_class.write_row(['hr', 'rr', 'stress', 'time', 'real_time'])
    while True:
        try:
            print("Trying to connect to Zephyr")
            adapter.start()
            device = adapter.connect('F4:5E:AB:09:CA:70', timeout=10, auto_reconnect=True)
            #print(device.discover_characteristics())
            handle_data = partial(handle_data, writer=writer_class)
            while True:
                device.subscribe(HEART_UUID,
                            callback=handle_data)
        except Exception as e:
            print(e)
            adapter.stop()
            continue

if __name__ == "__main__":
    try:
        main(handle_data)
    except KeyboardInterrupt:
        print('Interrupted')
        writer_class.flush()
        del writer_class
        try:
            sys.exit(0)
        except SystemExit:
            os._exit(0)