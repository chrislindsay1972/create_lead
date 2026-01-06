# Stelvio Group Recruitment Portal - Technical Specification

## 1. Executive Summary
This document outlines the technical specification for the Stelvio Group Recruitment Portal. The portal is designed to streamline the recruitment process through automation, intelligent data enrichment, and seamless workflow integration. It features bulk CV processing, automated job matching, company data enrichment via Clay.com, and targeted stakeholder communication.

## 2. System Architecture

### 2.1 High-Level Architecture
The system will follow a modern, microservices-oriented or modular monolith architecture to ensure scalability and maintainability.

*   **Frontend**: Single Page Application (SPA) or Server-Side Rendered (SSR) web application.
*   **Backend**: RESTful API or GraphQL API handling business logic, authentication, and integrations.
*   **Database**: Relational database for structured data (Users, Candidates, Companies) and potentially a Vector store for semantic matching.
*   **Worker/Queue System**: For handling background tasks (CV parsing, external API calls to Clay.com, Job scraping) to ensure UI responsiveness.

### 2.2 Technology Stack Recommendations
*   **Frontend**: React.js or Next.js (for performance and SEO if needed).
    *   *Styling*: Tailwind CSS (configured with Stelvio Group branding colors).
*   **Backend**: Node.js (NestJS/Express) or Python (Django/FastAPI). Python is recommended if heavy AI/ML matching logic is implemented locally.
*   **Database**: PostgreSQL (robust relational data).
*   **Queue**: Redis (BullMQ or Celery) for managing asynchronous workflows.
*   **Infrastructure**: AWS/Azure/GCP containerized environment (Docker/Kubernetes).

## 3. User Interface & User Experience (UX)

### 3.1 Design System
*   **Theme**: The application will enforce the **Stelvio Group colour palette** globally.
*   **Responsive Design**: Mobile-friendly interface for all modules.
*   **Accessibility**: WCAG 2.1 AA compliance.

### 3.2 UX Improvements & "User Friendly" Corrections
*   **Website Guessing Strategy**: Instead of purely "guessing" the website from the company name (which is error-prone), the system should:
    1.  Attempt to find the domain via a search API (e.g., Google Custom Search or a dedicated Company Autocomplete API).
    2.  Present the "best guess" to the user for one-click confirmation during the import process.
    3.  Allow manual override before triggering downstream data enrichment.
*   **Bulk CV Load**: Provide a drag-and-drop interface with real-time progress bars. Show a "Draft" or "Review" state for parsed data before it is permanently committed to the database, allowing users to correct parsing errors immediately.
*   **Job Matching Visualization**: Instead of just a list, show a "Match Score" (0-100%) with a visual breakdown of *why* (e.g., "Skills matched: 8/10", "Location: Exact").

## 4. Modules & Functionality

### 4.1 Authentication & Authorization
*   **Login**: Secure login screen.
*   **Password Reset**: Self-service "Forgot Password" flow via email link.
*   **User Management (RBAC)**:
    *   **Admin**: Full access to all screens and configuration.
    *   **Recruiter**: Read/Write access to Candidates, Jobs, and Companies.
    *   **Viewer**: Read-only access.
    *   **Granular Permissions**: Ability to define custom groups with specific read/write/no-access flags per module.

### 4.2 Candidate Module
*   **Bulk CV Upload**:
    *   Support for PDF, DOCX, TXT formats.
    *   Uploads stored in secure object storage (e.g., S3).
*   **CV Parsing (API Integration)**:
    *   Integration with a Resume Parsing API (e.g., Affinda, Sovren, or OpenAI).
    *   **Extracted Fields**: Name, Address, Email, Mobile Number, Key Skills (Technical & Soft skills).
    *   **Action**: Upsert (Update if exists, Insert if new) Candidate record based on email/phone uniqueness.

### 4.3 Job Vacancy & Matching Workflow
*   **Trigger**: Event `ON_CANDIDATE_CREATED` triggers the matching workflow.
*   **External Job Search**:
    *   Connects to defined "Job Website Modules" (e.g., LinkedIn, Indeed, Glassdoor - via scraping APIs or official APIs).
    *   **Search Criteria**: Uses Candidate's "Key Skills" and "Location" to query job boards.
*   **Matching Logic**:
    *   Compare Candidate Skills vs. Job Description.
    *   **Generative AI Analysis**: Use an LLM (e.g., GPT-4) to generate a natural language "Reason for Match" (e.g., "Candidate has strong Python skills required by this Fintech role").
    *   Store `MatchRecord` linking Candidate `ID` and Job `ID`.

### 4.4 Company Data Enrichment (Clay.com)
*   **Workflow**:
    1.  Extract Company Name from matched Job Vacancy.
    2.  Resolve Website/Domain (using the improved strategy in 3.2).
    3.  **API Call**: Query Clay.com API using the Company Domain.
*   **Data Points to Store**:
    *   Company Name.
    *   Main Office Phone Number.
    *   Address (HQ).
    *   Website URL.
    *   Company Description.
    *   Employee Count (Total).
*   **Manual Search**: A dedicated UI to manually search Clay.com using a domain string and view/save results.

### 4.5 Stakeholder Management & Key Titles
*   **Configuration**:
    *   Define "Key Keywords" for Job Titles (e.g., "CTO", "Head of Engineering", "Talent Manager").
    *   Define "Employee Banding" rules (e.g., "From 0 to 50 employees" -> Target "Founder"; "From 50 to 200" -> Target "HR Director").
*   **Discovery Logic**:
    *   When enriching a Company, use the *Employee Count* to determine the correct *Banding*.
    *   Use the *Banding* to select target *Job Descriptions/Titles*.
    *   Query Clay.com (or similar contact provider linked via Clay) to find specific people at that company holding those titles.

### 4.6 Communication Module
*   **Email Templates**:
    *   WYSIWYG editor or HTML upload for email templates.
    *   Support for dynamic placeholders (e.g., `{{Candidate.Name}}`, `{{Job.Title}}`, `{{Reason.Match}}`).
*   **Workflow Integration**:
    *   Trigger emails manually (tick box on Match screen) or automatically.
    *   Log all communications in the Contact/Candidate record.

## 5. Data Model Schema (Simplified)

*   **User**: `id, email, password_hash, role_id`
*   **Role**: `id, name, permissions_json`
*   **Candidate**: `id, name, email, mobile, address, cv_file_url, skills_list, created_at`
*   **Company**: `id, name, domain, description, phone, address, employee_count, source_clay_data`
*   **JobVacancy**: `id, company_id, title, description, source_url, status`
*   **Match**: `id, candidate_id, job_id, match_score, match_reason_text`
*   **Stakeholder**: `id, company_id, name, job_title, email, phone`
*   **BandingRule**: `id, min_employees, max_employees, target_job_titles_list`

## 6. Security & Compliance
*   **Data Protection**: All PII (Personally Identifiable Information) encryption at rest and in transit.
*   **GDPR Compliance**:
    *   Mechanism to "Anonymize" or "Delete" candidate data upon request.
    *   Consent logs for email marketing.
*   **Rate Limiting**: Protect external API quotas (Clay.com, Job Boards) by implementing rate limiting on the background workers.

## 7. Next Steps for Development
1.  **Design Phase**: Create Wireframes using Stelvio branding.
2.  **Prototype**: Build the "CV Parsing" and "Clay.com" integration as a Proof of Concept (PoC).
3.  **MVP**: Develop the Core Portal (Auth, Candidate Upload, Basic Matching).
