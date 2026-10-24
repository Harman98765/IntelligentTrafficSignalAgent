import pygame
import random
import math
import csv
import os
from datetime import datetime
from agent import choose_signal, fixed_signal
from routing import astar

class RendererMixin:
    def draw_roads(self):
        self.screen.fill(self.GRASS)
        pygame.draw.rect(self.screen, self.ROAD, (0, self.ROAD_Y1, self.WIDTH, self.ROAD_Y2 - self.ROAD_Y1))
        for c in self.CENTERS:
            pygame.draw.rect(self.screen, self.ROAD, (c - 50, 0, 100, self.HEIGHT))
        for x in range(0, self.WIDTH, 40):
            pygame.draw.line(self.screen, self.YELLOW, (x, 325), (min(x + 20, self.WIDTH), 325), 3)
        for c in self.CENTERS:
            for y in range(0, self.HEIGHT, 40):
                if not self.ROAD_Y1 <= y <= self.ROAD_Y2:
                    pygame.draw.line(self.screen, self.YELLOW, (c, y), (c, min(y + 20, self.HEIGHT)), 3)

    def draw_vehicle(self, v):
        pygame.draw.rect(self.screen, self.ORANGE if v['emergency'] else self.BLUE, self.vehicle_rect(v), border_radius=4)
        if v['emergency']:
            pygame.draw.rect(self.screen, self.RED, self.vehicle_rect(v), 2, border_radius=4)

    def draw_signal(self, x, y, active, label):
        pygame.draw.rect(self.screen, self.BLACK, (x, y, 44, 72), border_radius=6)
        pygame.draw.circle(self.screen, self.RED if active == 'RED' else (75, 25, 25), (x + 22, y + 18), 12)
        pygame.draw.circle(self.screen, self.GREEN if active == 'GREEN' else (20, 65, 25), (x + 22, y + 52), 12)
        label_surface = self.small.render(label, True, self.WHITE)
        self.screen.blit(label_surface, (x + (44 - label_surface.get_width()) // 2, y + 75))

    def draw_signals(self):
        for c in self.CENTERS:
            state = self.signals[c]
            ns = 'GREEN' if state == 'NS' else 'RED'
            ew = 'GREEN' if state == 'EW' else 'RED'
            if state == 'ALL_RED':
                ns = ew = 'RED'
            self.draw_signal(c + 55, 15, ew, 'E<->W')
            self.draw_signal(c + 105, 15, ns, 'N<->S')

    def draw_dashboard(self):
        pygame.draw.rect(self.screen, self.BLACK, (10, 10, 220, 150), border_radius=8)
        self.draw_text('TRAFFIC MONITOR', 20, 18, self.YELLOW)
        self.draw_text(f'Mode: {self.mode}', 20, 44)
        self.draw_text(f'Traffic: {self.traffic_mode}', 20, 66)
        self.draw_text(f'Vehicles: {len(self.vehicles)}/{self.MAX_VEHICLES}', 20, 88)
        self.draw_text(f"Emergency: {sum((v['emergency'] for v in self.vehicles))}", 20, 110)
        self.draw_text(f'Waiting: {self.total_wait // 60}s', 20, 132)
        pygame.draw.rect(self.screen, self.BLACK, (10, self.HEIGHT - 95, 390, 85), border_radius=8)
        self.draw_text('F: Fixed | I: AI | N: Normal | P: Peak', 20, self.HEIGHT - 85, self.WHITE, self.small)
        self.draw_text('A*: emergency routing only | ESC: Quit', 20, self.HEIGHT - 60, self.WHITE, self.small)
        self.draw_text('Vehicles inside a junction clear it on red', 20, self.HEIGHT - 35, self.WHITE, self.small)
