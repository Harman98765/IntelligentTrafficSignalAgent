import csv
import os
import pygame
from . import config
from .utils import UtilsMixin
from .signals import SignalsMixin
from .vehicles import VehiclesMixin
from .renderer import RendererMixin
from .logger import LoggerMixin

class Simulation(UtilsMixin, SignalsMixin, VehiclesMixin, RendererMixin, LoggerMixin):
    def __init__(self):
        for name in dir(config):
            if name.isupper():
                setattr(self, name, getattr(config, name))
        pygame.init()
        self.screen=pygame.display.set_mode((self.WIDTH,self.HEIGHT))
        pygame.display.set_caption("Intelligent Traffic Signal Agent")
        self.clock=pygame.time.Clock()
        self.font=pygame.font.SysFont("Arial",17)
        self.small=pygame.font.SysFont("Arial",13)
        self.vehicles=[]
        self.signals={c:"NS" for c in self.CENTERS}
        self.signal_timers={c:0 for c in self.CENTERS}
        self.all_red={c:0 for c in self.CENTERS}
        self.previous={c:"NS" for c in self.CENTERS}
        self.mode="AI"
        self.traffic_mode="NORMAL"
        self.spawn_timer=0
        self.total_wait=0
        self.frame_count=0
        self.last_log_frame=0
        self.running=True
        self.initialize_log()

    def initialize_log(self):
        if not os.path.exists(self.CSV_FILE) or os.path.getsize(self.CSV_FILE)==0:
            with open(self.CSV_FILE,"w",newline="",encoding="utf-8") as f:
                csv.writer(f).writerow([
                    "timestamp","mode","traffic_mode","junction","signal",
                    "vehicles","emergency_vehicles","north_queue","south_queue",
                    "east_queue","west_queue","cumulative_wait_frames"
                ])

    def handle_events(self):
        for event in pygame.event.get():
            if event.type==pygame.QUIT:
                self.running=False
            elif event.type==pygame.KEYDOWN:
                if event.key==pygame.K_ESCAPE:
                    self.running=False
                elif event.key==pygame.K_f:
                    self.mode="FIXED"
                    self.reset_signals()
                elif event.key==pygame.K_i:
                    self.mode="AI"
                    self.reset_signals()
                elif event.key==pygame.K_n:
                    self.traffic_mode="NORMAL"
                elif event.key==pygame.K_p:
                    self.traffic_mode="PEAK"

    def reset_signals(self):
        self.signals={c:"NS" for c in self.CENTERS}
        self.signal_timers={c:0 for c in self.CENTERS}
        self.all_red={c:0 for c in self.CENTERS}

    def update(self):
        self.frame_count+=1
        self.spawn_timer+=1
        interval=self.SPAWN_NORMAL if self.traffic_mode=="NORMAL" else self.SPAWN_PEAK
        if self.spawn_timer>=interval:
            self.spawn_vehicle()
            self.spawn_timer=0
        self.update_signals()
        self.update_vehicles()
        self.log_data()

    def render(self):
        self.draw_roads()
        for v in self.vehicles:
            self.draw_vehicle(v)
        self.draw_signals()
        self.draw_dashboard()
        pygame.display.flip()

    def run(self):
        while self.running:
            self.clock.tick(60)
            self.handle_events()
            self.update()
            self.render()
        pygame.quit()
