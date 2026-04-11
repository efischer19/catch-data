# syntax=docker/dockerfile:1
#
# Lambda-compatible Docker build for example-app
# See ADR-006 for the containerization strategy and ADR-015 for AWS patterns.
#
# This Dockerfile produces a container image that can run as an AWS Lambda
# function. The build context must be the repository root (not this directory)
# because libs/example-lib is a local path dependency required at build time:
#   docker build -f apps/example-app/Dockerfile .

# ── Stage 1: Builder ────────────────────────────────────────────────────────
# Resolves dependencies and pre-builds wheels for reproducible installs.
FROM python:3.12-slim AS builder

RUN pip install --no-cache-dir poetry poetry-plugin-export

WORKDIR /build

# Copy the shared library (local path dependency)
COPY libs/example-lib ./libs/example-lib

# Copy application manifests before source code for Docker layer cache efficiency
COPY apps/example-app/pyproject.toml apps/example-app/poetry.lock \
     ./apps/example-app/

# Export pinned runtime dependencies from the Poetry lock file.
# The local path dependency (example-lib) is excluded and handled separately.
RUN cd apps/example-app \
    && poetry export \
       --without dev \
       --without-hashes \
       --format requirements.txt \
       --output /tmp/requirements.txt \
    && grep -vE "^(-e |example-lib)" /tmp/requirements.txt \
       > /tmp/app-requirements.txt || true

# Pre-build wheels for reproducible, offline installation in the runtime stage
RUN pip wheel --no-cache-dir --wheel-dir /wheels -r /tmp/app-requirements.txt
RUN pip wheel --no-cache-dir --wheel-dir /wheels ./libs/example-lib

# ── Stage 2: Lambda Runtime ─────────────────────────────────────────────────
# Uses the AWS Lambda Python base image for production deployment.
# See https://gallery.ecr.aws/lambda/python for available tags.
FROM public.ecr.aws/lambda/python:3.12

# Install pre-built wheels (no network access needed at this stage)
COPY --from=builder /wheels /tmp/wheels
RUN pip install --no-cache-dir /tmp/wheels/*.whl && rm -rf /tmp/wheels

# Copy application source code into the Lambda task root
COPY apps/example-app/app ${LAMBDA_TASK_ROOT}/app

# Lambda handler: module_path.function_name
# The handler function must accept (event, context) arguments.
# See app/lambda_handler.py for the implementation.
CMD ["app.lambda_handler.handler"]
