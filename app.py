import streamlit as st
from datetime import datetime, timedelta
import pandas as pd
from openai import OpenAI

st.set_page_config(layout="wide", page_title="Activity Progress")

# GSHEET connection
@st.cache_resource
def init_gsheets():
    
    creds_dict = json.loads(st.secrets["GCP_CREDENTIALS"])
   
    client = gspread.service_account_from_dict(creds_dict)
    
    sheet = client.open_by_url(st.secrets["SHEET_URL"]).sheet1
    return sheet

# Database
try:
    sheet = init_gsheets()
except Exception as e:
    st.error("Could not connect to Google Sheets. Check your Secrets.")
    st.stop()

load_user_data(name):
    records = sheet.get_all_records()
    for row in records:
        if row["Name"] == name:
            
            return {
                "timezone": int(row["Timezone"]),
                "tasks": json.loads(row["Tasks"]),
                "streak_data": json.loads(row["Streak"])
            }
    
    return {
        "timezone": 7,
        "tasks": {},
        "streak_data": {}
    }

def save_user_data(name, tz, tasks, streak):
    records = sheet.get_all_records()
    
    tasks_text = json.dumps(tasks)
    streak_text = json.dumps(streak)
       
    for i, row in enumerate(records):
        if row["Name"] == name:
            
            sheet.update_cell(i + 2, 2, tz)
            sheet.update_cell(i + 2, 3, tasks_text)
            sheet.update_cell(i + 2, 4, streak_text)
            return
            
    sheet.append_row([name, tz, tasks_text, streak_text])

# Memory
if "chat_messages" not in st.session_state:
    st.session_state.chat_messages = []

st.sidebar.title("Menu")

users = ["User 1", "User 2", "User 3", "User 4", "User 5"]
selected_user = st.sidebar.selectbox("👤 Select Profile:", users)

if "current_user" not in st.session_state or st.session_state.current_user != selected_user:
    st.session_state.current_user = selected_user
    user_data = load_user_data(selected_user)
    
    st.session_state.timezone = user_data["timezone"]
    st.session_state.tasks = user_data["tasks"]
    st.session_state.streak_data = user_data["streak_data"]
    st.session_state.chat_messages = []

page = st.sidebar.radio("Go to", ["Tracker", "Settings"])
st.sidebar.divider()
st.sidebar.caption("Connected to Cloud Database")

# SETTINGS PAGE
if page == "Settings":
    st.title("Settings")
    
    st.subheader("Timezone Configuration")
    
    tz_options = {"WIB (UTC+7)": 7, "WITA (UTC+8)": 8, "WIT (UTC+9)": 9}
    
    selected_tz_name = st.selectbox("Select your local time:", list(tz_options.keys()))
    
    st.session_state.timezone = tz_options[selected_tz_name]
    st.success(f"Timezone updated successfully!")
    
# TRACKER PAGE
elif page == "Tracker":
    st.title("My Activity Tracker")
    
    now = datetime.utcnow() + timedelta(hours=st.session_state.timezone)
    
    minutes_in_day = 24 * 60
    current_minutes = (now.hour * 60) + now.minute
    day_progress = current_minutes / minutes_in_day
    
    minutes_in_week = 7 * 24 * 60
    current_week_minutes = (now.weekday() * 24 * 60) + current_minutes
    week_progress = current_week_minutes / minutes_in_week
    
    total_tasks = len(st.session_state.tasks)
    completed_tasks = sum(st.session_state.tasks.values())
    task_progress = completed_tasks / total_tasks if total_tasks > 0 else 0.0

    st.progress(task_progress, text=f"Task Progress ({completed_tasks}/{total_tasks})")
    st.progress(day_progress, text=f"Day Progression - Current Time: {now.strftime('%H:%M')}")
    st.progress(week_progress, text="Week Progression")
    
    st.divider()

    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Tasks")
        
        for task, is_done in st.session_state.tasks.items():
            
            st.session_state.tasks[task] = st.checkbox(task, value=is_done)
            
        new_task = st.text_input("Add a new task...")
        if st.button("Add Task") and new_task:
            st.session_state.tasks[new_task] = False
            st.rerun() 

    with col2:
        st.subheader("AI Consultant")
        
        chat_container = st.container(height=300)
        
        with chat_container:
            for message in st.session_state.chat_messages:
                with st.chat_message(message["role"]):
                    st.markdown(message["content"])
        
       
        if prompt := st.chat_input("Type Here to Start Consulting..."):
            
            st.session_state.chat_messages.append({"role": "user", "content": prompt})
            
            with chat_container:
                with st.chat_message("user"):
                    st.markdown(prompt)
                
                with st.chat_message("assistant"):
                    try:
                       
                        client = OpenAI(
                            api_key=st.secrets["GROQ_API_KEY"],
                            base_url="https://api.groq.com/openai/v1"
                        )
                        stream = client.chat.completions.create(
                            model="llama-3.1-8b-instant",
                            messages=st.session_state.chat_messages,
                            stream=True,
                        )
                        response = st.write_stream(stream)
                        st.session_state.chat_messages.append({"role": "assistant", "content": response})
                    except Exception as e:
                        st.error("Oops! API Key missing. Please check your secrets setup.")

    st.divider()

    st.subheader("Task Completion Graph (Per Day)")
    
    df = pd.DataFrame(
        list(st.session_state.streak_data.items()),
        columns=['Day', 'Tasks Completed']
    )
    df.set_index('Day', inplace=True)
    st.line_chart(df)
