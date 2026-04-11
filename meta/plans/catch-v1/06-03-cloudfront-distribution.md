# feat: Terraform CloudFront distribution for Gold layer public access

## What do you want to build?

Create a CloudFront CDN distribution that serves the Gold layer JSON files from
S3 to the catch-app frontend. This provides fast, cached, globally distributed
access to the UI-ready JSON files without exposing the S3 bucket directly to the
public internet.

## Acceptance Criteria

- [ ] A CloudFront distribution is defined in Terraform with an S3 origin pointing to the `gold/` prefix
- [ ] An Origin Access Control (OAC) policy restricts S3 access to CloudFront only — no direct S3 public access
- [ ] The S3 bucket policy is updated to allow `s3:GetObject` from the CloudFront distribution only, scoped to `gold/*`
- [ ] CORS headers are configured: `Access-Control-Allow-Origin` set to the catch-app domain(s)
- [ ] Cache behavior: TTL of 1 hour for Gold files (balance between freshness and caching)
- [ ] The distribution supports HTTPS only (redirect HTTP to HTTPS)
- [ ] A custom domain name and ACM certificate are configurable via Terraform variables (optional for V1)
- [ ] Price class is set to `PriceClass_100` (US/Canada/Europe only) to minimize cost
- [ ] CloudFront distribution tags: `Project=catch-data`, `Environment={env}`, `ManagedBy=terraform`
- [ ] All Terraform changes pass `terraform validate` and `terraform plan`

## Implementation Notes

**📝 ADR Consideration:**

- Propose an ADR documenting the decision to use CloudFront + OAC for Gold
  layer serving, including the CORS policy, cache strategy, and the security
  model (no direct S3 public access).

**🤑 FinOps Miser notes:**

- CloudFront pricing (PriceClass_100, US/Canada/Europe):
  - Data transfer: $0.085/GB for the first 10 TB. Catch's Gold layer is
    ~5 MB total. Even with 10,000 daily users, data transfer is <1 GB/month.
    Cost: ~$0.09/month.
  - Requests: $0.0075 per 10,000 HTTPS requests. At 10,000 users × 3
    requests/visit = 30,000 requests/day = ~$0.07/month.
  - Total CDN cost estimate: ~$2/year. Well within "low-cost" target.
- **Free tier note:** CloudFront includes 1 TB data transfer out and
  10,000,000 HTTP/HTTPS requests per month free for the first 12 months.
  This project will stay well under those limits indefinitely.

**⚡ PWA Performance Fanatic notes:**

- CloudFront edge caching ensures sub-100ms response times for US users.
  Gold JSON files are small (50-150 KB) and highly cacheable.
- Set `Cache-Control: public, max-age=3600` on Gold S3 objects so browsers
  also cache locally.
- Enable Gzip compression in CloudFront for JSON content types. This
  typically reduces Gold file sizes by 70-80%.

**🔧 Data Pipeline Janitor notes:**

- The OAC model ensures the S3 bucket remains private. Only CloudFront can
  read Gold files. This is the recommended AWS security pattern.
- Cache invalidation (triggered by the Gold Lambda, see ticket 05-03) ensures
  fresh data is available within minutes of the nightly pipeline run.

Terraform resources:

- `aws_cloudfront_distribution`
- `aws_cloudfront_origin_access_control`
- `aws_s3_bucket_policy` (update existing to allow CloudFront)
- `aws_acm_certificate` (optional, for custom domain)
- `aws_cloudfront_cache_policy` (custom TTL settings)

Reference ADR-015 (AWS), ADR-016 (Terraform).
