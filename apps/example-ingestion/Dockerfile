# syntax=docker/dockerfile:1
#
# Lambda-compatible Docker build for example-ingestion (Bronze layer)
# See ADR-006 for containerization and ADR-018 for medallion architecture.
#
# Build context must be the repository root (not this directory)
# because libs/example-data is a local path dependency:
#   docker build -f apps/example-ingestion/Dockerfile .

# ── Stage 1: Builder ────────────────────────────────────────────────────────
FROM python:3.12-slim AS builder

RUN pip install --no-cache-dir poetry poetry-plugin-export

WORKDIR /build

# Copy the shared library (local path dependency)
COPY libs/example-data ./libs/example-data

# Copy application manifests before source code for Docker layer cache efficiency
COPY apps/example-ingestion/pyproject.toml apps/example-ingestion/poetry.lock \
     ./apps/example-ingestion/

# Export pinned runtime dependencies from the Poetry lock file.
RUN cd apps/example-ingestion \
    && poetry export \
       --without dev \
       --without-hashes \
       --format requirements.txt \
       --output /tmp/requirements.txt \
    && grep -vE "^(-e |example-data)" /tmp/requirements.txt \
       > /tmp/app-requirements.txt || true

# Pre-build wheels for reproducible, offline installation in the runtime stage
RUN pip wheel --no-cache-dir --wheel-dir /wheels -r /tmp/app-requirements.txt
RUN pip wheel --no-cache-dir --wheel-dir /wheels ./libs/example-data

# ── Stage 2: Lambda Runtime ─────────────────────────────────────────────────
FROM public.ecr.aws/lambda/python:3.12

COPY --from=builder /wheels /tmp/wheels
RUN pip install --no-cache-dir /tmp/wheels/*.whl && rm -rf /tmp/wheels

COPY apps/example-ingestion/app ${LAMBDA_TASK_ROOT}/app

CMD ["app.lambda_handler.handler"]
