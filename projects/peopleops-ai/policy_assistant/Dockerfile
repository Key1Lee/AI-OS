FROM python:3.12-slim@sha256:a6e34c598f2467ed0e9a8d349809fcd8b5c603269512df273a0bb1784edc11b1
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir --require-hashes -r requirements.txt && useradd --uid 10001 --create-home app
COPY app app
COPY policies policies
COPY scripts scripts
COPY tests tests
COPY n8n n8n
COPY config config
COPY mock_data mock_data
COPY requirements requirements
COPY evals evals
COPY pyproject.toml .
USER app
CMD ["uvicorn", "app.api:app", "--host", "0.0.0.0", "--port", "8810", "--no-access-log"]
