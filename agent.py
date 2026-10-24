def choose_signal(queues,waiting_times,emergency=None):
    if emergency in ("N","S"):
        return "NS"
    if emergency in ("E","W"):
        return "EW"

    scores={}
    for phase,lanes in {"NS":("N","S"),"EW":("E","W")}.items():
        queue_score=sum(queues.get(d,0) for d in lanes)
        wait_score=sum(waiting_times.get(d,0) for d in lanes)
        scores[phase]=queue_score*5+wait_score*1.5

    return max(scores,key=scores.get)

def fixed_signal(timer):
    return "NS" if (timer//150)%2==0 else "EW"