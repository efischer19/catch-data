---
title: "ADR-019: CloudFront + OAC for Gold Layer Public Access"
status: "Accepted"
date: "2026-04-30"
tags:
  - "infrastructure"
  - "cloudfront"
  - "cdn"
  - "s3"
  - "security"
---

## Context

* **Problem:** The Gold layer JSON files produced by `catch-analytics`
  (see [ADR-018](ADR-018-medallion_architecture.md)) must be served to
  the catch-app frontend with low latency, global availability, and
  without exposing the S3 bucket directly to the public internet.
* **Constraints:**
  * The S3 bucket must remain private — no direct public access.
  * CORS headers must allow requests only from known catch-app origins.
  * Cost must remain minimal (target: < $5/month at expected traffic).
  * Infrastructure must be defined in Terraform
    (see [ADR-016](ADR-016-terraform_iac.md)) on AWS
    (see [ADR-015](ADR-015-aws_cloud_provider.md)).

## Decision

We will use **AWS CloudFront** with an **Origin Access Control (OAC)**
policy to serve Gold layer JSON files from S3 to the catch-app frontend.

### Key Design Choices

| Concern | Decision |
| :--- | :--- |
| S3 access model | OAC (Origin Access Control) — CloudFront-only, no direct public S3 access |
| Cache TTL | 1 hour (`default_ttl = max_ttl = 3600 s`) |
| HTTPS | Redirect HTTP → HTTPS; `viewer_protocol_policy = "redirect-to-https"` |
| Price class | `PriceClass_100` — US, Canada, and Europe edge nodes only |
| Compression | CloudFront Gzip + Brotli compression enabled (`compress = true`) |
| CORS | Response Headers Policy scoped to `var.cors_allowed_origins` |
| Custom domain | Optional — configurable via `cloudfront_custom_domain` + `acm_certificate_arn` |
| Cache invalidation | Gold Lambda calls `cloudfront:CreateInvalidation` after successful write |

### Security Model

1. **S3 bucket remains private.** `aws_s3_bucket_public_access_block`
   blocks all public access. The bucket policy grants only
   `s3:GetObject` on `gold/*` to `cloudfront.amazonaws.com`, scoped
   to the specific distribution ARN via `aws:SourceArn`.
2. **OAC signs requests.** CloudFront uses SigV4 signing when
   requesting objects from S3, so S3 can authenticate that requests
   come from the authorised distribution.
3. **CORS is enforced at the CDN edge.** The CloudFront response
   headers policy injects `Access-Control-Allow-Origin` for approved
   domains; the S3 bucket's own CORS configuration is unchanged.

### Cache Invalidation

When `catch-analytics` writes new Gold files, it calls
`cloudfront:CreateInvalidation` to purge stale CDN cache entries.
This ensures the frontend sees fresh data within minutes of the
nightly pipeline run. The Lambda execution role is granted
`cloudfront:CreateInvalidation` only on the specific distribution ARN
(`aws_iam_role_policy.analytics_cloudfront_invalidation`).

### Cost Model (PriceClass_100)

* Data transfer: $0.085/GB · ~1 GB/month ≈ **$0.09/month**
* Requests: $0.0075 per 10 k HTTPS requests · ~90 k/month ≈ **$0.07/month**
* Total estimate: **~$2/year** (well within the free tier for the
  first 12 months: 1 TB data transfer + 10 M requests/month).

## Considered Options

1. **CloudFront + OAC (Chosen):** CDN in front of private S3 with
   signed requests.
   * *Pros:* Industry-recommended AWS security pattern. Global edge
     caching yields sub-100 ms response times for US users. JSON files
     (50–150 KB) are highly compressible, reducing transfer costs.
     Cache invalidation integrates with the existing Gold Lambda.
   * *Cons:* Adds a CloudFront distribution resource to manage.
     Cache invalidation adds a small amount of pipeline complexity.
2. **S3 Static Website Hosting with public bucket:** Enable public
   access directly on the S3 bucket.
   * *Pros:* Simpler — no CloudFront configuration required.
   * *Cons:* Exposes raw S3 URLs, no CDN caching, no HTTPS (S3
     website endpoints are HTTP only), violates the project's
     security requirement to keep the bucket private.
3. **CloudFront + OAI (Origin Access Identity, legacy):** Older
   CloudFront + S3 integration pattern.
   * *Pros:* Familiar to operators who set it up before OAC existed.
   * *Cons:* OAC is the current AWS recommendation; OAI is legacy
     and lacks support for certain AWS features. OAC uses SigV4 and
     is more secure.

## Consequences

* **Positive:** Gold layer files are served from CloudFront edge
  locations, dramatically reducing latency for end users. The S3
  bucket stays private — only CloudFront can read Gold data. CORS is
  handled centrally in the CDN layer, not per-origin in S3.
* **Negative:** Terraform `apply` now deploys a CloudFront
  distribution, which can take 5–15 minutes to propagate globally.
  Pipeline must call `CreateInvalidation` after each Gold write.
* **Future Implications:** Cache invalidation logic in `catch-analytics`
  (see `CLOUDFRONT_DISTRIBUTION_ID` env var) should remain
  coordinated with this infrastructure. If a custom domain is
  configured later, the ACM certificate must be issued in `us-east-1`
  regardless of the bucket/Lambda region (CloudFront requirement).
