import struct
import serial
import math
import time

# 设置串口参数
ser = serial.Serial('COM1', 115200, timeout=1)

# 帧尾数据
frame_end = b'\x00\x00\x80\x7F'

# 生成 sin(0.5t) 的值,t单位为秒
t = 0
while True:
    # 生成一个数据点
    data = math.sin(0.5 * t)

    # 将浮点数转换为 IEEE 754 单精度浮点数格式,并转换为小端格式的十六进制字节
    hex_data = struct.pack('<f', data)

    # 发送数据8次
    for _ in range(8):
        ser.write(hex_data)

    # 发送帧尾
    ser.write(frame_end)

    # 更新时间
    t += 1/400

    # 等待 0.0025 秒(1/400秒)
    time.sleep(0.0025)
