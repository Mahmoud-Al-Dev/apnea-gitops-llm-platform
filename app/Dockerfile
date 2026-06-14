FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000
EXPOSE 8501

# 🚀 USE PYTHON -M TO LOCATE MODULES
RUN printf "#!/bin/bash\n\
python -m uvicorn main:app --host 0.0.0.0 --port 8000 & \n\
python -m streamlit run dashboard.py --server.port 8501 --server.address 0.0.0.0 \n\
wait -n\n" > /app/start.sh

RUN chmod +x /app/start.sh

CMD ["/app/start.sh"]