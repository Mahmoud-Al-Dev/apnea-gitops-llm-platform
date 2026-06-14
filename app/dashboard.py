import os
import requests
import pandas as pd
import streamlit as st
import plotly.graph_objects as go

st.set_page_config(page_title="RLHF Apnea Scorer", layout="wide")
st.title("🫁 Clinical Apnea Scorer AI")

API_URL = os.getenv("API_URL", "http://localhost:8000/predict_csv")

uploaded_file = st.file_uploader("Upload Patient Data (.csv)", type=["csv"])


def build_summary(pred_df: pd.DataFrame) -> dict:
    if pred_df.empty:
        return {
            "total_windows": 0,
            "apnea_windows": 0,
            "osa_windows": 0,
            "ca_windows": 0,
            "normal_windows": 0,
        }

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
        is_apnea = pred.get("is_apnea", False)

        if not is_apnea:
            continue

        if predicted_class == "OSA":
            fillcolor = "orange"
            label = "OSA"
        elif predicted_class == "Central Apnea":
            fillcolor = "red"
            label = "CA"
        else:
            fillcolor = "purple"
            label = predicted_class

        fig.add_vrect(
            x0=pred["start_time_sec"],
            x1=pred["end_time_sec"],
            fillcolor=fillcolor,
            opacity=0.25,
            layer="below",
            line_width=0,
            annotation_text=label,
            annotation_position="top left",
        )


if uploaded_file is not None:
    # Must match backend preprocessing order
    df = pd.read_csv(uploaded_file, header=None)
    df.columns = ["PFlow", "Thorax", "Abdomen", "SaO2", "Vitalog1", "Vitalog2", "time_sec"]

    st.write("### Raw Signal Preview")
    st.dataframe(df.head())

    if st.button("Run AI Inference", type="primary"):
        with st.spinner("Preprocessing signal, extracting features, and running dual-model inference..."):
            uploaded_file.seek(0)
            files = {"file": (uploaded_file.name, uploaded_file, "text/csv")}
            response = requests.post(API_URL, files=files)

            if response.status_code == 200:
                payload = response.json()
                predictions = payload.get("predictions", [])
                pred_df = pd.DataFrame(predictions)

                st.success(f"Analysis complete! Processed {len(predictions)} windows.")

                summary = build_summary(pred_df)

                c1, c2, c3, c4, c5 = st.columns(5)
                c1.metric("Total Windows", summary["total_windows"])
                c2.metric("Apnea Windows", summary["apnea_windows"])
                c3.metric("OSA Windows", summary["osa_windows"])
                c4.metric("CA Windows", summary["ca_windows"])
                c5.metric("Normal Windows", summary["normal_windows"])

                st.write("### Signal Analysis & Predicted Events")
                fig = go.Figure()

                # Show first 30 minutes of raw uploaded signal
                sample_df = df.head(256 * 60 * 30)

                fig.add_trace(
                    go.Scatter(
                        x=sample_df["time_sec"],
                        y=sample_df["PFlow"],
                        name="PFlow (Airflow)",
                        opacity=0.8,
                    )
                )

                fig.add_trace(
                    go.Scatter(
                        x=sample_df["time_sec"],
                        y=sample_df["SaO2"],
                        name="SaO2 (Oxygen)",
                        opacity=0.8,
                        yaxis="y2",
                    )
                )

                add_prediction_regions(fig, predictions)

                fig.update_layout(
                    xaxis_title="Time (Seconds)",
                    yaxis_title="Airflow (PFlow)",
                    yaxis2=dict(
                        title="Oxygen Saturation (SaO2)",
                        overlaying="y",
                        side="right",
                    ),
                    hovermode="x unified",
                    height=550,
                    legend=dict(orientation="h"),
                )

                st.plotly_chart(fig, use_container_width=True)

                if not pred_df.empty:
                    st.write("### Prediction Confidence Overview")

                    confidence_cols = [
                        col for col in ["confidence", "osa_confidence", "ca_confidence"]
                        if col in pred_df.columns
                    ]

                    if confidence_cols:
                        st.dataframe(pred_df[[
                            "window_index",
                            "start_time_sec",
                            "end_time_sec",
                            "predicted_class",
                            *confidence_cols,
                            "is_apnea",
                        ]])

                    st.write("### Class Distribution")
                    class_counts = (
                        pred_df["predicted_class"]
                        .value_counts(dropna=False)
                        .reset_index()
                    )
                    class_counts.columns = ["predicted_class", "count"]
                    st.bar_chart(class_counts.set_index("predicted_class"))

                    st.write("### Detailed Window Predictions")
                    st.dataframe(pred_df)
                else:
                    st.info("No prediction windows were returned by the API.")

            else:
                try:
                    error_payload = response.json()
                    detail = error_payload.get("detail", response.text)
                except Exception:
                    detail = response.text
 
                st.error(f"Error from API: {detail}")