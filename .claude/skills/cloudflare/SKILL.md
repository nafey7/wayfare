---
name: cloudflare
description: Manage CloudFlare for myvoya.ai - DNS records, analytics, cache purge, page rules, firewall events, zone settings. Use when user asks about CloudFlare, DNS, CDN, caching, traffic analytics, security events, or WAF.
allowed-tools: Bash, Read, Grep, Glob
argument-hint: [operation] [details]
---

# /cloudflare - CloudFlare Management for myvoya.ai

Manage DNS, analytics, cache, security, and zone settings for `myvoya.ai` via the CloudFlare API.

## Usage

```
/cloudflare                        # Show current status overview
/cloudflare dns                    # List DNS records
/cloudflare analytics [days]       # Traffic analytics (default: 7 days)
/cloudflare security [days]        # Firewall/WAF events
/cloudflare cache purge            # Purge entire cache
/cloudflare cache purge <urls>     # Purge specific URLs
/cloudflare page-rules             # List page rules
/cloudflare settings               # Show zone settings
/cloudflare <free-form question>   # Ask anything about the CloudFlare setup
```

## Configuration

**Zone:** `myvoya.ai`
**Zone ID:** `3242656176f9b361198648a7131f8a11`
**API Token:** `.local/secrets/cloudflare_token`
**Token Permissions:** Read-only by default (see `tools/README.md` for setup)
**Documentation:** `.local/docs/CLOUDFLARE.md`

## Authentication Setup

All API calls use Bearer token authentication:

```bash
CF_TOKEN=$(cat .local/secrets/cloudflare_token)
ZONE_ID="3242656176f9b361198648a7131f8a11"
```

Always read the token from file. Never hardcode it.

## Operations Reference

### DNS Records

```bash
# List all DNS records
curl -s "https://api.cloudflare.com/client/v4/zones/$ZONE_ID/dns_records?per_page=100" \
  -H "Authorization: Bearer $CF_TOKEN" | jq '.result[] | {id, name, type, content, proxied, ttl}'

# Get specific record
curl -s "https://api.cloudflare.com/client/v4/zones/$ZONE_ID/dns_records?name=app.myvoya.ai" \
  -H "Authorization: Bearer $CF_TOKEN" | jq '.result[]'

# Create CNAME record
curl -s -X POST "https://api.cloudflare.com/client/v4/zones/$ZONE_ID/dns_records" \
  -H "Authorization: Bearer $CF_TOKEN" -H "Content-Type: application/json" \
  -d '{"type":"CNAME","name":"subdomain","content":"target.example.com","proxied":true}'

# Update record (PUT = full replace)
curl -s -X PUT "https://api.cloudflare.com/client/v4/zones/$ZONE_ID/dns_records/{record_id}" \
  -H "Authorization: Bearer $CF_TOKEN" -H "Content-Type: application/json" \
  -d '{"type":"CNAME","name":"subdomain","content":"new-target.example.com","proxied":true}'

# Delete record
curl -s -X DELETE "https://api.cloudflare.com/client/v4/zones/$ZONE_ID/dns_records/{record_id}" \
  -H "Authorization: Bearer $CF_TOKEN"
```

**Note:** DNS write operations require a token with DNS Edit permission. The default read-only token cannot create, update, or delete records. Always confirm with the user before executing write operations.

### Traffic Analytics (GraphQL)

The old REST analytics API is sunset. Use the GraphQL API at `https://api.cloudflare.com/client/v4/graphql`.

```bash
# Daily traffic analytics (last N days)
curl -s -X POST "https://api.cloudflare.com/client/v4/graphql" \
  -H "Authorization: Bearer $CF_TOKEN" -H "Content-Type: application/json" \
  -d '{
    "query": "{ viewer { zones(filter: {zoneTag: \"'$ZONE_ID'\"}) { httpRequests1dGroups(limit: 30, filter: {date_geq: \"YYYY-MM-DD\", date_leq: \"YYYY-MM-DD\"}, orderBy: [date_ASC]) { dimensions { date } sum { requests cachedRequests bytes cachedBytes pageViews threats browserMap { pageViews uaBrowserFamily } countryMap { requests clientCountryName } responseStatusMap { requests edgeResponseStatus } } uniq { uniques } } } } }"
  }'
```

**Available datasets:**

| Dataset | Granularity | Use for |
|---------|-------------|---------|
| `httpRequests1dGroups` | Daily | Traffic overview, trends |
| `httpRequests1hGroups` | Hourly | Intraday patterns, incident response |
| `httpRequests1mGroups` | Per-minute | Real-time debugging |
| `httpRequestsAdaptiveGroups` | Adaptive | Custom grouping/filtering |

**Available aggregate fields in `sum`:**
- `requests`, `cachedRequests`, `bytes`, `cachedBytes`, `encryptedBytes`
- `pageViews`, `threats`
- `browserMap { pageViews uaBrowserFamily }`
- `countryMap { requests bytes threats clientCountryName }`
- `responseStatusMap { requests edgeResponseStatus }`
- `contentTypeMap { bytes requests contentTypeName edgeCacheStatus }`
- `ipClassMap { requests ipType }`
- `clientSSLMap { requests clientSSLProtocol }`

**Unique visitors:** `uniq { uniques }`

**Filter operators:** `_gt`, `_lt`, `_geq`, `_leq`, `_neq`, `_in`, `_like`

### Security / Firewall Events (GraphQL)

```bash
# Recent firewall events
curl -s -X POST "https://api.cloudflare.com/client/v4/graphql" \
  -H "Authorization: Bearer $CF_TOKEN" -H "Content-Type: application/json" \
  -d '{
    "query": "{ viewer { zones(filter: {zoneTag: \"'$ZONE_ID'\"}) { firewallEventsAdaptive(filter: {datetime_geq: \"YYYY-MM-DDTHH:MM:SSZ\", datetime_leq: \"YYYY-MM-DDTHH:MM:SSZ\"}, limit: 25, orderBy: [datetime_DESC]) { action clientAsn clientCountryName clientIP clientRequestHTTPHost clientRequestHTTPMethodName clientRequestPath datetime source userAgent } } } }"
  }'

# Aggregated firewall events by country
curl -s -X POST "https://api.cloudflare.com/client/v4/graphql" \
  -H "Authorization: Bearer $CF_TOKEN" -H "Content-Type: application/json" \
  -d '{
    "query": "{ viewer { zones(filter: {zoneTag: \"'$ZONE_ID'\"}) { firewallEventsAdaptiveGroups(filter: {datetime_geq: \"YYYY-MM-DDTHH:MM:SSZ\", datetime_leq: \"YYYY-MM-DDTHH:MM:SSZ\"}, limit: 25, orderBy: [count_DESC]) { count dimensions { action clientCountryName source } } } } }"
  }'
```

**Firewall event fields:** `action`, `clientAsn`, `clientCountryName`, `clientIP`, `clientRequestHTTPHost`, `clientRequestHTTPMethodName`, `clientRequestPath`, `clientRequestQuery`, `datetime`, `source`, `userAgent`, `ruleId`

**Possible actions:** `allow`, `block`, `challenge`, `jschallenge`, `managedchallenge`, `bypass`, `log`, `connectionclose`

### Cache Operations

```bash
# Purge everything
curl -s -X POST "https://api.cloudflare.com/client/v4/zones/$ZONE_ID/purge_cache" \
  -H "Authorization: Bearer $CF_TOKEN" -H "Content-Type: application/json" \
  -d '{"purge_everything": true}'

# Purge specific URLs
curl -s -X POST "https://api.cloudflare.com/client/v4/zones/$ZONE_ID/purge_cache" \
  -H "Authorization: Bearer $CF_TOKEN" -H "Content-Type: application/json" \
  -d '{"files": ["https://prod.myvoya.ai/", "https://prod.myvoya.ai/index.html"]}'

# Purge by host
curl -s -X POST "https://api.cloudflare.com/client/v4/zones/$ZONE_ID/purge_cache" \
  -H "Authorization: Bearer $CF_TOKEN" -H "Content-Type: application/json" \
  -d '{"hosts": ["prod.myvoya.ai"]}'

# Purge by prefix
curl -s -X POST "https://api.cloudflare.com/client/v4/zones/$ZONE_ID/purge_cache" \
  -H "Authorization: Bearer $CF_TOKEN" -H "Content-Type: application/json" \
  -d '{"prefixes": ["prod.myvoya.ai/static"]}'
```

**Note:** Cache purge requires a token with Cache Purge permission. The default read-only token cannot purge. Always confirm with the user before purging.

### Page Rules

```bash
# List page rules
curl -s "https://api.cloudflare.com/client/v4/zones/$ZONE_ID/pagerules" \
  -H "Authorization: Bearer $CF_TOKEN" | jq '.result[] | {id, priority, status, targets: [.targets[].constraint.value], actions: [.actions[] | {id, value}]}'
```

**Current page rules:**

| Priority | Pattern | Action |
|----------|---------|--------|
| 1 | `*.myvoya.ai/health` | Bypass cache |
| 2 | `*.myvoya.ai/api/*` | Bypass cache |
| 4 | `cdn.myvoya.ai/*` | Cache Everything |
| 5 | `cdn-staging.myvoya.ai/*` | Cache Everything |

### Zone Settings

```bash
# Get a specific setting
curl -s "https://api.cloudflare.com/client/v4/zones/$ZONE_ID/settings/{setting_id}" \
  -H "Authorization: Bearer $CF_TOKEN" | jq '.result'

# Update a setting
curl -s -X PATCH "https://api.cloudflare.com/client/v4/zones/$ZONE_ID/settings/{setting_id}" \
  -H "Authorization: Bearer $CF_TOKEN" -H "Content-Type: application/json" \
  -d '{"value": "new_value"}'
```

**Common setting IDs:** `always_use_https`, `automatic_https_rewrites`, `brotli`, `browser_cache_ttl`, `development_mode`, `early_hints`, `http2`, `http3`, `min_tls_version`, `minify`, `websocket`, `ssl`

### Zone Overview

```bash
# List zones
curl -s "https://api.cloudflare.com/client/v4/zones" \
  -H "Authorization: Bearer $CF_TOKEN" | jq '.result[] | {name, id, status}'

# Get zone details
curl -s "https://api.cloudflare.com/client/v4/zones/$ZONE_ID" \
  -H "Authorization: Bearer $CF_TOKEN" | jq '.result | {name, status, plan: .plan.name, name_servers}'
```

## Infrastructure Context

**App subdomains** (proxied through CloudFlare):

| Subdomain | Target | Purpose |
|-----------|--------|---------|
| `app.myvoya.ai` | production ALB | Production (user-facing) |
| `prod.myvoya.ai` | production ALB | Production (direct) |
| `staging.myvoya.ai` | staging ALB | Staging environment |
| `cdn.myvoya.ai` | production ALB | imgproxy CDN (production) |
| `cdn-staging.myvoya.ai` | staging ALB | imgproxy CDN (staging) |

**Cache strategy:**
- API/health/auth endpoints: `no-store` (via backend CacheControlMiddleware)
- Static assets: 1 year cache
- CDN subdomains: Cache Everything (page rule), not purged on deploy
- App subdomains: Respect backend Cache-Control headers

**Deploy cache purge:**
- Staging deploy: purges `staging.myvoya.ai`
- Production deploy: purges `prod.myvoya.ai` and `app.myvoya.ai`
- CDN subdomains: never purged by deploys (images stay cached)

## Output Formatting

When presenting results to the user:
- Use tables for DNS records, analytics, and page rules
- Highlight anomalies (traffic spikes, high error rates, threats)
- Calculate cache hit rates as percentages
- Convert bytes to human-readable sizes (KB, MB, GB)
- Flag security events with country and action
- Compare against expected traffic patterns (team countries: NL, GB, PK, PH, CO, US)

## Safety Rules

- **Always confirm** before: DNS changes, cache purges, setting updates
- **Never** create/delete DNS records without explicit user approval
- **Read the token** from `.local/secrets/cloudflare_token`, never hardcode
- **Report anomalies** proactively (attack patterns, unusual traffic, high error rates)
