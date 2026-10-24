import pygame
import random
import math
import csv
import os
from datetime import datetime
from agent import choose_signal, fixed_signal
from routing import astar

class VehiclesMixin:
    def spawn_vehicle(self):
        if len(self.vehicles) >= self.MAX_VEHICLES:
            return
        d = random.choice(('N', 'S', 'E', 'W'))
        c = random.choice(self.CENTERS)
        if d == 'N':
            x, y = (c - 25, -20)
        elif d == 'S':
            x, y = (c + 25, self.HEIGHT + 20)
        elif d == 'E':
            x, y = (self.WIDTH + 20, 275)
        else:
            x, y = (-20, 375)
        if not self.spawn_clear(d, x, y):
            return
        self.vehicles.append({'d': d, 'x': float(x), 'y': float(y), 'emergency': random.random() < 0.08, 'wait': 0, 'blocked': 0, 'route': [], 'route_index': 0, 'target': c, 'passed': set(), 'crossing': None})

    def nearest_node(self, x, y):
        r = min(range(len(self.GRID_Y)), key=lambda i: abs(self.GRID_Y[i] - y))
        c = min(range(len(self.GRID_X)), key=lambda i: abs(self.GRID_X[i] - x))
        return (r, c)

    def build_emergency_route(self, v, c):
        if not v['emergency'] or v['crossing'] is not None:
            return
        d = v['d']
        x, y = (v['x'], v['y'])
        if d in ('E', 'W'):
            bypass_y = 225 if y < 325 else 425
            start = self.nearest_node(x, y)
            entry = self.nearest_node(c, bypass_y)
            exit_node = self.nearest_node(c + 100 if d == 'E' else c - 100, bypass_y)
            goal = self.nearest_node(0 if d == 'E' else self.WIDTH, y)
        else:
            bypass_x = c - 50 if d == 'N' else c + 50
            start = self.nearest_node(x, y)
            entry = self.nearest_node(bypass_x, self.ROAD_Y1 if d == 'N' else self.ROAD_Y2)
            exit_node = self.nearest_node(bypass_x, self.ROAD_Y2 if d == 'N' else self.ROAD_Y1)
            goal = self.nearest_node(x, self.HEIGHT if d == 'N' else 0)
        segments = [astar(start, entry, grid_x=self.GRID_X, grid_y=self.GRID_Y, road_check=self.road_check), astar(entry, exit_node, grid_x=self.GRID_X, grid_y=self.GRID_Y, road_check=self.road_check), astar(exit_node, goal, grid_x=self.GRID_X, grid_y=self.GRID_Y, road_check=self.road_check)]
        if any((not path for path in segments)):
            return
        path = []
        for segment in segments:
            for point in segment:
                if not path or path[-1] != point:
                    path.append(point)
        v['route'] = path
        v['route_index'] = 0

    def collision(self, v, nx, ny):
        r = self.vehicle_rect(v, nx, ny)
        for other in self.vehicles:
            if other is not v and r.colliderect(self.vehicle_rect(other)):
                return True
        return False

    def blocked_ahead(self, v):
        for other in self.vehicles:
            if other is v or other['d'] != v['d']:
                continue
            dx = other['x'] - v['x']
            dy = other['y'] - v['y']
            d = v['d']
            if d == 'N' and abs(dx) < 15 and (0 < dy < self.MIN_GAP):
                return True
            if d == 'S' and abs(dx) < 15 and (0 < -dy < self.MIN_GAP):
                return True
            if d == 'E' and abs(dy) < 15 and (0 < -dx < self.MIN_GAP):
                return True
            if d == 'W' and abs(dy) < 15 and (0 < dx < self.MIN_GAP):
                return True
        return False

    def move_vehicle(self, v):
        d = v['d']
        speed = self.EMERGENCY_SPEED if v['emergency'] else self.NORMAL_SPEED
        if v['emergency'] and v['route'] and (v['route_index'] < len(v['route'])):
            tx, ty = v['route'][v['route_index']]
            dx, dy = (tx - v['x'], ty - v['y'])
            distance = math.hypot(dx, dy)
            if distance < speed + 2:
                v['x'], v['y'] = (tx, ty)
                v['route_index'] += 1
                if v['route_index'] >= len(v['route']):
                    v['route'] = []
                    v['route_index'] = 0
                return
            nx = v['x'] + dx / distance * speed
            ny = v['y'] + dy / distance * speed
            if self.collision(v, nx, ny):
                v['wait'] += 1
                self.total_wait += 1
                return
            v['x'], v['y'] = (nx, ny)
            v['wait'] = 0
            return
        nx, ny = (v['x'], v['y'])
        if d == 'N':
            ny += speed
        elif d == 'S':
            ny -= speed
        elif d == 'E':
            nx -= speed
        else:
            nx += speed
        c = v['crossing']
        if c is None:
            c = self.junction_ahead(v)
            if c is not None and self.entering_junction(v, nx, ny, c):
                if not v['emergency'] and self.signals[c] != 'NS' and (d in ('N', 'S')):
                    v['wait'] += 1
                    self.total_wait += 1
                    return
                if not v['emergency'] and self.signals[c] != 'EW' and (d in ('E', 'W')):
                    v['wait'] += 1
                    self.total_wait += 1
                    return
                if self.signals[c] == 'ALL_RED' and (not v['emergency']):
                    v['wait'] += 1
                    self.total_wait += 1
                    return
                v['crossing'] = c
                v['blocked'] = 0
        if v['crossing'] is not None:
            c = v['crossing']
            if self.left_junction(v, nx, ny, c):
                if self.collision(v, nx, ny):
                    v['wait'] += 1
                    self.total_wait += 1
                    return
                v['x'], v['y'] = (nx, ny)
                v['passed'].add(c)
                v['crossing'] = None
                v['wait'] = 0
                return
        if self.blocked_ahead(v):
            v['wait'] += 1
            v['blocked'] += 1
            self.total_wait += 1
            c = self.junction_ahead(v)
            if v['emergency'] and c is not None and (v['blocked'] >= 30):
                self.build_emergency_route(v, c)
                v['blocked'] = 0
            return
        if self.collision(v, nx, ny):
            v['wait'] += 1
            self.total_wait += 1
            return
        v['x'], v['y'] = (nx, ny)
        v['wait'] = 0

    def update_vehicles(self):
        remove = []
        for v in list(self.vehicles):
            self.move_vehicle(v)
            d, x, y = (v['d'], v['x'], v['y'])
            if d == 'N' and y > self.HEIGHT + 35:
                remove.append(v)
            elif d == 'S' and y < -35:
                remove.append(v)
            elif d == 'E' and x < -35:
                remove.append(v)
            elif d == 'W' and x > self.WIDTH + 35:
                remove.append(v)
        for v in remove:
            if v in self.vehicles:
                self.vehicles.remove(v)
