# x-ui REST API Documentation

> **Version:** 2.0.0  
> **Base URL:** `http://<server>:8001/api/v1`  
> **Interactive Docs:** `http://<server>:8001/docs` (Swagger UI) · `http://<server>:8001/redoc`  
> **Operations:** Full CRUD on managed tables, Read-only on auto-updated tables

---

## ⚠️ Important: Auto-Updated Fields

The `x-ui.db` database is **actively written to by 3x-ui every ~1 second**. The following data is **read-only** through this API:

| Auto-managed data | Reason |
|---|---|
| `up`, `down`, `all_time` on `inbounds` | Traffic counters updated by xray core |
| `up`, `down`, `all_time`, `last_online` on `client_traffics` | Per-client traffic tracked by xray |
| Entire `outbound_traffics` table | Outbound route stats managed by xray |
| Entire `inbound_client_ips` table | Client IPs populated as clients connect |

**You CAN write:** `enable`, `expiry_time`, `total` (quota), `reset`, configuration fields.

---

## Table of Contents

1. [Quick Start](#quick-start)
2. [Inbounds](#3-inbounds) — Full CRUD (traffic fields read-only)
3. [Client Traffics](#4-client-traffics) — Full CRUD + reset (traffic fields read-only)
4. [Client IPs](#5-client-ips) — Read-only
5. [Outbound Traffics](#6-outbound-traffics) — Read-only
6. [Error Responses](#error-responses)
7. [Quick Reference](#quick-reference--curl-examples)

---

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Run the server (from the project root, next to x-ui.db)
cd /etc/x-ui
uvicorn api.main:app --host 0.0.0.0 --port 8001 --reload
```

---

## Common Conventions

| Convention | Detail |
|---|---|
| **Content-Type** | `application/json` |
| **Partial updates** | Use `PATCH` — only send fields you want to change |
| **Traffic values** | All `up`, `down`, `total`, `all_time` are in **bytes** |
| **Timestamps** | `expiry_time`, `last_online` are **Unix milliseconds** (`0` = unlimited/never) |
| **Email in URL** | URL-encode spaces: `Mahamuth -v` → `Mahamuth%20-v` |

---

## 1. Inbounds

> Xray inbound proxy configurations. **Full CRUD** (traffic counters are read-only).

| Method | Path | Description |
|---|---|---|
| `GET` | `/inbounds/` | List all inbounds |
| `GET` | `/inbounds/{id}` | Get inbound by ID |
| `POST` | `/inbounds/` | Create new inbound |
| `PATCH` | `/inbounds/{id}` | Update inbound fields |
| `DELETE` | `/inbounds/{id}` | Delete an inbound |

### Writable fields on PATCH

| Field | Type | Description |
|---|---|---|
| `remark` | str | Display name |
| `enable` | bool | Active status |
| `expiry_time` | int | Expiry (ms) — 0 = never |
| `traffic_reset` | str | Reset period |
| `listen` | str | Bind address |
| `port` | int | Listening port |
| `protocol` | str | `vless`, `vmess`, `trojan`, etc. |
| `settings` | str | JSON string |
| `stream_settings` | str | JSON string |
| `tag` | str | Unique xray tag |
| `sniffing` | str | JSON string |
| `total` | int | Quota (bytes) — 0 = unlimited |

> ❌ **Cannot update:** `up`, `down`, `all_time`, `last_traffic_reset_time` — auto-managed by 3x-ui.

### `PATCH /inbounds/{id}` — example
```json
{ "enable": false, "total": 107374182400 }
```

### `DELETE /inbounds/{id}`
```json
{ "deleted": true, "id": 1, "tag": "inbound-443" }
```

---

## 2. Client Traffics

> Per-client traffic tracking, quotas, and expiry. **Full CRUD + reset** (traffic counters are read-only).

| Method | Path | Description |
|---|---|---|
| `GET` | `/client-traffics/` | List all clients |
| `GET` | `/client-traffics/{id}` | Get client by ID |
| `GET` | `/client-traffics/by-email/{email}` | Get client by email |
| `POST` | `/client-traffics/` | Create client record |
| `PATCH` | `/client-traffics/{id}` | Update client fields |
| `PATCH` | `/client-traffics/by-email/{email}` | Update client by email |
| `POST` | `/client-traffics/{id}/reset` | Reset traffic counters |
| `DELETE` | `/client-traffics/{id}` | Delete client record |
| `DELETE` | `/client-traffics/by-email/{email}` | Delete client by email |

### Writable fields on PATCH

| Field | Type | Description |
|---|---|---|
| `enable` | bool | Active status |
| `expiry_time` | int | Expiry (ms) — 0 = never |
| `total` | int | Quota (bytes) — 0 = unlimited |
| `reset` | int | Reset counter |

> ❌ **Cannot update:** `up`, `down`, `all_time`, `last_online` — auto-managed by 3x-ui.

### `GET /client-traffics/by-email/{email}`

> ⚠️ **URL-encode spaces** — e.g. `Mahamuth -v` → `Mahamuth%20-v`

```bash
curl "http://localhost:8001/api/v1/client-traffics/by-email/Mahamuth%20-v"
```

### `POST /client-traffics/`
```json
{
  "inbound_id": 1,
  "email": "newuser -v",
  "enable": true,
  "expiry_time": 0,
  "total": 107374182400
}
```

### `PATCH /client-traffics/{id}`
```json
{ "total": 214748364800, "expiry_time": 1790000000000 }
```

### `PATCH /client-traffics/by-email/{email}`
```json
{ "enable": false }
```

### `POST /client-traffics/{id}/reset`
Resets `up` and `down` to 0 and increments the `reset` counter. No request body needed.

**Response `200`**
```json
{ "id": 31, "reset": 1, "up": 0, "down": 0 }
```

### `DELETE /client-traffics/{id}`
```json
{ "deleted": true, "id": 31, "email": "Mahamuth -v" }
```

### `DELETE /client-traffics/by-email/{email}`
```json
{ "deleted": true, "id": 31, "email": "Mahamuth -v" }
```

---

## 3. Client IPs

> Tracks IP addresses seen per client email. **Read-only** — populated by 3x-ui.

| Method | Path | Description |
|---|---|---|
| `GET` | `/client-ips/` | List all records |
| `GET` | `/client-ips/{id}` | Get by ID |
| `GET` | `/client-ips/by-email/{email}` | Get by client email |

### `GET /client-ips/by-email/{email}`
```bash
curl "http://localhost:8001/api/v1/client-ips/by-email/vikum%20-v"
```

---

## 4. Outbound Traffics

> Tracks traffic per outbound xray route tag. **Read-only** — managed by 3x-ui.

| Method | Path | Description |
|---|---|---|
| `GET` | `/outbound-traffics/` | List all |
| `GET` | `/outbound-traffics/{id}` | Get by ID |
| `GET` | `/outbound-traffics/by-tag/{tag}` | Get by tag name |

---

## 5. Error Responses

| Status | Meaning | Example trigger |
|---|---|---|
| `400` | Bad request | Missing required field, duplicate unique value, trying to update auto-managed fields |
| `404` | Not found | Wrong ID or email |
| `422` | Unprocessable entity | Wrong data type in body |

**`400` — Trying to update auto-managed fields:**
```json
{ "detail": "Cannot update auto-managed fields: up, down" }
```

---

## 6. Quick Reference — curl Examples

```bash
BASE="http://localhost:8001/api/v1"

# ── Read ─────────────────────────────────────────────────────────
curl "$BASE/client-traffics/"
curl "$BASE/client-traffics/by-email/Mahamuth%20-v"
curl "$BASE/client-traffics/31"
curl "$BASE/inbounds/"
curl "$BASE/client-ips/by-email/vikum%20-v"
curl "$BASE/outbound-traffics/"

# ── Create ───────────────────────────────────────────────────────
curl -X POST "$BASE/client-traffics/" \
  -H "Content-Type: application/json" \
  -d '{"inbound_id": 1, "email": "newuser -v", "total": 107374182400}'

# ── Update (only management fields — NOT traffic) ────────────────
curl -X PATCH "$BASE/client-traffics/31" \
  -H "Content-Type: application/json" \
  -d '{"enable": false}'

curl -X PATCH "$BASE/client-traffics/by-email/Mahamuth%20-v" \
  -H "Content-Type: application/json" \
  -d '{"total": 214748364800, "expiry_time": 1790000000000}'

# ── Reset traffic counters ───────────────────────────────────────
curl -X POST "$BASE/client-traffics/31/reset"

# ── Delete ───────────────────────────────────────────────────────
curl -X DELETE "$BASE/client-traffics/31"
curl -X DELETE "$BASE/client-traffics/by-email/newuser%20-v"
curl -X DELETE "$BASE/inbounds/2"
```
