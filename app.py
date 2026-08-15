import streamlit as st
import pandas as pd
import plotly.express as px
from google import genai
import os
from dotenv import load_dotenv

from src.database import (
    create_tables,
    save_schedule,
    get_schedules,
    delete_schedule
)

st.set_page_config(
    page_title="Digital Life-OS",
    page_icon="📱",
    layout="wide"
)

create_tables()

load_dotenv()

api_key = os.getenv("GEMINI_API_KEY")

if api_key:
    client = genai.Client(api_key=api_key)

data = pd.read_csv("data/screentime.csv")
data["Date"] = pd.to_datetime(data["Date"])

st.title("📱 Digital Life-OS")
st.subheader("AI-Powered Digital Wellbeing Tracker")

st.write(
    "Understand your digital habits, manage app schedules, "
    "and receive personalized wellbeing recommendations."
)

st.divider()

selected_date = st.date_input(
    "📅 Select Date",
    value=data["Date"].max().date()
)

day_data = data[data["Date"].dt.date == selected_date]

total_minutes = day_data["Duration_Minutes"].sum()
daily_goal = 300
difference = total_minutes - daily_goal

if not day_data.empty:
    most_used_app = day_data.loc[
        day_data["Duration_Minutes"].idxmax(),
        "App"
    ]
else:
    most_used_app = "No data"

total_hours = total_minutes // 60
remaining_minutes = total_minutes % 60

col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric(
        "📱 Screen Time",
        f"{total_hours}h {remaining_minutes}m"
    )

with col2:
    st.metric(
        "🎯 Daily Goal",
        "5h"
    )

with col3:
    st.metric(
        "📊 Goal Difference",
        f"{difference} min",
        delta=f"{difference} min"
    )

with col4:
    st.metric(
        "🔥 Most Used App",
        most_used_app
    )

st.divider()

st.header("📊 Today's App Usage")

if not day_data.empty:
    st.write(
        "Apps found in CSV:", 
        day_data["App"].unique().tolist()
    )
    fig = px.bar(
        day_data,
        x="App",
        y="Duration_Minutes",
        color="Category",
        title=f"App Usage on {selected_date}"
    )

    fig.update_layout(
        xaxis_title="Application",
        yaxis_title="Minutes Used"
    )

    st.plotly_chart(
        fig,
        use_container_width=True
    )
else:
    st.warning("No screen-time data available for this date.")

st.header("📈 Usage by Category")

if not day_data.empty:
    category_data = (
        day_data.groupby("Category")["Duration_Minutes"]
        .sum()
        .reset_index()
    )

    fig_category = px.pie(
        category_data,
        names="Category",
        values="Duration_Minutes",
        title="Screen Time Distribution"
    )

    st.plotly_chart(
        fig_category,
        use_container_width=True
    )

st.header("📋 Today's Activity")

st.dataframe(
    day_data,
    use_container_width=True,
    hide_index=True
)

st.header("📈 7-Day Screen-Time Trend")

daily_usage = (
    data.groupby("Date")["Duration_Minutes"]
    .sum()
    .reset_index()
    .sort_values("Date")
    .tail(7)
)

fig_trend = px.line(
    daily_usage,
    x="Date",
    y="Duration_Minutes",
    markers=True,
    title="Last 7 Days"
)

fig_trend.update_layout(
    xaxis_title="Date",
    yaxis_title="Minutes"
)

st.plotly_chart(
    fig_trend,
    use_container_width=True
)

st.header("⏰ Smart App Schedule")

with st.form("schedule_form"):
    col1, col2, col3 = st.columns(3)

    with col1:
        available_apps = sorted(data["App"].dropna().unique().tolist())

        with col1:
            app_name = st.selectbox(
             "Select App",
             available_apps
            )

    with col2:
        start_time = st.time_input("Allowed From")

    with col3:
        end_time = st.time_input("Allowed Until")

    submitted = st.form_submit_button("💾 Save Schedule")

if submitted:
    if start_time == end_time:
        st.error("Start and end time cannot be the same.")
    else:
        save_schedule(
            app_name,
            start_time.strftime("%H:%M"),
            end_time.strftime("%H:%M")
        )

        st.success(
            f"{app_name} is scheduled from "
            f"{start_time.strftime('%I:%M %p')} to "
            f"{end_time.strftime('%I:%M %p')}."
        )

schedules = get_schedules()

if schedules:
    st.subheader("📋 Saved Schedules")

    schedule_data = pd.DataFrame(
        schedules,
        columns=["ID", "App", "Start", "End"]
    )

    schedule_display = schedule_data.copy()

    schedule_display["Start"] = pd.to_datetime(
        schedule_display["Start"],
        format="%H:%M"
    ).dt.strftime("%I:%M %p")

    schedule_display["End"] = pd.to_datetime(
        schedule_display["End"],
        format="%H:%M"
    ).dt.strftime("%I:%M %p")

    st.dataframe(
        schedule_display,
        use_container_width=True,
        hide_index=True
    )

    st.subheader("🗑️ Remove Schedule")

    schedule_options = {
        f"{row[1]} ({row[2]} - {row[3]})": row[0]
        for row in schedules
    }

    selected_schedule = st.selectbox(
        "Select schedule to remove",
        list(schedule_options.keys())
    )

    if st.button("Delete Schedule"):
        delete_schedule(
            schedule_options[selected_schedule]
        )

        st.success("Schedule deleted.")
        st.rerun()
st.subheader("📊 Schedule Compliance")

if schedules:
    compliance_results = []

    for schedule in schedules:
        app_data = day_data[
            day_data["App"] == schedule[1]
        ]

        allowed_start = pd.to_datetime(
            schedule[2],
            format="%H:%M"
        ).time()

        allowed_end = pd.to_datetime(
            schedule[3],
            format="%H:%M"
        ).time()

        total_usage = 0
        allowed_usage = 0
        outside_usage = 0

        for _, row in app_data.iterrows():
            actual_start = pd.to_datetime(
                row["Start_Time"]
            ).time()

            actual_end = pd.to_datetime(
                row["End_Time"]
            ).time()

            duration = int(row["Duration_Minutes"])

            start_minutes = (
                actual_start.hour * 60
                + actual_start.minute
            )

            end_minutes = (
                actual_end.hour * 60
                + actual_end.minute
            )

            allowed_start_minutes = (
                allowed_start.hour * 60
                + allowed_start.minute
            )

            allowed_end_minutes = (
                allowed_end.hour * 60
                + allowed_end.minute
            )

            overlap_start = max(
                start_minutes,
                allowed_start_minutes
            )

            overlap_end = min(
                end_minutes,
                allowed_end_minutes
            )

            if overlap_end > overlap_start:
                within_minutes = min(
                    overlap_end - overlap_start,
                    duration
                )
            else:
                within_minutes = 0

            total_usage += duration
            allowed_usage += within_minutes
            outside_usage += duration - within_minutes

        if total_usage > 0:
            compliance = (
                allowed_usage / total_usage
            ) * 100
        else:
            compliance = 100

        compliance_results.append({
            "App": schedule[1],
            "Allowed Time": (
                f"{allowed_start.strftime('%I:%M %p')} - "
                f"{allowed_end.strftime('%I:%M %p')}"
            ),
            "Total Usage": f"{total_usage} min",
            "Within Schedule": f"{allowed_usage} min",
            "Outside Schedule": f"{outside_usage} min",
            "Compliance": f"{compliance:.1f}%"
        })

    compliance_df = pd.DataFrame(
        compliance_results
    )

    st.dataframe(
        compliance_df,
        use_container_width=True,
        hide_index=True
    )
st.header("🧠 Usage Patterns")

if not day_data.empty:
    peak_app = (
        day_data.groupby("App")["Duration_Minutes"]
        .sum()
        .sort_values(ascending=False)
        .index[0]
    )

    peak_app_minutes = (
        day_data.groupby("App")["Duration_Minutes"]
        .sum()
        .max()
    )

    average_daily_usage = (
        data.groupby("Date")["Duration_Minutes"]
        .sum()
        .mean()
    )

    most_active_day = (
        data.groupby("Date")["Duration_Minutes"]
        .sum()
        .idxmax()
    )

    pattern_col1, pattern_col2, pattern_col3 = st.columns(3)

    with pattern_col1:
        st.metric(
            "🔥 Highest Usage App",
            peak_app,
            f"{peak_app_minutes} min"
        )

    with pattern_col2:
        st.metric(
            "📊 Average Daily Usage",
            f"{average_daily_usage:.0f} min"
        )

    with pattern_col3:
        st.metric(
            "📅 Highest Usage Day",
            most_active_day.strftime("%d %b %Y")
        )

    st.subheader("💡 Today's Pattern")

    if total_minutes > daily_goal:
        st.warning(
            f"Your usage is {difference} minutes above "
            "your current daily goal."
        )
    else:
        remaining = daily_goal - total_minutes
        st.success(
            f"You are {remaining} minutes within "
            "your current daily goal."
        )

    st.write(
        f"Your highest-usage app today is **{peak_app}** "
        f"with **{peak_app_minutes} minutes** of usage."
    )
else:
    st.info("No usage data available for pattern analysis.")
st.header("🤖 AI Wellbeing Coach")

if api_key:
    if st.button("✨ Analyze My Digital Habits"):

        prompt = f"""
You are a digital wellbeing assistant.

Analyze the user's digital usage data.

Today's screen time: {total_minutes} minutes
Daily goal: {daily_goal} minutes
Goal difference: {difference} minutes
Most used app: {most_used_app}
Average daily usage: {average_daily_usage:.0f} minutes
Highest usage app today: {peak_app}
Highest usage app minutes: {peak_app_minutes} minutes

Give a concise analysis with:

1. 📊 Usage Summary
2. 🔍 Important Pattern
3. 💡 Personalized Recommendation
4. 🎯 One realistic goal for tomorrow

Do not diagnose addiction or mental health conditions.
Give practical and supportive digital wellbeing advice.
"""

        with st.spinner("Analyzing your digital habits..."):

            response = client.models.generate_content(
                model="gemini-3.1-flash-lite",
                contents=prompt
            )

        st.markdown(response.text)

else:
    st.error(
        "Gemini API key not found. "
        "Please check your .env file."
    )
