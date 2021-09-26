FROM python:3-alpine

RUN pip install requests

COPY logos.py /app.py

ENTRYPOINT ["python", "/app.py", "8080", "/data"]
