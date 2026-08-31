FROM docker:29-cli AS docker-cli

FROM python:3.12.8-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    EVALUATOR_BENCHMARK_ROOT=/app/benchmarks/python

COPY --from=docker-cli /usr/local/bin/docker /usr/local/bin/docker

WORKDIR /app
COPY services/evaluator/pyproject.toml /app/services/evaluator/pyproject.toml
COPY services/evaluator/src /app/services/evaluator/src
RUN pip install --no-cache-dir /app/services/evaluator

COPY benchmarks/python /app/benchmarks/python

EXPOSE 8000
CMD ["uvicorn", "ai_code_evaluator.api:app", "--host", "0.0.0.0", "--port", "8000"]
