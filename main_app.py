import streamlit as st

from app.login import show_login
from app.dashboard import show_dashboard
from app.detect import show_detect_page
from app.history import show_history_page
from app.symptoms import show_symptoms_page
from app.recovery import show_recovery_page


# Page configuration
st.set_page_config(
    page_title="Millet Disease Detection System",
    page_icon="🌾",
    layout="wide",
    initial_sidebar_state="expanded"
)


# Session state initialization
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

if "username" not in st.session_state:
    st.session_state.username = ""


# LOGIN PAGE
if not st.session_state.logged_in:
    show_login()

# MAIN APPLICATION
else:

    st.sidebar.title("🌾 Millet Disease Detection")

    page = st.sidebar.radio(
        "Navigation",
        [
            "Dashboard",
            "Detect Disease",
            "History",
            "Symptoms",
            "Recovery",
            "Logout"
        ]
    )

    # DASHBOARD
    if page == "Dashboard":
        show_dashboard()

    # DETECT DISEASE
    elif page == "Detect Disease":
        show_detect_page()

    # HISTORY
    elif page == "History":
        show_history_page()

    # SYMPTOMS
    elif page == "Symptoms":
        show_symptoms_page()

    # RECOVERY
    elif page == "Recovery":
        show_recovery_page()

    # LOGOUT
    elif page == "Logout":
        st.session_state.logged_in = False
        st.session_state.username = ""
        st.rerun()