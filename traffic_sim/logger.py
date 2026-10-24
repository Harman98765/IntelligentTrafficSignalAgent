import pygame
import random
import math
import csv
import os
from datetime import datetime
from agent import choose_signal, fixed_signal
from routing import astar

class LoggerMixin:
    def log_data(self):
        if self.frame_count - self.last_log_frame < 60:
            return
        self.last_log_frame = self.frame_count
        with open(self.CSV_FILE, 'a', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            for c in self.CENTERS:
                queues, _ = self.queues_for(c)
                writer.writerow([datetime.now().isoformat(timespec='seconds'), self.mode, self.traffic_mode, c, self.signals[c], len(self.vehicles), sum((v['emergency'] for v in self.vehicles)), queues['N'], queues['S'], queues['E'], queues['W'], self.total_wait])
