# syntax=docker/dockerfile:1
#
# Lambda-compatible Docker build for catch-processing (Silver layer)
# See ADR-006 for containerization and ADR-018 for medallion architecture.
#
# Build context must be the repository root (not this directory)
# because libs/catch-models is a local path dependency:
#   docker build -f apps/catch-processing/Dockerfile .

# ── Stage 1: Builder ────────────────────────────────────────────────────────
FROM python:3.12-slim AS builder

RUN pip install --no-cache-dir poetry poetry-plugin-export

WORKDIR /build

# Copy the shared library (local path dependency)
COPY libs/catch-models ./libs/catch-models

# Copy application manifests before source code for Docker layer cache efficiency
COPY apps/catch-processing/pyproject.toml apps/catch-processing/poetry.lock \
     ./apps/catch-processing/

# Export pinned runtime dependencies from the Poetry lock file.
RUN cd apps/catch-processing \
    && poetry export \
       --without dev \
       --without-hashes \
       --format requirements.txt \
       --output /tmp/requirements.txt \
    && grep -vE "^(-e |catch-models)" /tmp/requirements.txt \
       > /tmp/app-requirements.txt || true

# Pre-build wheels for reproducible, offline installation in the runtime stage
RUN pip wheel --no-cache-dir --wheel-dir /wheels -r /tmp/app-requirements.txt
RUN pip wheel --no-cache-dir --wheel-dir /wheels ./libs/catch-models

# ── Stage 2: Lambda Runtime ─────────────────────────────────────────────────
FROM public.ecr.aws/lambda/python:3.12

COPY --from=builder /wheels /tmp/wheels
RUN pip install --no-cache-dir /tmp/wheels/*.whl && rm -rf /tmp/wheels

COPY apps/catch-processing/app ${LAMBDA_TASK_ROOT}/app

CMD ["app.lambda_handler.handler"]
