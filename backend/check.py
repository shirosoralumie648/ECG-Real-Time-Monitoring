import numpy as np
import neurokit2 as nk
import matplotlib.pyplot as plt

# 读取 .npy 文件中的数据
def read_data(file_path):
    # 使用 numpy 加载 .npy 文件
    data = np.load(file_path)
    return data

# 删除前30组和后30组数据
def preprocess_data(data, remove_samples=30):
    # 切片操作：去除前30组和后30组数据
    data = data[remove_samples:-remove_samples]
    return data

# 使用 nk.ecg_process() 进行分析
def analyze_ecg(data, sampling_rate=400):
    # 处理 ECG 信号
    signals, info = nk.ecg_process(data, sampling_rate=sampling_rate)

    # 打印处理后的 ECG 特征
    print("Processed ECG signals:")
    print(signals.head())  # 显示前几行处理后的信号数据

    print("\nAdditional info about the ECG signal:")
    print(info)  # 显示有关信号的详细信息

    # 绘制 ECG 波形
    nk.ecg_plot(signals, info)

    return signals, info

# 主函数
if __name__ == "__main__":
    file_path = "lead_0_1732628349.645503_1732628380.1220875.npy"  # 修改为你的文件路径
    data = read_data(file_path)

    # 预处理数据，去除前30组和后30组数据
    processed_data = preprocess_data(data)

    # 使用 nk.ecg_process() 进行分析并可视化
    analyze_ecg(processed_data)
    plt.show()  # 显示图形