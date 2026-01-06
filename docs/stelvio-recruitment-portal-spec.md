# Stelvio Group — Recruitment Portal Specification

## 1) Overview

### 1.1 Goal
Build a secure, easy-to-use recruitment portal for Stelvio Group that:
- Ingests candidate CVs in bulk
- Extracts structured candidate data via CV analysis API and **upserts** to Candidate records
- Automatically finds relevant job vacancies across configured job sites
- Enriches employer (company) information via **Clay**
- Identifies key stakeholders for outreach based on configurable rules
- Generates match explanations and enables one-click stakeholder emailing from approved templates

### 1.2 Primary users (personas)
- **Recruiter**: Uploads CVs, reviews candidates, reviews matches, emails stakeholders.
- **Team Lead / Manager**: Oversees pipeline, configures sources and stakeholder rules, approves templates.
- **Admin**: Manages users/groups/permissions, integrations, audit, and security.

### 1.3 Product principles (what makes it “lovable”)
- **Everything is guided**: clear next actions (Upload → Review parsing → Run matching → Review matches → Email).
- **Fast to recover**: undo, retry, and “needs review” states instead of hard failures.
- **Explainability by default**: every match and enrichment stores a “why” and sources used.
- **Minimal data entry**: infer from CVs/job descriptions; only ask users to confirm/complete.

---

## 2) Branding & UI/UX Standards

### 2.1 Stelvio colour scheme
Use Stelvio Group brand colours. If official brand tokens are not available at build time, implement a **theme token system** so colours can be updated without code changes.

Required theme tokens (examples only; replace with official Stelvio palette):
- `--color-primary` (buttons/links)
- `--color-primary-contrast` (text on primary)
- `--color-accent` (highlights)
- `--color-bg` / `--color-surface` / `--color-border`
- `--color-success` / `--color-warning` / `--color-danger`

### 2.2 UX patterns
- **Global search**: search candidates/companies/vacancies by name, email, phone, domain.
- **Left nav** (modules) + **top bar** (search, notifications, user menu).
- **Sticky action bar** on key records (Candidate/Vacancy/Company) with primary actions.
- **Bulk actions** in lists (tag, assign, run matching, export).
- **Empty states** that explain what to do next (and allow uploading/config directly).
- **Inline validation** + “Save draft” for long forms (templates/rules).

### 2.3 Accessibility & responsiveness
- WCAG 2.1 AA targets (contrast, focus, keyboard navigation)
- Responsive for laptop + tablet; mobile read-only is acceptable unless requested.

### 2.4 Information architecture (screens)
Left navigation (module → screens):
- **Dashboard**
  - Overview KPIs
  - Work queue (Needs review / Needs approval)
- **Candidates**
  - Candidate list
  - Candidate detail (Overview / CV & Parsing / Matches / Activity / Notes)
  - Bulk upload
- **Vacancies**
  - Vacancy list
  - Vacancy detail (Description / Matches / Company / Activity)
- **Companies**
  - Company list (filter by domain/website)
  - Company detail (Overview / Enrichment / Contacts / Activity)
- **Contacts**
  - Contact list
  - Contact detail
- **Matching**
  - Match review queue (by candidate and by vacancy)
- **Email**
  - Templates (list/detail/editor)
  - Outbox / delivery events
- **Configuration**
  - Job Sources (job websites)
  - Stakeholder Keywords
  - Stakeholder Bands (employee ranges + titles)
  - Integrations (CV parsing, Clay, email provider)
- **Admin**
  - Users
  - Groups & Permissions
  - Audit log

---

## 3) Authentication, Authorization, and Security

### 3.1 Authentication
Minimum:
- Email + password login
- **Reset password** via email token (time-limited, single-use)
- Session management (secure cookies, CSRF protection)

Recommended:
- Optional **MFA** (TOTP) for Admins
- Optional SSO (SAML/OIDC) as a future enhancement

### 3.2 Authorization (groups, roles, and per-screen access)
The system must support:
- **User Groups** (e.g., Recruiters, Managers, Admins)
- **Permissions** per module/screen: `NO_ACCESS`, `READ`, `WRITE`
- Optional finer-grain permissions: `EXPORT`, `BULK_IMPORT`, `RUN_MATCHING`, `SEND_EMAIL`, `MANAGE_TEMPLATES`, `MANAGE_INTEGRATIONS`

Implementation requirements:
- Permission checks enforced **server-side** on every endpoint.
- UI hides/disabled actions based on permissions but is not the security boundary.
- Audit log includes permission-denied events.

Suggested `module_key` list (used by permissions):
- `DASHBOARD`
- `CANDIDATES`
- `CANDIDATE_IMPORT`
- `VACANCIES`
- `COMPANIES`
- `CONTACTS`
- `MATCHING`
- `EMAIL_TEMPLATES`
- `EMAIL_SENDING`
- `JOB_SOURCES`
- `STAKEHOLDER_RULES`
- `INTEGRATIONS`
- `USERS_ADMIN`
- `AUDIT_LOG`

### 3.3 Data protection & compliance
- GDPR: lawful basis, retention policies, deletion/anonymization flow for candidates.
- CV files stored encrypted at rest; access logged.
- PII fields masked in logs; secrets never logged.
Additional controls:
- Malware scanning for uploaded CV files (recommended) before parsing.
- Row-level access controls (optional future): e.g., recruiters only see their assigned candidates.

---

## 4) Core Modules (Functional Specification)

### 4.1 Users & Groups
Screens:
- User list + invite user (email invite link)
- User detail: group membership, status (active/disabled), last login
- Group management: name, description, module permissions matrix

Rules:
- Disabled users cannot log in; their actions remain in audit history.

### 4.2 Candidates
Candidate fields (minimum):
- Full name
- Address (structured when possible: street/city/postcode/country)
- Email(s), Mobile/Phone(s)
- Key skills (normalized list)
- CV: file(s), parsed text, parsing confidence, parsing provider metadata
- Source (bulk upload, manual, API)
- Tags, assigned recruiter, notes

Candidate UX:
- Candidate profile with tabs: **Overview**, **CV & Parsing**, **Matches**, **Activity**, **Notes**
- “Needs review” banner if parsing confidence is low or required fields missing

### 4.3 Bulk CV upload
Supported formats (initial):
- PDF, DOC, DOCX (optionally TXT)

Upload UX:
- Drag/drop multi-file upload
- Progress + per-file status: uploaded → parsing → upserted → matched
- Ability to **retry** parsing per CV and to **merge/resolve duplicates**

Import rules:
- Deduplicate by (normalized email) OR (normalized phone) OR (name + postcode) with confidence scoring.
- Provide merge UI if ambiguous.

### 4.4 CV Analysis API (parsing & skills extraction)
Portal must call an external API to extract:
- Name, Address, Email, Mobile number, Key Skills

Technical requirements:
- Async processing via background job queue
- Store raw response, normalized fields, and mapping decisions
- Confidence thresholds:
  - High: auto-upsert
  - Medium: upsert + mark “needs review”
  - Low: do not overwrite existing verified fields; require user confirmation

Upsert behavior:
- Candidate is identified by email/phone (configurable priority).
- On upsert, do not overwrite “verified” fields unless user explicitly allows.

### 4.5 Job Websites (Vacancy Sources) module
Purpose: Configure where the portal searches for jobs.

Entity: **Job Source**
- Name
- Type: `API`, `RSS`, `SCRAPE` (scrape only where allowed by terms)
- Base URL(s)
- Search endpoint details (template for query params) OR API credentials
- Rate limits + concurrency config
- Enabled/disabled
- Supported geographies, industries (optional)

Job Source config (recommended `config_json` shape):
- `auth`: `{ type: "none"|"api_key"|"oauth2", headerName?: string, apiKeySecretRef?: string, tokenUrl?: string, clientIdSecretRef?: string, clientSecretRef?: string }`
- `search`: `{ urlTemplate: string, method: "GET"|"POST", headers?: object, queryMapping: { skills: string, location?: string, seniority?: string }, bodyTemplate?: object }`
- `responseMapping`: `{ titlePath: string, companyNamePath: string, descriptionPath: string, locationPath?: string, postedAtPath?: string, urlPath: string }`
- `limits`: `{ requestsPerMinute: number, maxConcurrent: number }`

### 4.6 Vacancy discovery workflow (per candidate)
Trigger: Candidate created (from CV upsert) OR manual “Run matching”.

Process:
1. Build a candidate search query from **Key Skills** + optional location/seniority.
2. For each enabled Job Source:
   - Search for relevant vacancies
   - Normalize vacancy details
3. For each vacancy:
   - Compute match score + “why” explanation
   - Persist match result

Stored vacancy fields (minimum):
- Job title
- Company name (as posted)
- Job description (raw + cleaned)
- Location
- Source site + source URL
- Date posted (if available)

Match explanation fields:
- Matching skills
- Missing but relevant skills (optional)
- Seniority/industry alignment (optional)
- A short narrative reason (AI-generated allowed, with guardrails)

### 4.7 Company enrichment (best-guess website + Clay)
Goal: Use vacancy company name + job description to identify company website and enrich company data.

Step A — Best-guess website/domain:
- Input: company_name, job_description, vacancy_source_url
- Preferred approach: use a “company domain discovery” strategy:
  - If vacancy page contains canonical domain, use it
  - Else use a search provider (configurable) to find official site
  - Apply domain heuristics (exclude job boards/social networks unless official)
- Output: `company_domain`, `company_website_url`, confidence score, evidence/source

Step B — Clay enrichment:
- Input parameter: website/domain (required), company name (optional)
- Call Clay to fetch and return company details and store in Company table.

Company fields required (as requested):
- Company name
- Main office number
- Address
- Website
- Description
- Number of employees

Additional recommended fields:
- Industry
- HQ location breakdown (city/country)
- LinkedIn company URL
- Enrichment status + timestamps + provider metadata

Clay integration requirements:
- Configurable API key(s) and workspace/table identifiers
- Rate limit handling + retries with exponential backoff
- Store Clay request id / run id for traceability
- Allow re-enrichment from Company screen

### 4.8 Key Stakeholders module (rules & job titles)
Purpose: Define which stakeholder job titles to target based on company size banding and keywords.

Concepts:
- **Stakeholder Keywords**: keyword list used to build role/title queries (e.g., “Finance”, “Operations”, “HR”).
- **Employee Band Rules**: each record defines:
  - Employees **from** / **to**
  - Applicable stakeholder title patterns (e.g., CFO, Finance Director, Head of Finance)
  - Optional include/exclude keywords

UX:
- A table editor to manage bands (e.g., 1–50, 51–200, 201–1000, 1000+)
- For each band: list of titles (chips) + preview “generated role queries”

API usage requirement:
When stakeholder discovery is triggered, the system selects the employee band based on company employee count and uses those titles/keywords to request stakeholders.

### 4.9 Contacts (key stakeholders)
Contact record minimum fields:
- Name
- Job title
- Email (optional)
- Phone (optional)
- LinkedIn URL (optional)
- Company (link)
- Source + source URL(s)

Creation:
- From stakeholder discovery workflow (preferred)
- Manual creation allowed (with validation and duplicate detection)

### 4.10 Email templates (HTML) + triggering
Template capabilities:
- Upload HTML templates
- Versioning (draft/published/archived)
- Variables/merge tags (examples):
  - `{{contact.first_name}}`, `{{company.name}}`, `{{candidate.name}}`, `{{vacancy.title}}`, `{{match.reason}}`
- Preview rendering with sample data
- “Send test email” feature
Guardrails:
- Block remote image loading in previews unless explicitly allowed (privacy).
- Validate HTML size and strip dangerous tags/attributes to prevent XSS in the portal.

Trigger:
- Workflow can trigger an email when a **Contact** is created, but to keep UX safe:
  - Default: create an “Email ready” task/notification requiring user approval
  - Optional setting per template: “auto-send on contact create” (Admin-only)

Email sending:
- Use a transactional provider (SendGrid/Mailgun/AWS SES) or Microsoft 365/Google OAuth if required.
- Track delivery status, bounces, and opens/clicks if available.

### 4.11 Matching module (candidate ↔ vacancy)
Core outputs:
- Match score (0–100)
- Reason text + matching skills list
- “Email stakeholders” checkbox/action

UX:
- Candidate → Matches: sortable list with filters (score, source, date, company)
- Vacancy → Candidate matches: list view for reverse lookup
- “Select matches” → bulk email stakeholders (with review step)

Safety:
- Always show recipients, template, and final rendered email before send unless auto-send is explicitly enabled.

---

## 5) Workflow Orchestration (Technical)

### 5.1 Event triggers
Events:
- `candidate.created`
- `candidate.updated` (skills changed)
- `cv.uploaded`
- `vacancy.discovered`
- `company.enrichment.requested`
- `contact.created`

### 5.2 Job queue / background workers
Because CV parsing, job searching, enrichment, and stakeholder discovery are long-running and rate-limited, implement:
- Job queue (e.g., Redis-backed) with worker concurrency controls
- Idempotency keys for external calls to avoid duplicates
- Retries with backoff and dead-letter queue

Idempotency guidance:
- CV parse idempotency: keyed by file `sha256`
- Vacancy discovery idempotency: keyed by `(candidate_id, job_source_id, query_hash)`
- Company enrichment idempotency: keyed by `(company_domain, provider)`

### 5.3 Suggested workflow pipeline
1. CV uploaded → store file → enqueue `parse_cv`
2. `parse_cv` → call CV API → normalize → upsert candidate → emit `candidate.created`
3. `candidate.created` → enqueue `discover_vacancies(candidate_id)`
4. `discover_vacancies` → query each Job Source → store vacancies + matches
5. For vacancies missing company website → enqueue `resolve_company_domain(vacancy_id)`
6. When domain resolved → enqueue `enrich_company_with_clay(company_id)`
7. When company enriched → enqueue `discover_stakeholders(company_id)`
8. When contacts created → trigger template workflow (approval or auto-send)

---

## 6) Data Model (Relational — recommended tables)

### 6.1 Core tables
- `users` (id, email, name, status, password_hash/identity_provider, last_login_at, created_at)
- `groups` (id, name, description)
- `group_memberships` (user_id, group_id)
- `permissions` (group_id, module_key, access_level, created_at)

- `candidates` (id, full_name, address_json, emails_json, phones_json, key_skills_json, assigned_user_id, status, created_at, updated_at)
- `candidate_files` (id, candidate_id, file_name, mime_type, storage_url, sha256, uploaded_by, created_at)
- `cv_parses` (id, candidate_file_id, provider, raw_response_json, normalized_json, confidence_json, status, created_at)

- `job_sources` (id, name, type, config_json, enabled, created_at)
- `vacancies` (id, job_source_id, source_url, title, company_name_raw, location, description_raw, description_clean, posted_at, created_at)
- `candidate_vacancy_matches` (id, candidate_id, vacancy_id, score, reasons_json, narrative_reason, created_at)

- `companies` (id, name, website, domain, main_phone, address_json, description, employee_count, enrichment_status, created_at, updated_at)
- `company_enrichments` (id, company_id, provider, request_id, raw_response_json, status, created_at)
- `vacancy_company_links` (vacancy_id, company_id, confidence, evidence_json)

- `stakeholder_keywords` (id, keyword, created_at)
- `stakeholder_bands` (id, employees_from, employees_to, titles_json, include_keywords_json, exclude_keywords_json, created_at)

- `contacts` (id, company_id, full_name, job_title, email, phone, linkedin_url, source, source_url, created_at)

- `email_templates` (id, name, status, subject_template, html_body, variables_schema_json, created_at, updated_at)
- `email_events` (id, template_id, contact_id, candidate_id, vacancy_id, status, provider_message_id, error, created_at)

- `audit_log` (id, actor_user_id, action_key, entity_type, entity_id, metadata_json, created_at, ip_address)

### 6.2 Indexing & uniqueness (examples)
- Unique (lower(email)) in contacts where not null (with company_id scope if desired)
- Unique (source_url) in vacancies (per job_source)
- Unique (domain) in companies

### 6.3 Status/state fields (recommended enums)
- `cv_parses.status`: `PENDING`, `RUNNING`, `SUCCEEDED`, `FAILED`, `NEEDS_REVIEW`
- `companies.enrichment_status`: `NOT_STARTED`, `RUNNING`, `SUCCEEDED`, `FAILED`
- `email_templates.status`: `DRAFT`, `PUBLISHED`, `ARCHIVED`
- `email_events.status`: `QUEUED`, `SENT`, `DELIVERED`, `BOUNCED`, `FAILED`

---

## 7) Internal APIs (Portal Backend)

### 7.1 Authentication
- `POST /auth/login`
- `POST /auth/logout`
- `POST /auth/forgot-password`
- `POST /auth/reset-password`

### 7.2 Candidates & files
- `POST /candidates` (manual create)
- `GET /candidates`
- `GET /candidates/:id`
- `PATCH /candidates/:id`
- `POST /candidates/:id/files` (multipart upload)
- `POST /candidates/:id/run-matching`

### 7.3 Job sources
- `GET /job-sources`
- `POST /job-sources`
- `PATCH /job-sources/:id`

### 7.4 Vacancies & matches
- `GET /vacancies`
- `GET /vacancies/:id`
- `GET /candidates/:id/matches`

### 7.5 Companies & enrichment
- `GET /companies`
- `GET /companies/:id`
- `POST /companies/:id/enrich` (Clay)
Notes:
- `GET /companies` supports filters: `?domain=`, `?website=`, `?name=`

### 7.6 Stakeholders & contacts
- `GET /stakeholder-bands`
- `POST /stakeholder-bands`
- `PATCH /stakeholder-bands/:id`
- `POST /companies/:id/discover-stakeholders`
- `GET /contacts`
- `POST /contacts`

### 7.7 Email templates & send
- `GET /email-templates`
- `POST /email-templates`
- `PATCH /email-templates/:id`
- `POST /email-templates/:id/test-send`
- `POST /emails/send` (requires permission + review payload)

All endpoints must enforce RBAC permissions.

---

## 8) External Integrations

### 8.1 CV parsing provider
Requirements for provider:
- Accepts PDF/DOC/DOCX
- Returns structured fields + skills
- Returns confidence per field

Portal integration:
- Store API keys in secret manager
- Timeouts and retries
- Provider failures must not block upload UX; file stays in “needs retry” state

### 8.2 Job vacancy sources
Each Job Source record stores:
- Auth (API key/OAuth if needed)
- Query mapping rules (skills → keywords, location, seniority)
- Response mapping (normalize to internal vacancy schema)

Compliance:
- Respect robots.txt and ToS for any scraping
- Prefer official APIs/RSS feeds

### 8.3 Clay (Company enrichment)
Clay usage:
- Search/enrich by website/domain and return company data fields
- Map fields into `companies`
- Record provenance (provider + run/request id)

### 8.4 Stakeholder discovery provider (how key stakeholders are returned)
The portal must be able to “instigate an API” to return key stakeholders using:
- Company domain/website
- Company size (employee_count) → selects stakeholder band
- Generated title queries (from band titles + stakeholder keywords)

This can be implemented via:
- Clay (if using people enrichment), OR
- A separate contact-finding provider (Apollo/ZoomInfo/Clearbit successor/etc.), OR
- A custom web discovery process (respecting ToS and consent requirements)

Expected response shape (normalized into `contacts`):
- `full_name`, `job_title`, `email?`, `phone?`, `linkedin_url?`, `source_url?`, `confidence`

---

## 9) Observability, Reliability, and Admin Tools

### 9.1 Audit & activity
- Every create/update/delete + workflow actions (parsing, enrichment, sends) recorded.
- Candidate activity timeline merges audit + system events.

### 9.2 Monitoring
- Job queue metrics (latency, failures, retries)
- External API latency/error rate
- Email delivery/bounce tracking

### 9.3 Admin configuration
Screens:
- Integrations (keys, rate limits, test connection)
- Feature flags (auto-send on contact create, scraping enabled)
- Retention settings (CV file retention, data deletion requests)

---

## 10) Acceptance Criteria (by feature)

### 10.1 Login & reset password
- User can request reset; email token expires; password updated; old sessions invalidated.

### 10.2 Permissions
- Admin can create group, assign module permissions, and behavior matches `NO_ACCESS/READ/WRITE`.

### 10.3 Bulk CV upload + parsing
- Upload 50+ CVs; each shows per-file status; candidates are created/upserted; duplicates flagged.

### 10.4 Vacancy discovery + matching
- New candidate triggers vacancy search across enabled sources; matches stored with reasons; visible in UI.

### 10.5 Company enrichment via Clay
- Vacancy company resolved to website; Clay enrichment populates company table; linked to vacancy and contacts.

### 10.6 Stakeholders (employee bands)
- Admin defines bands; for a company with employee_count, correct band applies and stakeholder discovery uses generated titles.

### 10.7 Email templates + workflow
- Admin uploads template; recruiter previews on a contact; send produces logged email event; failures are visible and retryable.

---

## 11) Open Questions / Assumptions (explicit)
- “Stelvio colours” are assumed to be provided as brand tokens; portal implements theme tokens to avoid rework.
- Job board sources must be confirmed (some prohibit scraping). The spec assumes configurable sources and prefers APIs/RSS.
- “Use Clay” assumes Clay provides an API to enrich company details by domain; exact endpoints/fields must be mapped during implementation.

---

## 12) Reference Architecture (implementation-ready guidance)

### 12.1 Components
- **Web app (frontend)**: role-based UI, upload UI, record views, template editor.
- **Backend API**: authentication, RBAC enforcement, CRUD, orchestration endpoints, webhooks.
- **Database**: relational (PostgreSQL recommended) for core entities and audit.
- **Object storage**: for CV files and email template assets (S3-compatible).
- **Queue + workers**: background tasks (parsing, searching, enrichment, sending).
- **Email provider**: SMTP/API provider with event webhooks into `email_events`.
- **Secrets manager**: stores API keys for CV parsing, Clay, job sources, email provider.

### 12.2 Operational requirements
- Rate limiting per integration + global concurrency caps
- Timeouts and circuit breakers for external calls
- Structured logs + correlation ids across workflow steps
- Backups (DB + object storage) and retention policies

### 12.3 Environments
- Dev / Staging / Prod with separate integration credentials
- Staging should allow “sandbox mode” (no real emails unless explicitly enabled)

