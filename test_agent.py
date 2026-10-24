
from agent import choose_signal

queues={"N":8,"S":5,"E":2,"W":3}
waiting_times={"N":30,"S":20,"E":5,"W":10}

print("Selected signal:",choose_signal(queues,waiting_times,None))
print("Emergency priority:",choose_signal(queues,waiting_times,"EW"))
