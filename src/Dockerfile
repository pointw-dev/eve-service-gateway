FROM python:3.9-slim

ENV ES_API_PORT=80
EXPOSE 80

WORKDIR app
COPY eve-service-gateway/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY eve-service-gateway .

CMD ["python", "run.py"]
