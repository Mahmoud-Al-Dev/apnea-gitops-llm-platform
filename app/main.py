import io
import os
from fastapi import FastAPI, UploadFile, File, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
import pandas as pd
from sqlalchemy.orm import Session
from qdrant_client import QdrantClient
from openai import OpenAI

from model import process_csv_and_predict
from database import engine, Base, get_db
import db_models

# Bootstrap database tables directly on container instantiation in EKS
Base.metadata.create_all(bind=engine)

app = FastAPI(title="Apnea Detection & Monitoring API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize RAG Clients (Using internal K8s DNS for Qdrant)
qdrant = QdrantClient(url="http://qdrant-service:6333")
llm_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

@app.post("/predict_csv")
async def predict_csv(file: UploadFile = File(...), db: Session = Depends(get_db)):
    if not file.filename.endswith(".csv"):
        raise HTTPException(status_code=400, detail="Only CSV files are allowed.")

    contents = await file.read()
    df = pd.read_csv(io.BytesIO(contents), header=None)
    df.columns = ["PFlow", "Thorax", "Abdomen", "SaO2", "Vitalog1", "Vitalog2", "time_sec"]

    try:
        # Run your core DPO PyTorch pipeline inference
        results = process_csv_and_predict(df)
        
        # 1. Ensure a default clinical testing patient profile exists
        patient = db.query(db_models.Patient).first()
        if not patient:
            patient = db_models.Patient(name="Default Testing Subject")
            db.add(patient)
            db.commit()
            db.refresh(patient)

        # 2. Extract metrics to commit to state management
        total_w = len(results)
        apnea_w = sum(1 for x in results if x.get("is_apnea", False))
        osa_w = sum(1 for x in results if x.get("predicted_class") == "OSA")
        ca_w = sum(1 for x in results if x.get("predicted_class") == "Central Apnea")
        normal_w = sum(1 for x in results if x.get("predicted_class") == "Normal")

        # --- NEW: RAG PIPELINE INTEGRATION ---
        # Search Qdrant for relevant medical context
        search_query = f"Patient has {osa_w} obstructive sleep apnea events and {ca_w} central apnea events. What is the clinical severity and scoring guideline?"
        
        query_vector = llm_client.embeddings.create(
            input=[search_query], 
            model="text-embedding-3-small"
        ).data[0].embedding

        search_result = qdrant.query_points(
            collection_name="clinical_guidelines",
            query=query_vector,
            limit=2 
        )
        
        # Extract the points from the response, then get the text
        hits = search_result.points
        retrieved_context = "\n".join([hit.payload.get("page_content", "") for hit in hits])

        # Prompt the LLM
        prompt = f"""
        You are an expert sleep medicine physician. 
        Patient Data: {osa_w} OSA events, {ca_w} CA events.
        Official AASM Guidelines: {retrieved_context}
        
        Write a brief, 3-sentence clinical summary of these findings based ONLY on the provided guidelines.
        """

        response = llm_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}]
        )

        clinical_summary = response.choices[0].message.content
        # -------------------------------------

        # 3. Store result to SQL database
        session_record = db_models.DiagnosticSession(
            patient_id=patient.id,
            filename=file.filename,
            total_windows=total_w,
            apnea_windows=apnea_w,
            osa_windows=osa_w,
            ca_windows=ca_w,
            normal_windows=normal_w
        )
        db.add(session_record)
        db.commit()

        # Return the summary alongside the raw predictions
        return {
            "filename": file.filename, 
            "predictions": results,
            "clinical_summary": clinical_summary
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/history")
def get_diagnostic_history(db: Session = Depends(get_db)):
    records = db.query(db_models.DiagnosticSession).order_by(db_models.DiagnosticSession.created_at.desc()).all()
    return [
        {
            "id": r.id,
            "filename": r.filename,
            "total_windows": r.total_windows,
            "apnea_windows": r.apnea_windows,
            "osa_windows": r.osa_windows,
            "ca_windows": r.ca_windows,
            "normal_windows": r.normal_windows,
            "date": r.created_at.strftime("%Y-%m-%d %H:%M:%S")
        } for r in records
    ]