import os
import requests
import pandas as pd
import streamlit as st
import plotly.graph_objects as go

st.set_page_config(page_title="RLHF Apnea Scorer Cluster", layout="wide")
st.title("🫁 Clinical Apnea Scorer AI & Data Platform")

# Dynamic backend resolution values
API_BASE = os.getenv("API_URL", "http://localhost:8000").rstrip("/predict_csv")
PREDICT_URL = f"{API_BASE}/predict_csv"
HISTORY_URL = f"{API_BASE}/history"

# Split UI logically between production processing and data management
tab_inference, tab_history = st.tabs(["🚀 Run AI Inference", "📊 Patient Diagnostic Database"])

def build_summary(pred_df: pd.DataFrame) -> dict:
    if pred_df.empty:
        return {"total_windows": 0, "apnea_windows": 0, "osa_windows": 0, "ca_windows": 0, "normal_windows": 0}
    predicted_series = pred_df["predicted_class"].fillna("Unknown")
    return {
        "total_windows": len(pred_df),
        "apnea_windows": int(pred_df["is_apnea"].sum()) if "is_apnea" in pred_df.columns else 0,
        "osa_windows": int((predicted_series == "OSA").sum()),
        "ca_windows": int((predicted_series == "Central Apnea").sum()),
        "normal_windows": int((predicted_series == "Normal").sum()),
    }

def add_prediction_regions(fig: go.Figure, predictions: list):
    for pred in predictions:
        predicted_class = pred.get("predicted_class", "Unknown")
        if not pred.get("is_apnea", False):
            continue
        fillcolor = "orange" if predicted_class == "OSA" else ("red" if predicted_class == "Central Apnea" else "purple")
        fig.add_vrect(
            x0=pred["start_time_sec"], x1=pred["end_time_sec"],
            fillcolor=fillcolor, opacity=0.25, layer="below", line_width=0,
            annotation_text="OSA" if predicted_class == "OSA" else "CA",
            annotation_position="top left",
        )

# -------------------------------------------------------------
# TAB 1: RUN INFERENCE PIPELINE
# -------------------------------------------------------------
with tab_inference:
    uploaded_file = st.file_uploader("Upload Patient Data (.csv)", type=["csv"])
    
    if uploaded_file is not None:
        df = pd.read_csv(uploaded_file, header=None)
        df.columns = ["PFlow", "Thorax", "Abdomen", "SaO2", "Vitalog1", "Vitalog2", "time_sec"]

        st.write("### Raw Signal Preview")
        st.dataframe(df.head())

        if st.button("Run AI Inference", type="primary"):
            with st.spinner("Executing DPO-aligned Bi-LSTM prediction engine..."):
                uploaded_file.seek(0)
                files = {"file": (uploaded_file.name, uploaded_file, "text/csv")}
                response = requests.post(PREDICT_URL, files=files)

                if response.status_code == 200:
                    payload = response.json()
                    predictions = payload.get("predictions", [])
                    pred_df = pd.DataFrame(predictions)

                    st.success(f"Analysis complete and saved to cloud database! Processed {len(predictions)} windows.")

                    summary = build_summary(pred_df)
                    c1, c2, c3, c4, c5 = st.columns(5)
                    c1.metric("Total Windows", summary["total_windows"])
                    c2.metric("Apnea Windows", summary["apnea_windows"])
                    c3.metric("OSA Windows", summary["osa_windows"])
                    c4.metric("CA Windows", summary["ca_windows"])
                    c5.metric("Normal Windows", summary["normal_windows"])

                    fig = go.Figure()
                    sample_df = df.head(256 * 60 * 30)
                    fig.add_trace(go.Scatter(x=sample_df["time_sec"], y=sample_df["PFlow"], name="PFlow (Airflow)", opacity=0.8))
                    fig.add_trace(go.Scatter(x=sample_df["time_sec"], y=sample_df["SaO2"], name="SaO2 (Oxygen)", opacity=0.8, yaxis="y2"))
                    add_prediction_regions(fig, predictions)

                    fig.update_layout(
                        xaxis_title="Time (Seconds)", yaxis_title="Airflow (PFlow)",
                        yaxis2=dict(title="Oxygen Saturation (SaO2)", overlaying="y", side="right"),
                        hovermode="x unified", height=550, legend=dict(orientation="h")
                    )
                    st.plotly_chart(fig, use_container_width=True)
                else:
                    st.error(f"Error from API: {response.text}")

# -------------------------------------------------------------
# TAB 2: HISTORICAL PATIENT DATABASE
# -------------------------------------------------------------
with tab_history:
    st.write("### 📜 Automated Diagnostic Storage Log")
    st.info("This table pulls historical clinical metrics saved automatically by the FastAPI backend on AWS EKS.")
    
    if st.button("🔄 Refresh Database Records"):
        try:
            res = requests.get(HISTORY_URL)
            if res.status_code == 200:
                history_data = res.json()
                if history_data:
                    history_df = pd.DataFrame(history_data)
                    # Reordering for clear clinical visibility
                    history_df = history_df[["date", "id", "filename", "total_windows", "apnea_windows", "osa_windows", "ca_windows", "normal_windows"]]
                    st.dataframe(history_df, use_container_width=True)
                    
                    # Trend chart of past metrics
                    st.write("### 📈 Historical Apnea Window Trends")
                    st.line_chart(history_df.set_index("date")[["osa_windows", "ca_windows"]])
                else:
                    st.info("Database is connected but empty. Run inference to generate records.")
            else:
                st.error(f"Could not reach database tracking logs: {res.text}")
        except Exception as e:
            st.error(f"Network Connection Error: {str(e)}")