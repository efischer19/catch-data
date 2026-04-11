#!/usr/bin/env bash
# scripts/ecr-helper.sh
#
# Helper script for common Amazon ECR operations.
# See ADR-015 (AWS as Cloud Provider) for context.
#
# Prerequisites:
#   - AWS CLI installed and configured
#   - Docker installed
#
# Usage:
#   ./scripts/ecr-helper.sh login              # Log in to ECR
#   ./scripts/ecr-helper.sh list [app-name]    # List images
#   ./scripts/ecr-helper.sh latest <app-name>  # Get latest image URI
#   ./scripts/ecr-helper.sh pull <app-name>    # Pull latest image
#   ./scripts/ecr-helper.sh help               # Show usage

set -euo pipefail

# Replace these placeholders with your real values.
ECR_REPOSITORY="{{PROJECT_NAME}}-prod"
AWS_REGION="{{AWS_REGION}}"

# ── Helpers ──────────────────────────────────────────────────────────────────

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log_info()    { echo -e "${BLUE}ℹ️  $1${NC}"; }
log_success() { echo -e "${GREEN}✅ $1${NC}"; }
log_warning() { echo -e "${YELLOW}⚠️  $1${NC}"; }
log_error()   { echo -e "${RED}❌ $1${NC}"; }

check_aws_cli() {
    if ! command -v aws &> /dev/null; then
        log_error "AWS CLI is not installed. Install it first."
        exit 1
    fi
    if ! aws sts get-caller-identity &> /dev/null; then
        log_error "AWS CLI is not configured or credentials are invalid."
        exit 1
    fi
    log_success "AWS CLI is configured"
}

# ── Commands ─────────────────────────────────────────────────────────────────

ecr_login() {
    log_info "Logging in to ECR..."
    aws ecr get-login-password --region "$AWS_REGION" | \
        docker login --username AWS --password-stdin \
        "$(aws sts get-caller-identity --query Account --output text).dkr.ecr.$AWS_REGION.amazonaws.com"
    log_success "Logged in to ECR"
}

list_images() {
    local app_filter="${1:-}"

    log_info "Listing images in ECR repository: $ECR_REPOSITORY"

    if [[ -n "$app_filter" ]]; then
        log_info "Filtering for application: $app_filter"
        aws ecr describe-images \
            --repository-name "$ECR_REPOSITORY" \
            --region "$AWS_REGION" \
            --query "imageDetails[?starts_with(imageTags[0], '${app_filter}-')].{Tags:imageTags,Pushed:imagePushedAt,Size:imageSizeInBytes}" \
            --output table
    else
        aws ecr describe-images \
            --repository-name "$ECR_REPOSITORY" \
            --region "$AWS_REGION" \
            --query "imageDetails[].{Tags:imageTags,Pushed:imagePushedAt,Size:imageSizeInBytes}" \
            --output table
    fi
}

get_latest_image() {
    local app_name="$1"

    log_info "Getting latest image for: $app_name"

    local registry
    registry="$(aws sts get-caller-identity --query Account --output text).dkr.ecr.$AWS_REGION.amazonaws.com"
    local image_tag
    image_tag=$(aws ecr describe-images \
        --repository-name "$ECR_REPOSITORY" \
        --region "$AWS_REGION" \
        --query "imageDetails[?contains(imageTags, '${app_name}-latest')].imageTags[0]" \
        --output text)

    if [[ "$image_tag" != "None" && -n "$image_tag" ]]; then
        echo "$registry/$ECR_REPOSITORY:$image_tag"
        log_success "Latest image: $image_tag"
    else
        log_error "No latest image found for $app_name"
        return 1
    fi
}

pull_image() {
    local app_name="$1"
    local tag="${2:-latest}"

    log_info "Pulling image: $app_name-$tag"
    ecr_login

    local registry
    registry="$(aws sts get-caller-identity --query Account --output text).dkr.ecr.$AWS_REGION.amazonaws.com"
    local full_image="$registry/$ECR_REPOSITORY:$app_name-$tag"

    if docker pull "$full_image"; then
        log_success "Pulled: $full_image"
    else
        log_error "Failed to pull image. Verify the image exists."
        return 1
    fi
}

repo_info() {
    log_info "ECR Repository Information"
    aws ecr describe-repositories \
        --repository-names "$ECR_REPOSITORY" \
        --region "$AWS_REGION" \
        --output table
}

usage() {
    cat <<EOF
ECR Helper Script
=================

Usage: $0 <command> [arguments]

Commands:
  login                  Log in to Amazon ECR
  list [app-name]        List images (optionally filter by app)
  latest <app-name>      Get the latest image URI for an app
  pull <app-name> [tag]  Pull an image (default tag: latest)
  info                   Show repository information
  help                   Show this help message

Examples:
  $0 login
  $0 list
  $0 list example-app
  $0 latest example-app
  $0 pull example-app
  $0 pull example-app abc123
EOF
}

# ── Main ─────────────────────────────────────────────────────────────────────

main() {
    if [[ $# -eq 0 ]]; then
        usage
        exit 1
    fi

    check_aws_cli

    case "$1" in
        login)   ecr_login ;;
        list)    list_images "${2:-}" ;;
        latest)
            if [[ $# -lt 2 ]]; then
                log_error "Provide an application name"
                echo "Usage: $0 latest <app-name>"
                exit 1
            fi
            get_latest_image "$2"
            ;;
        pull)
            if [[ $# -lt 2 ]]; then
                log_error "Provide an application name"
                echo "Usage: $0 pull <app-name> [tag]"
                exit 1
            fi
            pull_image "$2" "${3:-latest}"
            ;;
        info)         repo_info ;;
        help|--help|-h) usage ;;
        *)
            log_error "Unknown command: $1"
            usage
            exit 1
            ;;
    esac
}

main "$@"
