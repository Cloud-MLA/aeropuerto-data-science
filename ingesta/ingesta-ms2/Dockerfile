FROM python:3.12-slim

WORKDIR /ingesta

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY ingesta.py .

ENTRYPOINT ["python", "ingesta.py"]