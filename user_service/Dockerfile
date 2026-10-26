FROM python:3.13-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
COPY shared /app/shared
COPY user_service /app/user_service
RUN --mount=type=cache,target=/root/.cache/pip pip install /app/shared /app/user_service
CMD ["uvicorn", "user_service.main:create_user_app", "--factory", "--host", "0.0.0.0", "--port", "8001"]
