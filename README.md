# Email Verification Integration for Lead Gen

This adds **multi-signal email verification** to your lead generation workflow - the same approach Hunter.io uses, without needing their API.

## Two Verification Approaches

### Approach 1: SMTP Handshake (Like Hunter.io)
1. **Syntax Check** - Validates email format
2. **MX Record Lookup** - Verifies domain has mail servers
3. **SMTP Handshake** - Connects to mail server and asks "does this mailbox exist?"

⚠️ **Limitation**: Major providers (Microsoft 365, Gmail) block SMTP verification from cloud IPs.

### Approach 2: Multi-Signal Validation (Recommended) ✅
1. **Syntax Check** - Valid email format
2. **MX Record Lookup** - Domain has mail servers
3. **Email Pattern Analysis** - Follows professional pattern (firstname.lastname)
4. **Name Matching** - Email matches provided contact name
5. **Gravatar Check** - Email has been used to create an avatar
6. **LinkedIn/Web Search** - Person exists at company (via Perplexity)

## Components

### 1. `email_verifier.py` - SMTP Verification Microservice (Optional)

A Python service that performs the actual SMTP handshake. Deploy this as:
- AWS Lambda
- Google Cloud Function  
- Azure Function
- Your own server (Flask/FastAPI)

### 2. `email_validator_multi_signal.py` - Multi-Signal Validator

Standalone Python validator using multiple signals - no external service needed.

### 3. `lead_gen_with_multi_signal_validation` - Recommended Zoho Deluge Script ⭐

Enhanced lead_gen script with **built-in multi-signal validation**:
- All validation runs directly in Deluge (no external service needed!)
- Uses Perplexity (which you already have) for LinkedIn/web validation
- Returns confidence scores and evidence for each email

### 4. `lead_gen_with_email_verification` - SMTP-based Zoho Deluge Script

Alternative script that uses external SMTP verification service.

## Setup Instructions

### Option A: Multi-Signal Validation (Recommended - No Setup Required!)

Simply replace your existing `lead_gen` code with `lead_gen_with_multi_signal_validation`.

**That's it!** The script uses:
- Google DNS API for MX checks (free, public)
- Gravatar API for email usage check (free, public)
- Your existing Perplexity API for LinkedIn/web validation

### Option B: SMTP Verification (Advanced)

If you want to also do SMTP handshake verification:

#### Step 1: Deploy the Email Verifier

**AWS Lambda:**
```bash
pip install dnspython -t .
zip -r email_verifier.zip email_verifier.py dns* 
# Upload to Lambda - Handler: email_verifier.lambda_handler
```

**Google Cloud Function:**
```bash
gcloud functions deploy verify-email \
  --runtime python311 \
  --trigger-http \
  --allow-unauthenticated \
  --entry-point verify_email_gcf
```

#### Step 2: Configure Zoho CRM

Add Organization Variable:
- **Variable Name:** `EMAIL_VERIFY_URL`
- **Value:** Your deployed endpoint URL

#### Step 3: Use SMTP Script

Replace your `lead_gen` code with `lead_gen_with_email_verification`.

## Output Format

Each contact now includes an `email_validation` field with detailed signals:

```json
{
  "primary_contact": {
    "name": "Chris Lindsay",
    "email": "chris.lindsay@blossombi.com",
    "job_title": "CFO",
    "email_validation": {
      "email": "chris.lindsay@blossombi.com",
      "syntax_valid": true,
      "mx_found": true,
      "confidence_score": 85,
      "confidence_level": "high",
      "evidence": [
        "Valid email syntax",
        "Domain has valid MX records",
        "Email follows professional 'firstname.lastname' pattern",
        "Email name matches provided name: Chris Lindsay",
        "Web search confirms Chris Lindsay works at Blossom BI",
        "LinkedIn profile found: https://linkedin.com/in/chrislindsay"
      ],
      "signals": {
        "syntax": {"valid": true},
        "mx_records": {"mx_found": true, "mx_records": ["mail.protection.outlook.com"]},
        "pattern": {"detected": "firstname.lastname"},
        "name_extraction": {"first_name": "Chris", "last_name": "Lindsay"},
        "gravatar": {"has_gravatar": false},
        "web_search": {
          "person_verified": true,
          "linkedin_found": true,
          "linkedin_url": "https://linkedin.com/in/chrislindsay",
          "email_found_publicly": false,
          "company_page_found": true
        }
      },
      "recommendation": "Email highly likely valid - multiple signals confirm"
    }
  }
}
```

### Confidence Levels

| Level | Score | Meaning |
|-------|-------|---------|
| `high` | 70+ | Multiple signals confirm - safe to use |
| `medium` | 45-69 | Some confirming signals - likely valid |
| `low-medium` | 25-44 | Limited validation - use with caution |
| `low` | 0-24 | Could not validate - verify manually |

### Signal Scoring

| Signal | Max Points | Description |
|--------|-----------|-------------|
| Syntax valid | +10 | Basic email format check |
| MX records found | +15 | Domain has mail servers |
| Professional pattern | +5 | firstname.lastname, etc. |
| Name matches email | +15-25 | Provided name matches extracted name |
| Has Gravatar | +15 | Email has been used to create avatar |
| LinkedIn found | +15 | Person's LinkedIn profile exists |
| Person verified at company | +20 | Web search confirms employment |
| Email found publicly | +25 | Email appears on indexed web pages |
| Company page mention | +15 | Person on company team/about page |

## Testing

```bash
# Test multi-signal validator
python3 email_validator_multi_signal.py "chris.lindsay@blossombi.com" "Chris Lindsay" "Blossom BI"

# Test SMTP verifier (may timeout for Microsoft/Google)
python3 email_verifier.py chris.lindsay@blossombi.com
```

## Why Multi-Signal is Better Than SMTP

| Factor | SMTP Verification | Multi-Signal |
|--------|------------------|--------------|
| Works with Microsoft 365 | ❌ Blocked | ✅ Yes |
| Works with Gmail/Google | ❌ Blocked | ✅ Yes |
| Requires deployment | ✅ Yes (external service) | ❌ No |
| Verifies person exists | ❌ No | ✅ Yes (LinkedIn) |
| Additional cost | Maybe (hosting) | ❌ None (uses existing Perplexity) |

## Notes

- **Rate Limiting**: Perplexity has rate limits - the script handles this gracefully
- **Catch-All Servers**: Multi-signal validation works even for catch-all domains by verifying the person exists
- **Best Results**: The more contact info you have (name, company, title), the better the validation
