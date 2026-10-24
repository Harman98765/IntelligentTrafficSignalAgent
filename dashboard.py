
import os
import pandas as pd
import streamlit as st
import matplotlib.pyplot as plt

st.set_page_config(page_title="Intelligent Traffic Signal Agent",layout="wide")

st.title("🚦 Intelligent Traffic Signal Agent")
st.caption("AI-based traffic control | Multi-junction simulation | A* emergency routing")

file="traffic_data.csv"

if not os.path.exists(file):
    st.warning("Run the Pygame simulation first to generate traffic_data.csv.")
    st.stop()

data=pd.read_csv(file)
data["junction"]=data["junction"].replace({300:"Left",700:"Right"})

required=[
    "timestamp","mode","traffic_mode","junction","signal","vehicles",
    "emergency_vehicles","north_queue","south_queue","east_queue",
    "west_queue","cumulative_wait_frames"
]

if not all(c in data.columns for c in required):
    st.error("CSV columns do not match the simulation data.")
    st.write("Available columns:",list(data.columns))
    st.stop()

data["timestamp"]=pd.to_datetime(data["timestamp"],errors="coerce")
data=data.dropna(subset=["timestamp"]).sort_values("timestamp")

if data.empty:
    st.warning("No valid timestamped records found.")
    st.stop()

queue_cols=["north_queue","south_queue","east_queue","west_queue"]
data["total_queue"]=data[queue_cols].sum(axis=1)

st.sidebar.header("Dashboard Filters")

modes=st.sidebar.multiselect(
    "Signal Control",
    sorted(data["mode"].dropna().unique()),
    default=list(sorted(data["mode"].dropna().unique()))
)

traffic_modes=st.sidebar.multiselect(
    "Traffic Condition",
    sorted(data["traffic_mode"].dropna().unique()),
    default=list(sorted(data["traffic_mode"].dropna().unique()))
)

junctions=st.sidebar.multiselect(
    "Junction",
    sorted(data["junction"].dropna().unique(),key=str),
    default=list(sorted(data["junction"].dropna().unique(),key=str))
)

filtered=data[
    data["mode"].isin(modes)
    & data["traffic_mode"].isin(traffic_modes)
    & data["junction"].isin(junctions)
].copy()

if filtered.empty:
    st.warning("No records match the selected filters.")
    st.stop()

latest=filtered.iloc[-1]

st.subheader("1. Traffic Overview")

a,b,c,d=st.columns(4)
a.metric("Vehicles in Latest Record",int(latest["vehicles"]))
b.metric("Emergency Vehicles",int(latest["emergency_vehicles"]))
c.metric("Current Total Queue",int(latest["total_queue"]))
d.metric("Cumulative Wait",f'{latest["cumulative_wait_frames"]/30:.1f} seconds')

st.caption("These values describe the latest recorded snapshot, not necessarily completed trips.")

st.divider()
st.subheader("2. Traffic and Queue Analysis")

left,right=st.columns(2)

with left:
    st.markdown("**Vehicle Count Over Time**")
    vehicle_trend=filtered.groupby(
        ["timestamp","mode"],as_index=False
    )["vehicles"].mean()
    vehicle_pivot=vehicle_trend.pivot(
        index="timestamp",columns="mode",values="vehicles"
    )
    st.line_chart(vehicle_pivot)

with right:
    st.markdown("**Total Queue Over Time**")
    queue_trend=filtered.groupby(
        ["timestamp","mode"],as_index=False
    )["total_queue"].mean()
    queue_pivot=queue_trend.pivot(
        index="timestamp",columns="mode",values="total_queue"
    )
    st.line_chart(queue_pivot)

left,right=st.columns(2)

with left:
    st.markdown("**Average Queue by Direction**")
    direction_summary=filtered.groupby("mode")[queue_cols].mean()
    direction_summary.columns=["North","South","East","West"]
    st.bar_chart(direction_summary)

with right:
    st.markdown("**Normal vs Peak Traffic**")
    traffic_summary=filtered.groupby(
        ["traffic_mode","mode"]
    )[["vehicles","total_queue"]].mean()
    st.dataframe(traffic_summary,use_container_width=True)

st.divider()
st.subheader("3. Fixed-Time vs AI Control")

filtered["cumulative_wait_seconds"]=filtered["cumulative_wait_frames"]/30

comparison=filtered.groupby("mode").agg(
    Average_Vehicles=("vehicles","mean"),
    Average_Queue=("total_queue","mean"),
    Maximum_Queue=("total_queue","max"),
    Maximum_Cumulative_Wait=("cumulative_wait_seconds","max")
).round(2)

st.dataframe(comparison,use_container_width=True)

if "FIXED" in comparison.index and "AI" in comparison.index:
    fixed_queue=comparison.loc["FIXED","Average_Queue"]
    ai_queue=comparison.loc["AI","Average_Queue"]
    fixed_wait=comparison.loc["FIXED","Maximum_Cumulative_Wait"]
    ai_wait=comparison.loc["AI","Maximum_Cumulative_Wait"]

    x,y=st.columns(2)

    with x:
        st.markdown("**Average Queue Comparison**")
        if fixed_queue>0:
            change=(fixed_queue-ai_queue)/fixed_queue*100
            st.metric("Queue Change with AI",f"{change:+.1f}%","positive means reduction")
        else:
            st.write("Fixed-time average queue is zero; percentage comparison is unavailable.")

    with y:
        st.markdown("**Maximum Cumulative Wait Comparison**")
        st.write(f"Fixed: {fixed_wait:.0f} seconds")
        st.write(f"AI: {ai_wait:.0f} seconds")
        st.caption("Cumulative wait is displayed in seconds. It is not the average waiting time per vehicle.")

st.divider()
st.subheader("4. Traffic Signal States")

signal_counts=filtered.groupby(["junction","signal"]).size().unstack(fill_value=0)
st.bar_chart(signal_counts)

st.caption("Signal-state counts show how often each state was recorded, not necessarily its exact duration.")

st.divider()
st.subheader("5. Intelligent Agent Features")

f1,f2,f3=st.columns(3)

with f1:
    st.markdown("**Rule-Based Control**")
    st.write("Fixed-time mode provides baseline signal control; AI mode selects signal directions using traffic conditions.")

with f2:
    st.markdown("**Queue-Based Decisions**")
    st.write("Directional queues and cumulative waiting time in seconds help evaluate congestion and signal decisions.")

with f3:
    st.markdown("**Emergency Routing**")
    st.write("A* routing is used by the simulation for emergency vehicle bypassing. Route details are not recorded in the current CSV.")

st.divider()
st.subheader("6. Raw Simulation Records")
st.dataframe(filtered,use_container_width=True)

csv=filtered.to_csv(index=False).encode("utf-8")
st.download_button(
    "Download Filtered Results",
    data=csv,
    file_name="traffic_analysis.csv",
    mime="text/csv"
)

st.caption("Intelligent Traffic Signal Agent | Simulation Analytics Dashboard")