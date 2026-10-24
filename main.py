
import pygame
import random
import math
import csv
import os
from datetime import datetime
from agent import choose_signal, fixed_signal
from routing import astar

pygame.init()

WIDTH,HEIGHT=1000,600
screen=pygame.display.set_mode((WIDTH,HEIGHT))
pygame.display.set_caption("Intelligent Traffic Signal Agent")
clock=pygame.time.Clock()
font=pygame.font.SysFont("Arial",17)
small=pygame.font.SysFont("Arial",13)

WHITE=(245,245,245)
BLACK=(15,15,15)
ROAD=(65,65,65)
GRASS=(35,110,45)
YELLOW=(255,220,0)
RED=(235,55,55)
GREEN=(40,210,80)
BLUE=(45,145,255)
ORANGE=(255,145,30)
PURPLE=(220,40,220)

WIDTHS=50
CENTERS=[300,700]
ROAD_Y1,ROAD_Y2=250,400
MAX_VEHICLES=60
NORMAL_SPEED=3.0
EMERGENCY_SPEED=4.5
MIN_GAP=36
SPAWN_NORMAL=65
SPAWN_PEAK=32
CSV_FILE="traffic_data.csv"

GRID_X=[225,250,275,325,350,375,625,650,675,725,750,775]
GRID_Y=[25,100,175,225,275,325,375,425,475,575,675]

vehicles=[]
signals={c:"NS" for c in CENTERS}
signal_timers={c:0 for c in CENTERS}
all_red={c:0 for c in CENTERS}
previous={c:"NS" for c in CENTERS}
mode="AI"
traffic_mode="NORMAL"
spawn_timer=0
total_wait=0
frame_count=0
last_log_frame=0
running=True

if not os.path.exists(CSV_FILE) or os.path.getsize(CSV_FILE)==0:
    with open(CSV_FILE,"w",newline="",encoding="utf-8") as f:
        csv.writer(f).writerow([
            "timestamp","mode","traffic_mode","junction","signal",
            "vehicles","emergency_vehicles","north_queue","south_queue",
            "east_queue","west_queue","cumulative_wait_frames"
        ])

def draw_text(value,x,y,color=WHITE,f=font):
    screen.blit(f.render(str(value),True,color),(x,y))

def road_check(x,y):
    vertical=any(c-50<=x<=c+50 for c in CENTERS) and 0<=y<=HEIGHT
    horizontal=0<=x<=WIDTH and ROAD_Y1<=y<=ROAD_Y2
    return vertical or horizontal

def lane_x(direction,c):
    return c-25 if direction=="N" else c+25

def vehicle_rect(v,x=None,y=None):
    x=v["x"] if x is None else x
    y=v["y"] if y is None else y
    w,h=(18,30) if v["d"] in ("N","S") else (30,18)
    return pygame.Rect(round(x-w/2),round(y-h/2),w,h)

def spawn_clear(d,x,y):
    for v in vehicles:
        if v["d"]==d and math.hypot(v["x"]-x,v["y"]-y)<65:
            return False
    return True

def spawn_vehicle():
    if len(vehicles)>=MAX_VEHICLES:
        return

    d=random.choice(("N","S","E","W"))
    c=random.choice(CENTERS)

    if d=="N":
        x,y=c-25,-20
    elif d=="S":
        x,y=c+25,HEIGHT+20
    elif d=="E":
        x,y=WIDTH+20,300
    else:
        x,y=-20,350

    if not spawn_clear(d,x,y):
        return

    vehicles.append({
        "d":d,"x":float(x),"y":float(y),
        "emergency":random.random()<0.08,
        "wait":0,"blocked":0,
        "route":[],"route_index":0,
        "target":c,"passed":set(),"crossing":None
    })

def signal_for(d):
    return "NS" if d in ("N","S") else "EW"

def junction_ahead(v):
    d,x,y=v["d"],v["x"],v["y"]
    candidates=[]

    for c in CENTERS:
        if c in v["passed"] or c==v["crossing"]:
            continue

        if d=="N" and abs(x-(c-25))<5 and y<ROAD_Y1:
            candidates.append((ROAD_Y1-y,c))
        elif d=="S" and abs(x-(c+25))<5 and y>ROAD_Y2:
            candidates.append((y-ROAD_Y2,c))
        elif d=="E" and abs(y-300)<5 and x>c+50:
            candidates.append((x-(c+50),c))
        elif d=="W" and abs(y-350)<5 and x<c-50:
            candidates.append(((c-50)-x,c))

    if not candidates:
        return None
    return min(candidates)[1]

def entering_junction(v,nx,ny,c):
    d=v["d"]
    x,y=v["x"],v["y"]

    if d=="N":
        return x==c-25 and y<ROAD_Y1 and ny>=ROAD_Y1
    if d=="S":
        return x==c+25 and y>ROAD_Y2 and ny<=ROAD_Y2
    if d=="E":
        return abs(y-300)<5 and x>c+50 and nx<=c+50
    return abs(y-350)<5 and x<c-50 and nx>=c-50

def left_junction(v,nx,ny,c):
    d=v["d"]
    if d=="N":
        return ny>=ROAD_Y2
    if d=="S":
        return ny<=ROAD_Y1
    if d=="E":
        return nx<=c-50
    return nx>=c+50

def queues_for(c):
    queues={d:0 for d in ("N","S","E","W")}
    waits={d:0 for d in ("N","S","E","W")}

    for v in vehicles:
        if v["crossing"]==c:
            continue
        if v["d"]=="N" and abs(v["x"]-(c-25))<5 and ROAD_Y1-100<=v["y"]<ROAD_Y1:
            queues["N"]+=1
            waits["N"]+=v["wait"]
        elif v["d"]=="S" and abs(v["x"]-(c+25))<5 and ROAD_Y2<v["y"]<=ROAD_Y2+100:
            queues["S"]+=1
            waits["S"]+=v["wait"]
        elif v["d"]=="E" and c+50<v["x"]<=c+150 and abs(v["y"]-300)<5:
            queues["E"]+=1
            waits["E"]+=v["wait"]
        elif v["d"]=="W" and c-150<=v["x"]<c-50 and abs(v["y"]-350)<5:
            queues["W"]+=1
            waits["W"]+=v["wait"]

    return queues,waits


def update_signals():
    for c in CENTERS:
        signal_timers[c]+=1

        if signals[c]=="ALL_RED":
            all_red[c]-=1
            if all_red[c]<=0:
                signals[c]="EW" if previous[c]=="NS" else "NS"
                signal_timers[c]=0
            continue

        emergency=next(
            (v for v in vehicles
             if v["emergency"] and v["crossing"] is None
             and junction_ahead(v)==c),
            None
        )

        if mode=="FIXED":
            if signal_timers[c]<150:
                continue
            wanted="EW" if signals[c]=="NS" else "NS"
        elif emergency:
            wanted=signal_for(emergency["d"])
        else:
            queues,waits=queues_for(c)
            wanted=choose_signal(queues,waits,None)
            if wanted not in ("NS","EW"):
                wanted="NS"

        if mode=="AI" and signal_timers[c]<90:
            continue

        if wanted in ("NS","EW") and wanted!=signals[c]:
            previous[c]=signals[c]
            signals[c]="ALL_RED"
            all_red[c]=45
            signal_timers[c]=0
        elif mode=="FIXED" and signal_timers[c]>=150:
            previous[c]=signals[c]
            signals[c]="ALL_RED"
            all_red[c]=45
            signal_timers[c]=0
        elif mode=="AI" and signal_timers[c]>=300:
            previous[c]=signals[c]
            signals[c]="ALL_RED"
            all_red[c]=45
            signal_timers[c]=0


def nearest_node(x,y):
    r=min(range(len(GRID_Y)),key=lambda i:abs(GRID_Y[i]-y))
    c=min(range(len(GRID_X)),key=lambda i:abs(GRID_X[i]-x))
    return r,c

def build_emergency_route(v,c):
    if not v["emergency"] or v["crossing"] is not None:
        return

    d=v["d"]
    x,y=v["x"],v["y"]

    if d in ("E","W"):
        bypass_y=225 if y<325 else 425
        start=nearest_node(x,y)
        entry=nearest_node(c,bypass_y)
        exit_node=nearest_node(c+100 if d=="E" else c-100,bypass_y)
        goal=nearest_node(0 if d=="E" else WIDTH,y)
    else:
        bypass_x=c-50 if d=="N" else c+50
        start=nearest_node(x,y)
        entry=nearest_node(bypass_x,ROAD_Y1 if d=="N" else ROAD_Y2)
        exit_node=nearest_node(bypass_x,ROAD_Y2 if d=="N" else ROAD_Y1)
        goal=nearest_node(x,HEIGHT if d=="N" else 0)

    segments=[
        astar(start,entry,grid_x=GRID_X,grid_y=GRID_Y,road_check=road_check),
        astar(entry,exit_node,grid_x=GRID_X,grid_y=GRID_Y,road_check=road_check),
        astar(exit_node,goal,grid_x=GRID_X,grid_y=GRID_Y,road_check=road_check)
    ]

    if any(not path for path in segments):
        return

    path=[]
    for segment in segments:
        for point in segment:
            if not path or path[-1]!=point:
                path.append(point)

    v["route"]=path
    v["route_index"]=0

def collision(v,nx,ny):
    r=vehicle_rect(v,nx,ny)
    for other in vehicles:
        if other is not v and r.colliderect(vehicle_rect(other)):
            return True
    return False

def blocked_ahead(v):
    for other in vehicles:
        if other is v or other["d"]!=v["d"]:
            continue

        dx=other["x"]-v["x"]
        dy=other["y"]-v["y"]
        d=v["d"]

        if d=="N" and abs(dx)<15 and 0<dy<MIN_GAP:
            return True
        if d=="S" and abs(dx)<15 and 0<-dy<MIN_GAP:
            return True
        if d=="E" and abs(dy)<15 and 0<-dx<MIN_GAP:
            return True
        if d=="W" and abs(dy)<15 and 0<dx<MIN_GAP:
            return True

    return False

def move_vehicle(v):
    global total_wait

    d=v["d"]
    speed=EMERGENCY_SPEED if v["emergency"] else NORMAL_SPEED

    if v["emergency"] and v["route"] and v["route_index"]<len(v["route"]):
        tx,ty=v["route"][v["route_index"]]
        dx,dy=tx-v["x"],ty-v["y"]
        distance=math.hypot(dx,dy)

        if distance<speed+2:
            v["x"],v["y"]=tx,ty
            v["route_index"]+=1
            if v["route_index"]>=len(v["route"]):
                v["route"]=[]
                v["route_index"]=0
            return

        nx=v["x"]+dx/distance*speed
        ny=v["y"]+dy/distance*speed

        if collision(v,nx,ny):
            v["wait"]+=1
            total_wait+=1
            return

        v["x"],v["y"]=nx,ny
        v["wait"]=0
        return

    nx,ny=v["x"],v["y"]

    if d=="N":
        ny+=speed
    elif d=="S":
        ny-=speed
    elif d=="E":
        nx-=speed
    else:
        nx+=speed

    c=v["crossing"]

    if c is None:
        c=junction_ahead(v)
        if c is not None:
            distance=abs(ROAD_Y1-v["y"]) if d=="N" else abs(v["y"]-ROAD_Y2) if d=="S" else abs(v["x"]-(c+50)) if d=="E" else abs((c-50)-v["x"])
            red=signals[c]=="ALL_RED" or (d in ("N","S") and signals[c]!="NS") or (d in ("E","W") and signals[c]!="EW")
            if red and distance<=40:
                v["wait"]+=1
                total_wait+=1
                return
            if entering_junction(v,nx,ny,c):
                    if not v["emergency"] and signals[c]!="NS" and d in ("N","S"):
                        v["wait"]+=1
                        total_wait+=1
                        return
                    if not v["emergency"] and signals[c]!="EW" and d in ("E","W"):
                        v["wait"]+=1
                        total_wait+=1
                        return

                    if signals[c]=="ALL_RED" and not v["emergency"]:
                        v["wait"]+=1
                        total_wait+=1
                        return

                    v["crossing"]=c
                    v["blocked"]=0

    if v["crossing"] is not None:
        c=v["crossing"]
        if left_junction(v,nx,ny,c):
            if collision(v,nx,ny):
                v["wait"]+=1
                total_wait+=1
                return
            v["x"],v["y"]=nx,ny
            v["passed"].add(c)
            v["crossing"]=None
            v["wait"]=0
            return

    if blocked_ahead(v):
        v["wait"]+=1
        v["blocked"]+=1
        total_wait+=1

        c=junction_ahead(v)
        if v["emergency"] and c is not None and v["blocked"]>=30:
            build_emergency_route(v,c)
            v["blocked"]=0
        return

    if collision(v,nx,ny):
        v["wait"]+=1
        total_wait+=1
        return

    v["x"],v["y"]=nx,ny
    v["wait"]=0

def update_vehicles():
    remove=[]

    for v in list(vehicles):
        move_vehicle(v)
        d,x,y=v["d"],v["x"],v["y"]

        if d=="N" and y>HEIGHT+35:
            remove.append(v)
        elif d=="S" and y<-35:
            remove.append(v)
        elif d=="E" and x<-35:
            remove.append(v)
        elif d=="W" and x>WIDTH+35:
            remove.append(v)

    for v in remove:
        if v in vehicles:
            vehicles.remove(v)

def log_data():
    global last_log_frame

    if frame_count-last_log_frame<60:
        return

    last_log_frame=frame_count

    with open(CSV_FILE,"a",newline="",encoding="utf-8") as f:
        writer=csv.writer(f)
        for c in CENTERS:
            queues,_=queues_for(c)
            writer.writerow([
                datetime.now().isoformat(timespec="seconds"),
                mode,traffic_mode,c,signals[c],len(vehicles),
                sum(v["emergency"] for v in vehicles),
                queues["N"],queues["S"],queues["E"],queues["W"],total_wait
            ])

def draw_roads():
    screen.fill(GRASS)
    pygame.draw.rect(screen,ROAD,(0,ROAD_Y1,WIDTH,ROAD_Y2-ROAD_Y1))

    for c in CENTERS:
        pygame.draw.rect(screen,ROAD,(c-75,0,150,HEIGHT))

    for x in range(0,WIDTH,40):
        if not any(x+20>=c-75-20 and x<=c+75+20 for c in CENTERS):
            pygame.draw.line(screen,WHITE,(x,325),(min(x+20,WIDTH),325),3)

    for c in CENTERS:
        for y in range(0,HEIGHT,40):
            if y+20<=ROAD_Y1-20 or y>=ROAD_Y2+20:
                pygame.draw.line(screen,WHITE,(c,y),(c,min(y+20,HEIGHT)),3)

    for c in CENTERS:
        pygame.draw.rect(screen,WHITE,(c-50,ROAD_Y1 +25,100,3))
        pygame.draw.rect(screen,WHITE,(c-50,ROAD_Y2-28,100,3))
        pygame.draw.rect(screen,WHITE,(c-50,275,3,100))
        pygame.draw.rect(screen,WHITE,(c+50,275,3,100))

def draw_vehicle(v):
    pygame.draw.rect(screen,ORANGE if v["emergency"] else BLUE,
                     vehicle_rect(v),border_radius=4)
    if v["emergency"]:
        pygame.draw.rect(screen,RED,vehicle_rect(v),2,border_radius=4)

def draw_signal(x,y,active,label):
    pygame.draw.rect(screen,BLACK,(x,y,44,72),border_radius=6)
    pygame.draw.circle(screen,RED if active=="RED" else (75,25,25),(x+22,y+18),12)
    pygame.draw.circle(screen,GREEN if active=="GREEN" else (20,65,25),(x+22,y+52),12)
    label_surface=small.render(label,True,WHITE)
    screen.blit(label_surface,(x+(44-label_surface.get_width())//2,y+75))

def draw_signals():
    for i,c in enumerate(CENTERS):
        state=signals[c]
        ns="GREEN" if state=="NS" else "RED"
        ew="GREEN" if state=="EW" else "RED"
        if state=="ALL_RED":
            ns=ew="RED"

        x=127 if i==0 else 779
        y=155
        draw_signal(x,y,ew,"E<->W")
        draw_signal(x+50,y,ns,"N<->S")

def draw_dashboard():
    pygame.draw.rect(screen,BLACK,(385,10,230,150),border_radius=8)
    draw_text("TRAFFIC MONITOR",395,18,YELLOW)
    draw_text(f"Mode: {mode}",410,44)
    draw_text(f"Traffic: {traffic_mode}",410,66)
    draw_text(f"Vehicles: {len(vehicles)}/{MAX_VEHICLES}",410,88)
    draw_text(f"Emergency: {sum(v['emergency'] for v in vehicles)}",410,110)
    draw_text(f"Waiting: {total_wait//60}s",410,132)

    pygame.draw.rect(screen,BLACK,(385,HEIGHT-95,230,85),border_radius=8)
    draw_text("F: Fixed | I: AI | N: Normal | P: Peak",410,HEIGHT-85,WHITE,small)
    draw_text("A*: emergency routing | ESC: Quit",410,HEIGHT-60,WHITE,small)
    draw_text("Vehicles clear junctions on red",410,HEIGHT-35,WHITE,small)

while running:
    clock.tick(60)
    frame_count+=1

    for event in pygame.event.get():
        if event.type==pygame.QUIT:
            running=False
        elif event.type==pygame.KEYDOWN:
            if event.key==pygame.K_ESCAPE:
                running=False
            elif event.key==pygame.K_f:
                mode="FIXED"
                signals={c:"NS" for c in CENTERS}
                signal_timers={c:0 for c in CENTERS}
                all_red={c:0 for c in CENTERS}
            elif event.key==pygame.K_i:
                mode="AI"
                signals={c:"NS" for c in CENTERS}
                signal_timers={c:0 for c in CENTERS}
                all_red={c:0 for c in CENTERS}
            elif event.key==pygame.K_n:
                traffic_mode="NORMAL"
            elif event.key==pygame.K_p:
                traffic_mode="PEAK"

    spawn_timer+=1
    interval=SPAWN_NORMAL if traffic_mode=="NORMAL" else SPAWN_PEAK
    if spawn_timer>=interval:
        spawn_vehicle()
        spawn_timer=0

    update_signals()
    update_vehicles()
    log_data()

    draw_roads()
    for v in vehicles:
        draw_vehicle(v)
    draw_signals()
    draw_dashboard()
    pygame.display.flip()

pygame.quit()
