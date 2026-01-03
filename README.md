# Email Verification Integration for Lead Gen

This adds SMTP-level email verification to your lead generation workflow, similar to how Hunter.io verifies emails.

## How Email Verification Works

1. **Syntax Check** - Validates email format
2. **MX Record Lookup** - Verifies domain has mail servers
3. **SMTP Handshake** - Connects to mail server and asks "does this mailbox exist?"

## Components

### 1. `email_verifier.py` - SMTP Verification Microservice

A Python service that performs the actual SMTP handshake. Deploy this as:
- AWS Lambda
- Google Cloud Function  
- Azure Function
- Your own server (Flask/FastAPI)

### 2. `lead_gen_with_email_verification` - Updated Zoho Deluge Script

Enhanced lead_gen script that:
- Validates email syntax (in Deluge)
- Checks MX records via Google DNS API (in Deluge)
- Calls your SMTP verification service for full verification

## Setup Instructions

### Step 1: Deploy the Email Verifier

#### Option A: AWS Lambda

```bash
# Install dependencies
pip install dnspython -t .

# Zip everything
zip -r email_verifier.zip email_verifier.py dns* 

# Upload to Lambda
# Handler: email_verifier.lambda_handler
# Runtime: Python 3.11+
# Timeout: 30 seconds
# Memory: 128 MB
```

Create an API Gateway trigger and note the URL.

#### Option B: Google Cloud Function

```bash
gcloud functions deploy verify-email \
  --runtime python311 \
  --trigger-http \
  --allow-unauthenticated \
  --entry-point verify_email_gcf \
  --source .
```

#### Option C: Run Locally (for testing)

```bash
pip install dnspython fastapi uvicorn

# Uncomment the FastAPI section in email_verifier.py, then:
uvicorn email_verifier:app --reload --port 8000

# Test: http://localhost:8000/verify?email=test@example.com
```

### Step 2: Configure Zoho CRM

Add a new Organization Variable in Zoho CRM:

- **Variable Name:** `EMAIL_VERIFY_URL`
- **Value:** Your deployed endpoint URL (e.g., `https://xxxxx.execute-api.us-east-1.amazonaws.com/verify`)

### Step 3: Update Your Lead Gen Function

Replace your existing `lead_gen` code with the contents of `lead_gen_with_email_verification`.

## Output Format

Each contact now includes an `email_verification` field:

```json
{
  "primary_contact": {
    "name": "Chris Lindsay",
    "email": "chris.lindsay@blossombi.com",
    "email_verification": {
      "email": "chris.lindsay@blossombi.com",
      "syntax_valid": true,
      "mx_found": true,
      "smtp_verified": true,
      "status": "valid",
      "score": 100,
      "message": "Email address verified successfully"
    }
  }
}
```

### Verification Statuses

| Status | Score | Meaning |
|--------|-------|---------|
| `valid` | 80-100 | Email verified, safe to send |
| `risky` | 50-70 | MX valid but can't confirm mailbox (catch-all server) |
| `invalid` | 0-20 | Email doesn't exist or domain has no mail servers |
| `unknown` | 30-50 | Couldn't determine (server blocking, timeout) |

## Testing

```bash
# Test the verifier directly
python email_verifier.py chris.lindsay@blossombi.com
```

## Notes

- **Rate Limiting**: Mail servers may block IPs making too many verification requests. For high volume, consider using Hunter.io API or similar service.
- **Catch-All Servers**: Some domains accept all emails - verification can't determine if specific mailbox exists.
- **Firewalls**: Some corporate mail servers block SMTP verification attempts.
