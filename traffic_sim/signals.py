import pygame
import random
import math
import csv
import os
from datetime import datetime
from agent import choose_signal, fixed_signal
from routing import astar

class SignalsMixin:
    def signal_for(self, d):
        return 'NS' if d in ('N', 'S') else 'EW'

    def junction_ahead(self, v):
        d, x, y = (v['d'], v['x'], v['y'])
        candidates = []
        for c in self.CENTERS:
            if c in v['passed'] or c == v['crossing']:
                continue
            if d == 'N' and abs(x - (c - 25)) < 5 and (y < self.ROAD_Y1):
                candidates.append((self.ROAD_Y1 - y, c))
            elif d == 'S' and abs(x - (c + 25)) < 5 and (y > self.ROAD_Y2):
                candidates.append((y - self.ROAD_Y2, c))
            elif d == 'E' and y == 275 and (x > c + 50):
                candidates.append((x - (c + 50), c))
            elif d == 'W' and y == 375 and (x < c - 50):
                candidates.append((c - 50 - x, c))
        if not candidates:
            return None
        return min(candidates)[1]

    def entering_junction(self, v, nx, ny, c):
        d = v['d']
        x, y = (v['x'], v['y'])
        if d == 'N':
            return x == c - 25 and y < self.ROAD_Y1 and (ny >= self.ROAD_Y1)
        if d == 'S':
            return x == c + 25 and y > self.ROAD_Y2 and (ny <= self.ROAD_Y2)
        if d == 'E':
            return y == 275 and x > c + 50 and (nx <= c + 50)
        return y == 375 and x < c - 50 and (nx >= c - 50)

    def left_junction(self, v, nx, ny, c):
        d = v['d']
        if d == 'N':
            return ny >= self.ROAD_Y2
        if d == 'S':
            return ny <= self.ROAD_Y1
        if d == 'E':
            return nx <= c - 50
        return nx >= c + 50

    def queues_for(self, c):
        queues = {d: 0 for d in ('N', 'S', 'E', 'W')}
        waits = {d: 0 for d in ('N', 'S', 'E', 'W')}
        for v in self.vehicles:
            if v['crossing'] == c:
                continue
            if v['d'] == 'N' and abs(v['x'] - (c - 25)) < 5 and (self.ROAD_Y1 - 100 <= v['y'] < self.ROAD_Y1):
                queues['N'] += 1
                waits['N'] += v['wait']
            elif v['d'] == 'S' and abs(v['x'] - (c + 25)) < 5 and (self.ROAD_Y2 < v['y'] <= self.ROAD_Y2 + 100):
                queues['S'] += 1
                waits['S'] += v['wait']
            elif v['d'] == 'E' and c + 50 < v['x'] <= c + 150 and (abs(v['y'] - 275) < 5):
                queues['E'] += 1
                waits['E'] += v['wait']
            elif v['d'] == 'W' and c - 150 <= v['x'] < c - 50 and (abs(v['y'] - 375) < 5):
                queues['W'] += 1
                waits['W'] += v['wait']
        return (queues, waits)

    def update_signals(self):
        for c in self.CENTERS:
            self.signal_timers[c] += 1
            if self.signals[c] == 'ALL_RED':
                self.all_red[c] -= 1
                if self.all_red[c] <= 0:
                    self.signals[c] = 'EW' if self.previous[c] == 'NS' else 'NS'
                    self.signal_timers[c] = 0
                continue
            emergency = next((v for v in self.vehicles if v['emergency'] and v['crossing'] is None and (self.junction_ahead(v) == c)), None)
            if self.mode == 'FIXED':
                wanted = 'EW' if self.signals[c] == 'NS' else 'NS'
                if self.signal_timers[c] < 150:
                    continue
            elif emergency:
                wanted = self.signal_for(emergency['d'])
            else:
                queues, waits = self.queues_for(c)
                wanted = choose_signal(queues, waits, None)
                if wanted not in ('NS', 'EW'):
                    wanted = 'NS'
            if wanted in ('NS', 'EW') and wanted != self.signals[c]:
                self.previous[c] = self.signals[c]
                self.signals[c] = 'ALL_RED'
                self.all_red[c] = 15
                self.signal_timers[c] = 0
            elif self.mode == 'FIXED' and self.signal_timers[c] >= 150:
                self.previous[c] = self.signals[c]
                self.signals[c] = 'ALL_RED'
                self.all_red[c] = 15
                self.signal_timers[c] = 0
            elif self.mode == 'AI' and self.signal_timers[c] >= 180:
                self.previous[c] = self.signals[c]
                self.signals[c] = 'ALL_RED'
                self.all_red[c] = 15
                self.signal_timers[c] = 0
