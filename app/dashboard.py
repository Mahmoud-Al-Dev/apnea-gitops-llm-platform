import streamlit as np
import streamlit as st
import requests
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime

# Configure the Streamlit page layout
st.set_page_config(
    page_title="Clinical Apnea Scorer AI & Data Platform",
    page_icon="🫁",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Hardcoded FastAPI backend URL inside the Kubernetes cluster service network
# (Or your external LoadBalancer URL depending on how your local environment routes traffic)
BACKEND_URL = "http://localhost:8000"

st.title("🫁 Clinical Apnea Scorer AI & Data Platform")

# ---------------------------------------------------------
# Sidebar Navigation & History Fetching
# ---------------------------------------------------------
st.sidebar.header("Navigation")
page = st.sidebar.radio("Go to", ["🚀 Run AI Inference", "📊 Patient Diagnostic Database"])

if page == "🚀 Run AI Inference":
    st.header("Upload Patient Data (.csv)")
    uploaded_file = st.file_uploader("Choose a sleep study CSV file", type=["csv"])

    if uploaded_file is not None:
        # Read a preview of the file locally for user reassurance
        try:
            preview_df = pd.read_csv(uploaded_file, nrows=5, header=None)
            preview_df.columns = ["PFlow", "Thorax", "Abdomen", "SaO2", "Vitalog1", "Vitalog2", "time_sec"]
            st.subheader("Raw Signal Preview")
            st.dataframe(preview_df)
            # Reset file pointer after reading preview
            uploaded_file.seek(0)
        except Exception as e:
            st.error(f"Error parsing preview: {str(e)}")

        if st.button("Run AI Inference", type="primary"):
            with st.spinner("Processing deep pipeline models and retrieving medical guidelines..."):
                try:
                    # Prepare the multi-part file payload for FastAPI
                    files = {"file": (uploaded_file.name, uploaded_file.getvalue(), "text/csv")}
                    response = requests.post(f"{BACKEND_URL}/predict_csv", files=files)
                    
                    if response.status_code == 200:
                        results = response.json()
                        predictions = results.get("predictions", [])
                        
                        # Calculate raw metric display values
                        total_w = len(predictions)
                        apnea_w = sum(1 for x in predictions if x.get("is_apnea", False))
                        osa_w = sum(1 for x in predictions if x.get("predicted_class") == "OSA")
                        ca_w = sum(1 for x in predictions if x.get("predicted_class") == "Central Apnea")
                        normal_w = sum(1 for x in predictions if x.get("predicted_class") == "Normal")

                        st.success(f"Analysis complete and saved to cloud database! Processed {total_w} windows.")

                        # Display Summary Cards
                        m_col1, m_col2, m_col3, m_col4, m_col5 = st.columns(5)
                        m_col1.metric("Total Windows", total_w)
                        m_col2.metric("Apnea Windows", apnea_w)
                        m_col3.metric("OSA Windows", osa_w)
                        m_col4.metric("CA Windows", ca_w)
                        m_col5.metric("Normal Windows", normal_w)

                        # ✨ NEW: Display the LLM Clinical Summary directly from the RAG Pipeline ✨
                        if "clinical_summary" in results:
                            st.markdown("---")
                            st.subheader("🤖 AI Clinical Diagnostic Summary (RAG)")
                            st.info(results["clinical_summary"])
                            st.markdown("---")

                        # Build the Interactive Plotly Chart
                        st.subheader("Interactive Signal & Prediction Timeline")
                        
                        # Reconstruct basic time indices for visualization
                        time_axis = [x for x in range(total_w)]
                        osa_series = [1 if x.get("predicted_class") == "OSA" else 0 for x in predictions]
                        ca_series = [1 if x.get("predicted_class") == "Central Apnea" else 0 for x in predictions]
                        
                        fig = go.Figure()
                        fig.add_trace(go.Scatter(x=time_axis, y=osa_series, name="OSA Detected", mode='lines+markers', line=dict(color='orange')))
                        fig.add_trace(go.Scatter(x=time_axis, y=ca_series, name="Central Apnea Detected", mode='lines+markers', line=dict(color='red')))
                        
                        fig.update_layout(
                            xaxis_title="Window Sequence Index (Epochs)",
                            yaxis_title="Detection State (Binary)",
                            yaxis=dict(tickvals=[0, 1], ticktext=["Normal", "Event Event"]),
                            height=400,
                            template="plotly_dark"
                        )
                        st.plotly_chart(fig, use_container_width=True)

                    else:
                        st.error(f"Error from API: {response.text}")
                except Exception as e:
                    st.error(f"Failed to connect to the backend server: {str(e)}")

elif page == "📊 Patient Diagnostic Database":
    st.header("📜 Automated Diagnostic Storage Log")
    st.caption("This table pulls historical clinical metrics saved automatically by the FastAPI backend on AWS EKS.")

    if st.button("Refresh Database Records"):
        st.rerun()

    try:
        history_response = requests.get(f"{BACKEND_URL}/history")
        if history_response.status_code == 200:
            history_data = history_response.json()
            if history_data:
                df_history = pd.DataFrame(history_data)
                # Reorder columns for clean visual representation
                df_history = df_history[["date", "id", "filename", "total_windows", "apnea_windows", "osa_windows", "ca_windows", "normal_windows"]]
                st.dataframe(df_history, use_container_width=True)
                
                # Historic Trends Chart
                st.subheader("📈 Historical Apnea Window Trends")
                trend_fig = go.Figure()
                trend_fig.add_trace(go.Scatter(x=df_history["date"], y=df_history["ca_windows"], name="ca_windows", mode='lines+markers'))
                trend_fig.add_trace(go.Scatter(x=df_history["date"], y=df_history["osa_windows"], name="osa_windows", mode='lines+markers'))
                trend_fig.update_layout(template="plotly_dark", height=350, margin=dict(l=20, r=20, t=20, b=20))
                st.plotly_chart(trend_fig, use_container_width=True)
            else:
                st.warning("No historical diagnostics found in the cloud database yet.")
        else:
            st.error(f"Could not load history. Status code: {history_response.status_code}")
    except Exception as e:
        st.error(f"Could not connect to history endpoint: {str(e)}")