FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .

RUN python -c "f=open('requirements.txt','rb');c=f.read();f.close();c=c.replace(b'\x00',b'');f=open('requirements.txt','wb');f.write(c);f.close()" && \
    python -m pip install --upgrade pip --root-user-action=ignore && \
    python -m pip install --no-cache-dir -r requirements.txt --root-user-action=ignore

COPY . .

EXPOSE 8000

CMD ["uvicorn", "src.interface.api:app", "--host", "0.0.0.0", "--port", "8000"]
