from routing import astar

path=astar((0,0),(7,7),{(2,2),(2,3),(2,4),(3,4),(4,4)})
print("Route:",path)
print("Steps:",len(path)-1 if path else "No route")