
import heapq

def astar(start,goal,blocked=None,grid_x=None,grid_y=None,road_check=None):
    if grid_x is None or grid_y is None:
        return []

    blocked=set(blocked or [])
    rows,cols=len(grid_y),len(grid_x)

    def valid(node):
        r,c=node
        if not (0<=r<rows and 0<=c<cols):
            return False
        if node in blocked and node!=goal:
            return False
        if road_check and not road_check(grid_x[c],grid_y[r]):
            return False
        return True

    def heuristic(a,b):
        return abs(grid_x[a[1]]-grid_x[b[1]])+abs(grid_y[a[0]]-grid_y[b[0]])

    if not valid(start) or not valid(goal):
        return []

    frontier=[(heuristic(start,goal),0,start)]
    came_from={start:None}
    costs={start:0}

    while frontier:
        _,cost,current=heapq.heappop(frontier)

        if current==goal:
            break
        if cost!=costs.get(current):
            continue

        r,c=current
        for nxt in ((r-1,c),(r+1,c),(r,c-1),(r,c+1)):
            if not valid(nxt):
                continue

            nr,nc=nxt
            step=abs(grid_x[nc]-grid_x[c])+abs(grid_y[nr]-grid_y[r])
            new_cost=cost+step

            if new_cost<costs.get(nxt,float("inf")):
                costs[nxt]=new_cost
                came_from[nxt]=current
                heapq.heappush(frontier,(new_cost+heuristic(nxt,goal),new_cost,nxt))

    if goal not in came_from:
        return []

    path=[]
    node=goal

    while node is not None:
        path.append((grid_x[node[1]],grid_y[node[0]]))
        node=came_from[node]

    return path[::-1]
