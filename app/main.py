from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import pandas as pd
import io
from model import process_csv_and_predict
from prometheus_fastapi_instrumentator import Instrumentator

app = FastAPI(title="Apnea Detection API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

Instrumentator().instrument(app).expose(app)

@app.post("/predict_csv")
async def predict_csv(file: UploadFile = File(...)):
    if not file.filename.endswith(".csv"):
        raise HTTPException(status_code=400, detail="Only CSV files are allowed.")

    contents = await file.read()
    df = pd.read_csv(io.BytesIO(contents), header=None)
    df.columns = ["PFlow", "Thorax", "Abdomen", "SaO2", "Vitalog1", "Vitalog2", "time_sec"]

    try:
        results = process_csv_and_predict(df)
        return {"filename": file.filename, "predictions": results}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))