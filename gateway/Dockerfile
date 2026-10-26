FROM python:3.13-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
COPY shared /app/shared
COPY gateway /app/gateway
RUN --mount=type=cache,target=/root/.cache/pip pip install /app/shared /app/gateway
CMD ["uvicorn", "gateway.main:create_gateway_app", "--factory", "--host", "0.0.0.0", "--port", "8000"]
