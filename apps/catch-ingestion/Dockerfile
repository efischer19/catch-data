# syntax=docker/dockerfile:1
#
# Lambda-compatible Docker build for catch-ingestion (Bronze layer)
# See ADR-006 for containerization and ADR-018 for medallion architecture.
#
# Build context must be the repository root (not this directory)
# because libs/catch-models is a local path dependency:
#   docker build -f apps/catch-ingestion/Dockerfile .

# ── Stage 1: Builder ────────────────────────────────────────────────────────
FROM python:3.12-slim AS builder

RUN pip install --no-cache-dir poetry poetry-plugin-export

WORKDIR /build

# Copy the shared library (local path dependency)
COPY libs/catch-models ./libs/catch-models

# Copy application manifests before source code for Docker layer cache efficiency
COPY apps/catch-ingestion/pyproject.toml apps/catch-ingestion/poetry.lock \
     ./apps/catch-ingestion/

# Export pinned runtime dependencies from the Poetry lock file.
RUN cd apps/catch-ingestion \
    && poetry export \
       --without dev \
       --without-hashes \
       --format requirements.txt \
       --output /tmp/requirements.txt \
    && grep -vE "^(-e |catch-models)" /tmp/requirements.txt \
       > /tmp/app-requirements.txt || true

# Pre-build wheels for reproducible, offline installation in the runtime stage
RUN pip wheel --no-cache-dir --wheel-dir /wheels -r /tmp/app-requirements.txt
RUN pip wheel --no-cache-dir --no-deps --wheel-dir /wheels ./libs/catch-models

# ── Stage 2: Lambda Runtime ─────────────────────────────────────────────────
FROM public.ecr.aws/lambda/python:3.12

COPY --from=builder /wheels /tmp/wheels
RUN pip install --no-cache-dir /tmp/wheels/*.whl && rm -rf /tmp/wheels

COPY apps/catch-ingestion/app ${LAMBDA_TASK_ROOT}/app

CMD ["app.lambda_handler.handler"]
