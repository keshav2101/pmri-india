FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
RUN python data/generate_demo_data.py
CMD ["python", "train.py", "--artifacts-dir", "/app/artifacts"]
