#data_storage.py

import datetime
import numpy as np
import os


class DataStorage:

    def __init__(self):
        self.data = {i: [] for i in range(12)}
        self.start_time = datetime.datetime.now().strftime('%Y%m%d%H%M%S')

    def save_data_point(self, timestamp, lead_data):
        for i in range(12):
            self.data[i].append(lead_data[i])

    def save_to_npy(self, lead_index, start_timestamp, end_timestamp):
        filename = f"lead_{lead_index}_{start_timestamp}_{end_timestamp}.npy"
        np_data = np.array(self.data[lead_index])
        np.save(filename, np_data)

    def save_all_leads(self, start_timestamp, end_timestamp):
        for i in range(12):
            self.save_to_npy(i, start_timestamp, end_timestamp)

    def reset_data(self):
        self.data = {i: [] for i in range(12)}
        self.start_time = datetime.datetime.now().strftime('%Y%m%d%H%M%S')

