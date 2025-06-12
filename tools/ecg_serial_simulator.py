import serial
import struct
import time
import math
import random

# --- 配置参数 ---
VIRTUAL_SERIAL_PORT = '/tmp/ttyV0'  # 修改为您的虚拟串口名称 (发送端)
BAUD_RATE = 115200  # 波特率 (对于虚拟串口可能不那么重要，但保持一致)
SAMPLING_RATE_HZ = 250  # 模拟采样率 (Hz)
SEND_INTERVAL_S = 1.0 / SAMPLING_RATE_HZ # 发送间隔 (秒)
NUM_CHANNELS = 8 # 发送8个原始导联数据
FRAME_TAIL = b'\x00\x00\x80\x7f' # justfloat 格式的帧尾

# 波形参数 (每个通道可以有不同的参数以模拟不同导联)
# [ (amplitude_base, frequency_base_hz, phase_offset_rad, baseline_offset), ... for 8 channels ]
WAVE_PARAMS = [
    (1000, 1.0, 0, 0),        # Lead I (example)
    (1500, 1.0, math.pi/4, 50), # Lead II
    (800,  1.2, math.pi/2, -30),# V1
    (900,  0.9, math.pi, 20),   # V2
    (1200, 1.1, 3*math.pi/2, 0),# V3
    (1000, 1.0, math.pi/3, -10),# V4
    (1100, 0.8, 2*math.pi/3, 40),# V5
    (950,  1.3, 4*math.pi/3, -20) # V6
]
# 为PQRST波添加一些额外的频率和幅度
PQRST_COMPONENTS = [
    {'freq_multiplier': 5, 'amp_multiplier': 0.3, 'phase_offset': 0.1}, # QRS complex
    {'freq_multiplier': 0.5, 'amp_multiplier': 0.15, 'phase_offset': -0.2}, # P wave
    {'freq_multiplier': 0.7, 'amp_multiplier': 0.25, 'phase_offset': 0.5}  # T wave
]
NOISE_AMPLITUDE = 50 # 随机噪声幅度

def generate_ecg_value(t, params, component_params, noise_amp):
    """生成单个ECG采样点值"""
    base_amp, base_freq, base_phase, baseline = params
    signal = baseline + base_amp * math.sin(2 * math.pi * base_freq * t + base_phase)

    # 添加PQRST成分
    for comp in component_params:
        signal += (base_amp * comp['amp_multiplier'] *
                   math.sin(2 * math.pi * base_freq * comp['freq_multiplier'] * t + base_phase + comp['phase_offset']))

    # 添加噪声
    signal += random.uniform(-noise_amp, noise_amp)
    return signal

def main():
    print(f"ECG 8导联数据模拟器")
    print(f"尝试连接到虚拟串口: {VIRTUAL_SERIAL_PORT} @ {BAUD_RATE} bps")
    print(f"模拟采样率: {SAMPLING_RATE_HZ} Hz (发送间隔: {SEND_INTERVAL_S:.4f} s)")
    print(f"按 Ctrl+C 停止模拟。")

    try:
        ser = serial.Serial(VIRTUAL_SERIAL_PORT, BAUD_RATE, timeout=1)
        print(f"成功连接到 {VIRTUAL_SERIAL_PORT}")
    except serial.SerialException as e:
        print(f"错误: 无法打开串口 {VIRTUAL_SERIAL_PORT}: {e}")
        print("请确保虚拟串口已正确设置并且名称无误。")
        print("Linux示例: socat PTY,raw,echo=0,link=/tmp/ttyV0 PTY,raw,echo=0,link=/tmp/ttyV1")
        return

    current_time_s = 0
    sequence_num = 0

    try:
        while True:
            ecg_leads_data = []
            for i in range(NUM_CHANNELS):
                value = generate_ecg_value(current_time_s, WAVE_PARAMS[i], PQRST_COMPONENTS, NOISE_AMPLITUDE)
                ecg_leads_data.append(float(value))
            
            # 打包数据: 8个float (little-endian)
            packed_data = struct.pack(f'<{NUM_CHANNELS}f', *ecg_leads_data)
            
            # 附加帧尾
            frame_to_send = packed_data + FRAME_TAIL
            
            ser.write(frame_to_send)
            
            if sequence_num % SAMPLING_RATE_HZ == 0: # 每秒打印一次简略信息
                print(f"[{time.strftime('%H:%M:%S')}] 已发送帧 {sequence_num}. Lead I: {ecg_leads_data[0]:.2f}, Lead II: {ecg_leads_data[1]:.2f}...")

            current_time_s += SEND_INTERVAL_S
            sequence_num += 1
            time.sleep(SEND_INTERVAL_S)

    except KeyboardInterrupt:
        print("\n模拟器停止。")
    except Exception as e:
        print(f"\n发生错误: {e}")
    finally:
        if 'ser' in locals() and ser.is_open:
            ser.close()
            print(f"串口 {VIRTUAL_SERIAL_PORT} 已关闭。")

if __name__ == "__main__":
    main()
