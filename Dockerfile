FROM python:3.11-slim

WORKDIR /app

# Install system deps for building and faiss
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential git wget ca-certificates \
  && rm -rf /var/lib/apt/lists/*

COPY requirements.txt /app/requirements.txt
RUN python -m pip install --upgrade pip setuptools wheel
RUN pip install --no-cache-dir -r /app/requirements.txt

# copy project
COPY . /app

EXPOSE 8000

CMD ["uvicorn", "app.langserve_app:app", "--host", "0.0.0.0", "--port", "8000"]
