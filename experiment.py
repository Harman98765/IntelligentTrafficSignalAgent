import random
import pandas as pd
from agent import choose_signal,fixed_signal

def run_simulation(mode,steps=3600,seed=42):
    rng=random.Random(seed)
    directions=("N","S","E","W")
    queues={d:[] for d in directions}
    total_wait=0
    vehicles_passed=0
    signal="NS"
    max_queue=0

    arrivals=[
        [rng.random()<0.035 for d in directions]
        for _ in range(steps)
    ]

    for t in range(steps):
        for i,d in enumerate(directions):
            if arrivals[t][i]:
                queues[d].append(0)

        for d in directions:
            for i in range(len(queues[d])):
                queues[d][i]+=1
            total_wait+=len(queues[d])

        max_queue=max(max_queue,sum(map(len,queues.values())))

        if t%30==0:
            if mode=="AI":
                counts={d:len(queues[d]) for d in directions}
                waits={d:sum(queues[d]) for d in directions}
                signal=choose_signal(counts,waits,None)
            else:
                signal=fixed_signal(t)

        active=("N","S") if signal=="NS" else ("E","W")

        for d in active:
            if queues[d]:
                queues[d].pop(0)
                vehicles_passed+=1

    remaining=sum(len(q) for q in queues.values())
    average_wait=total_wait/max(vehicles_passed,1)/60

    return {
        "Mode":mode,
        "Average Waiting Time (seconds)":round(average_wait,2),
        "Vehicles Passed":vehicles_passed,
        "Vehicles Remaining":remaining,
        "Maximum Queue Length":max_queue,
        "Simulation Steps":steps,
        "Random Seed":seed
    }

if __name__=="__main__":
    results=[
        run_simulation("FIXED"),
        run_simulation("AI")
    ]

    df=pd.DataFrame(results)
    df.to_csv("experiment_results.csv",index=False)
    print(df.to_string(index=False))
    print("\nSaved experiment_results.csv")