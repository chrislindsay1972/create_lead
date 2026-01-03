"""
Multi-Signal Email Validation
Validates emails using multiple sources WITHOUT SMTP:
1. Gravatar (has the email been used to create an avatar?)
2. Google Search (does the email appear publicly?)
3. LinkedIn cross-reference (does this person exist at this company?)
4. Company website (does the person appear on team page?)
5. Email pattern matching (is it consistent with known company format?)
"""

import hashlib
import json
import urllib.request
import urllib.parse
import re
from typing import Optional


def check_gravatar(email: str) -> dict:
    """
    Check if email has a Gravatar profile.
    Gravatar uses MD5 hash of lowercase email.
    If a custom avatar exists, the email has been used somewhere.
    """
    result = {
        "has_gravatar": False,
        "profile_url": None,
        "confidence_boost": 0
    }
    
    try:
        email_hash = hashlib.md5(email.lower().strip().encode()).hexdigest()
        
        # Check if profile exists (not default)
        # d=404 means return 404 if no custom gravatar
        gravatar_url = f"https://www.gravatar.com/avatar/{email_hash}?d=404"
        
        req = urllib.request.Request(gravatar_url, method='HEAD')
        req.add_header('User-Agent', 'Mozilla/5.0')
        
        try:
            response = urllib.request.urlopen(req, timeout=5)
            if response.status == 200:
                result["has_gravatar"] = True
                result["profile_url"] = f"https://www.gravatar.com/{email_hash}"
                result["confidence_boost"] = 15
        except urllib.error.HTTPError as e:
            if e.code == 404:
                # No gravatar - doesn't mean email is invalid
                pass
                
    except Exception as e:
        result["error"] = str(e)
    
    return result


def check_email_pattern(email: str, known_emails: list = None, company_domain: str = None) -> dict:
    """
    Analyze email pattern and compare to known patterns from the company.
    """
    result = {
        "pattern_detected": None,
        "matches_known_pattern": False,
        "confidence_boost": 0
    }
    
    if not email or '@' not in email:
        return result
    
    local_part, domain = email.lower().split('@')
    
    # Detect pattern type
    patterns = {
        "firstname.lastname": r'^[a-z]+\.[a-z]+$',
        "firstnamelastname": r'^[a-z]{4,}$',  # Could be combined
        "f.lastname": r'^[a-z]\.[a-z]+$',
        "firstname_lastname": r'^[a-z]+_[a-z]+$',
        "firstname": r'^[a-z]{2,15}$',
        "flastname": r'^[a-z][a-z]+$',  # First initial + lastname
    }
    
    for pattern_name, regex in patterns.items():
        if re.match(regex, local_part):
            result["pattern_detected"] = pattern_name
            break
    
    # If we have known emails from this company, check if pattern matches
    if known_emails and len(known_emails) > 0:
        known_patterns = []
        for ke in known_emails:
            if '@' in ke:
                kl, kd = ke.lower().split('@')
                for pn, regex in patterns.items():
                    if re.match(regex, kl):
                        known_patterns.append(pn)
                        break
        
        if result["pattern_detected"] and result["pattern_detected"] in known_patterns:
            result["matches_known_pattern"] = True
            result["confidence_boost"] = 20
    
    # Common professional patterns get a small boost
    if result["pattern_detected"] in ["firstname.lastname", "f.lastname", "firstname_lastname"]:
        result["confidence_boost"] += 5
    
    return result


def extract_name_from_email(email: str) -> dict:
    """
    Try to extract a probable name from an email address.
    """
    result = {
        "probable_first_name": None,
        "probable_last_name": None,
        "full_name_guess": None
    }
    
    if not email or '@' not in email:
        return result
    
    local_part = email.lower().split('@')[0]
    
    # firstname.lastname
    if '.' in local_part:
        parts = local_part.split('.')
        if len(parts) == 2:
            result["probable_first_name"] = parts[0].title()
            result["probable_last_name"] = parts[1].title()
            result["full_name_guess"] = f"{parts[0].title()} {parts[1].title()}"
    
    # firstname_lastname
    elif '_' in local_part:
        parts = local_part.split('_')
        if len(parts) == 2:
            result["probable_first_name"] = parts[0].title()
            result["probable_last_name"] = parts[1].title()
            result["full_name_guess"] = f"{parts[0].title()} {parts[1].title()}"
    
    return result


def validate_email_multi_signal(
    email: str,
    person_name: str = None,
    company_name: str = None,
    job_title: str = None,
    known_company_emails: list = None,
    perplexity_api_key: str = None
) -> dict:
    """
    Validate email using multiple signals.
    Returns confidence score and evidence.
    """
    result = {
        "email": email,
        "is_valid_syntax": False,
        "confidence_score": 0,
        "confidence_level": "low",  # low, medium, high
        "signals": {},
        "evidence": [],
        "recommendation": ""
    }
    
    if not email or '@' not in email:
        result["recommendation"] = "Invalid email format"
        return result
    
    email = email.lower().strip()
    local_part, domain = email.split('@')
    
    # Basic syntax check
    email_regex = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    if not re.match(email_regex, email):
        result["recommendation"] = "Invalid email syntax"
        return result
    
    result["is_valid_syntax"] = True
    result["confidence_score"] = 10
    result["evidence"].append("Valid email syntax")
    
    # Signal 1: Gravatar check
    gravatar_result = check_gravatar(email)
    result["signals"]["gravatar"] = gravatar_result
    if gravatar_result["has_gravatar"]:
        result["confidence_score"] += gravatar_result["confidence_boost"]
        result["evidence"].append(f"Has Gravatar profile: {gravatar_result['profile_url']}")
    
    # Signal 2: Email pattern analysis
    pattern_result = check_email_pattern(email, known_company_emails, domain)
    result["signals"]["pattern"] = pattern_result
    if pattern_result["pattern_detected"]:
        result["confidence_score"] += pattern_result["confidence_boost"]
        result["evidence"].append(f"Email follows '{pattern_result['pattern_detected']}' pattern")
        if pattern_result["matches_known_pattern"]:
            result["evidence"].append("Pattern matches other known emails from this company")
    
    # Signal 3: Name extraction and cross-reference
    name_extraction = extract_name_from_email(email)
    result["signals"]["name_extraction"] = name_extraction
    
    if person_name and name_extraction["full_name_guess"]:
        # Compare provided name with extracted name
        provided_lower = person_name.lower()
        extracted_lower = name_extraction["full_name_guess"].lower()
        
        if provided_lower == extracted_lower:
            result["confidence_score"] += 25
            result["evidence"].append(f"Email name matches provided name: {person_name}")
        elif name_extraction["probable_first_name"] and name_extraction["probable_first_name"].lower() in provided_lower:
            result["confidence_score"] += 15
            result["evidence"].append(f"Email first name matches: {name_extraction['probable_first_name']}")
    
    # Signal 4: Web search validation (using Perplexity if available)
    if perplexity_api_key and (person_name or company_name):
        web_evidence = search_web_for_validation(
            email, person_name, company_name, job_title, perplexity_api_key
        )
        result["signals"]["web_search"] = web_evidence
        result["confidence_score"] += web_evidence.get("confidence_boost", 0)
        if web_evidence.get("evidence"):
            result["evidence"].extend(web_evidence["evidence"])
    
    # Calculate final confidence level
    score = result["confidence_score"]
    if score >= 70:
        result["confidence_level"] = "high"
        result["recommendation"] = "Email likely valid - multiple signals confirm"
    elif score >= 40:
        result["confidence_level"] = "medium"
        result["recommendation"] = "Email possibly valid - some confirming signals"
    else:
        result["confidence_level"] = "low"
        result["recommendation"] = "Email uncertain - limited validation signals"
    
    return result


def search_web_for_validation(
    email: str,
    person_name: str,
    company_name: str,
    job_title: str,
    api_key: str
) -> dict:
    """
    Use Perplexity to search for evidence that validates the email.
    Looks for:
    - LinkedIn profile confirming person works at company
    - Email appearing on public pages
    - Person mentioned in company news/press
    """
    result = {
        "searched": False,
        "confidence_boost": 0,
        "evidence": [],
        "linkedin_found": False,
        "company_page_found": False,
        "email_found_publicly": False
    }
    
    if not api_key:
        return result
    
    # Build search query
    search_parts = []
    if person_name:
        search_parts.append(person_name)
    if company_name:
        search_parts.append(company_name)
    if job_title:
        search_parts.append(job_title)
    
    if not search_parts:
        return result
    
    prompt = f"""Search the web to verify if this person and email are legitimate:

Email: {email}
Name: {person_name or 'Unknown'}
Company: {company_name or 'Unknown'}
Job Title: {job_title or 'Unknown'}

Please search for:
1. LinkedIn profile for {person_name or 'this person'} at {company_name or 'this company'}
2. The exact email "{email}" appearing on any public webpage
3. {person_name or 'This person'} mentioned on {company_name or 'company'}'s website (team page, about page, news)
4. Any news articles or press releases mentioning this person at this company

Return ONLY a valid JSON object with no markdown:
{{
    "person_exists_at_company": true/false,
    "linkedin_profile_found": true/false,
    "linkedin_url": "url or null",
    "email_found_publicly": true/false,
    "email_source_url": "url where email was found or null",
    "company_page_mention": true/false,
    "company_page_url": "url or null",
    "news_mentions": true/false,
    "confidence": "high/medium/low",
    "notes": "brief explanation of findings"
}}"""

    try:
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        
        body = {
            "model": "sonar",
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0
        }
        
        data = json.dumps(body).encode('utf-8')
        req = urllib.request.Request(
            "https://api.perplexity.ai/chat/completions",
            data=data,
            headers=headers,
            method='POST'
        )
        
        response = urllib.request.urlopen(req, timeout=30)
        resp_data = json.loads(response.read().decode('utf-8'))
        
        if 'choices' in resp_data and len(resp_data['choices']) > 0:
            content = resp_data['choices'][0]['message']['content']
            
            # Extract JSON from response
            start = content.find('{')
            end = content.rfind('}')
            if start >= 0 and end > start:
                json_str = content[start:end+1]
                web_data = json.loads(json_str)
                
                result["searched"] = True
                
                # Process findings
                if web_data.get("person_exists_at_company"):
                    result["confidence_boost"] += 20
                    result["evidence"].append(f"Web search confirms {person_name} works at {company_name}")
                
                if web_data.get("linkedin_profile_found"):
                    result["linkedin_found"] = True
                    result["confidence_boost"] += 15
                    url = web_data.get("linkedin_url", "LinkedIn")
                    result["evidence"].append(f"LinkedIn profile found: {url}")
                
                if web_data.get("email_found_publicly"):
                    result["email_found_publicly"] = True
                    result["confidence_boost"] += 25
                    url = web_data.get("email_source_url", "web")
                    result["evidence"].append(f"Email found publicly at: {url}")
                
                if web_data.get("company_page_mention"):
                    result["company_page_found"] = True
                    result["confidence_boost"] += 15
                    url = web_data.get("company_page_url", "company website")
                    result["evidence"].append(f"Person found on company website: {url}")
                
                if web_data.get("notes"):
                    result["notes"] = web_data["notes"]
                    
    except Exception as e:
        result["error"] = str(e)
    
    return result


# CLI Testing
if __name__ == "__main__":
    import sys
    import os
    
    # Test email
    test_email = sys.argv[1] if len(sys.argv) > 1 else "chris.lindsay@blossombi.com"
    test_name = sys.argv[2] if len(sys.argv) > 2 else "Chris Lindsay"
    test_company = sys.argv[3] if len(sys.argv) > 3 else "Blossom BI"
    
    # Get Perplexity API key from environment
    perplexity_key = os.environ.get("PERPLEXITY_API_KEY")
    
    print(f"\n{'='*60}")
    print(f"Multi-Signal Email Validation")
    print(f"{'='*60}")
    print(f"Email:   {test_email}")
    print(f"Name:    {test_name}")
    print(f"Company: {test_company}")
    print(f"{'='*60}\n")
    
    result = validate_email_multi_signal(
        email=test_email,
        person_name=test_name,
        company_name=test_company,
        job_title="CFO",
        perplexity_api_key=perplexity_key
    )
    
    print(json.dumps(result, indent=2))
    
    print(f"\n{'='*60}")
    print(f"RESULT: {result['confidence_level'].upper()} confidence ({result['confidence_score']}%)")
    print(f"{'='*60}")
    print(f"Recommendation: {result['recommendation']}")
    print(f"\nEvidence found:")
    for e in result['evidence']:
        print(f"  ✓ {e}")
