#serial_reader.py
import time

import eventlet
eventlet.monkey_patch()

import serial
import struct
import threading

class SerialPortReader:
    FRAME_TAIL = b'\x00\x00\x80\x7F'

    def __init__(self, port='COM7', baudrate=921600):
        self.port = port
        self.baudrate = baudrate
        self.serial_conn = None
        self.is_running = False
        self.callbacks = []
        self.buffer = bytearray()

    def open(self):
        try:
            self.serial_conn = serial.Serial(self.port, self.baudrate)
            self.is_running = True
            eventlet.spawn(self.read_data)  # 使用Eventlet的绿线程
            threading.Thread(target=self.read_data, daemon=True).start()
            print(f"Serial port {self.port} opened successfully")
        except Exception as e:
            print(f"Failed to open serial port: {e}")

    def close(self):
        self.is_running = False
        if self.serial_conn and self.serial_conn.is_open:
            self.serial_conn.close()

    def read_data(self):
        while self.is_running:
            data = self.serial_conn.read(self.serial_conn.in_waiting or 1)
            if data:
                #print(f"Read {len(data)} bytes from serial port")
                self.buffer.extend(data)
                self._parse_frames()
                eventlet.sleep(0)  # 让出控制权

    def _parse_frames(self):
        while True:
            tail_index = self.buffer.find(self.FRAME_TAIL)
            if tail_index != -1:
                frame_end = tail_index + len(self.FRAME_TAIL)
                if tail_index > 0:
                    frame_data = self.buffer[:tail_index]
                    try:
                        # 获取当前时间戳
                        current_time = time.time()

                        values = self.parse_frame(frame_data)
                        # 回调函数现在不仅传递解析的值，还传递时间戳
                        for callback in self.callbacks:
                            callback(values, current_time)
                    except Exception as e:
                        print(f"Error parsing frame: {e}")
                self.buffer = self.buffer[frame_end:]
            else:
                break

    def parse_frame(self, data):
        expected_length = 4 * 8
        if len(data) != expected_length:
            raise ValueError(f"Frame length mismatch: expected {expected_length}, got {len(data)}")
        values = []
        for i in range(8):
            bytes_ = data[i*4:(i+1)*4]
            value = struct.unpack('<f', bytes_)[0]
            values.append(value)
        return values

    def register_callback(self, callback):
        self.callbacks.append(callback)
