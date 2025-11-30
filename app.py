import streamlit as st
import database
import views

# --- SETUP ---
st.set_page_config(page_title="Meetly", page_icon="👋", layout="wide")
database.init_db()

# --- SESSION STATE INITIALIZATION ---
if 'ranked_results' not in st.session_state:
    st.session_state.ranked_results = None

if 'selected_events' not in st.session_state:
    st.session_state.selected_events = []

# --- NAVIGATION LOGIC ---
if "nav_page" not in st.session_state:
    st.session_state.nav_page = "Start"

if st.query_params.get("code"):
    st.session_state.nav_page = "Activity Planner"

# --- SIDEBAR ---
st.sidebar.title("Navigation")
page = st.sidebar.radio(
    "Go to", 
    ["Start", "Profiles", "Activity Planner", "Group Calendar"],
    key="nav_page"
)

# --- ROUTING ---
if page == "Start":
    views.show_start_page()

elif page == "Profiles":
    views.show_profiles_page()

elif page == "Activity Planner":
    views.show_activity_planner()

elif page == "Group Calendar":
    views.show_group_calendar()
