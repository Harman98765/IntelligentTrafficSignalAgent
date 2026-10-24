import pygame
import random
import math
import csv
import os
from datetime import datetime
from agent import choose_signal, fixed_signal
from routing import astar

class UtilsMixin:
    def draw_text(self, value, x, y, color=self.WHITE, f=self.font):
        self.screen.blit(f.render(str(value), True, color), (x, y))

    def road_check(self, x, y):
        vertical = any((c - 50 <= x <= c + 50 for c in self.CENTERS)) and 0 <= y <= self.HEIGHT
        horizontal = 0 <= x <= self.WIDTH and self.ROAD_Y1 <= y <= self.ROAD_Y2
        return vertical or horizontal

    def lane_x(self, direction, c):
        return c - 25 if direction == 'N' else c + 25

    def vehicle_rect(self, v, x=None, y=None):
        x = v['x'] if x is None else x
        y = v['y'] if y is None else y
        w, h = (18, 30) if v['d'] in ('N', 'S') else (30, 18)
        return pygame.Rect(round(x - w / 2), round(y - h / 2), w, h)

    def spawn_clear(self, d, x, y):
        for v in self.vehicles:
            if v['d'] == d and math.hypot(v['x'] - x, v['y'] - y) < 65:
                return False
        return True
