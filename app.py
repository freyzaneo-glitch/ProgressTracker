import streamlit as st
from datetime import datetime, timedelta
import pandas as pd
from openai import OpenAI


st.set_page_config(layout="wide", page_title="Activity Progress")

if "timezone" not in st.session_state:
    st.session_state.timezone = 7 
if "tasks" not in st.session_state:
    
    st.session_state.tasks = {"Type the task 1": False, "Type the task 2": False, "Type the task 3": False}
if "chat_messages" not in st.session_state:
    st.session_state.chat_messages = []
if "streak_data" not in st.session_state:
    
    st.session_state.streak_data = {"Monday": 1, "Tuesday": 2, "Wednesday": 4, "Thursday": 5, "Friday": 4}


st.sidebar.title("Menu")

page = st.sidebar.radio("Go to", ["Tracker", "Settings"])


# SETTINGS PAGE
if page == "Settings":
    st.title("Settings")
    
    st.subheader("Timezone Configuration")
    
    tz_options = {"WIB (UTC+7)": 7, "WITA (UTC+8)": 8, "WIT (UTC+9)": 9}
    
    selected_tz_name = st.selectbox("Select your local time:", list(tz_options.keys()))
    
    st.session_state.timezone = tz_options[selected_tz_name]
    st.success(f"Timezone updated successfully!")
    
    st.divider()
    
    st.subheader("Dark Mode")
    st.info("Streamlit handles Dark Mode automatically based on your computer's system theme! If you want to force it, click the three dots (⋮) in the top right corner of the page > Settings > Theme > Dark.")



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
    st.progress(day_progress, text=f"Time Left (Day) - Current Time: {now.strftime('%H:%M')}")
    st.progress(week_progress, text="Time Left (Week)")
    
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
        
       
        if prompt := st.chat_input("Type to Start Consulting..."):
            
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

   
    st.subheader("Task Completion Graph")
    
    df = pd.DataFrame(
        list(st.session_state.streak_data.items()),
        columns=['Day', 'Tasks Completed']
    )
    df.set_index('Day', inplace=True)
    st.line_chart(df)