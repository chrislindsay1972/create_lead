"""
Email Verification Microservice
Deploy this as a serverless function (AWS Lambda, Google Cloud Function, Vercel, etc.)
or run as a simple Flask/FastAPI server.

This performs the SMTP handshake to verify if an email address exists.
"""

import socket
import dns.resolver
import re
from typing import Optional
import json


def verify_email(email: str) -> dict:
    """
    Verify an email address using multiple checks:
    1. Syntax validation
    2. MX record lookup
    3. SMTP verification (the actual handshake)
    """
    result = {
        "email": email,
        "syntax_valid": False,
        "mx_found": False,
        "mx_records": [],
        "smtp_check": False,
        "smtp_response": None,
        "status": "unknown",  # valid, invalid, risky, unknown
        "score": 0,
        "message": ""
    }
    
    # Step 1: Syntax validation
    email_regex = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    if not re.match(email_regex, email):
        result["message"] = "Invalid email syntax"
        result["status"] = "invalid"
        return result
    
    result["syntax_valid"] = True
    result["score"] += 20
    
    # Extract domain
    domain = email.split('@')[1]
    
    # Step 2: MX Record Lookup
    try:
        mx_records = dns.resolver.resolve(domain, 'MX')
        mx_hosts = sorted([(r.preference, str(r.exchange).rstrip('.')) for r in mx_records])
        result["mx_found"] = True
        result["mx_records"] = [mx[1] for mx in mx_hosts]
        result["score"] += 30
    except (dns.resolver.NoAnswer, dns.resolver.NXDOMAIN, dns.resolver.NoNameservers) as e:
        result["message"] = f"No MX records found for domain: {domain}"
        result["status"] = "invalid"
        return result
    except Exception as e:
        result["message"] = f"DNS lookup failed: {str(e)}"
        result["status"] = "unknown"
        return result
    
    # Step 3: SMTP Verification
    if not mx_hosts:
        result["message"] = "No MX records to verify against"
        result["status"] = "unknown"
        return result
    
    # Try each MX server in order of preference
    smtp_verified = False
    smtp_response = None
    is_catch_all = False
    
    for preference, mx_host in mx_hosts:
        try:
            smtp_result = smtp_check(mx_host, email, domain)
            smtp_response = smtp_result
            
            if smtp_result["success"]:
                smtp_verified = True
                is_catch_all = smtp_result.get("catch_all", False)
                break
            elif smtp_result.get("definitive_failure", False):
                # Server definitively said the user doesn't exist
                result["smtp_check"] = False
                result["smtp_response"] = smtp_result
                result["status"] = "invalid"
                result["message"] = smtp_result.get("message", "Email address does not exist")
                return result
                
        except Exception as e:
            smtp_response = {"error": str(e)}
            continue
    
    result["smtp_response"] = smtp_response
    
    if smtp_verified:
        result["smtp_check"] = True
        result["score"] += 50
        
        if is_catch_all:
            result["status"] = "risky"
            result["message"] = "Server accepts all emails (catch-all) - cannot definitively verify"
            result["score"] -= 20
        else:
            result["status"] = "valid"
            result["message"] = "Email address verified successfully"
    else:
        result["status"] = "unknown"
        result["message"] = "Could not verify via SMTP - server may be blocking verification"
    
    return result


def smtp_check(mx_host: str, email: str, domain: str, timeout: int = 10) -> dict:
    """
    Perform SMTP handshake to verify email exists.
    
    The SMTP conversation:
    1. Connect to MX server on port 25
    2. EHLO/HELO - Introduce ourselves
    3. MAIL FROM - Specify sender (for the test)
    4. RCPT TO - Ask if recipient exists (THIS IS THE KEY CHECK)
    5. QUIT - Close connection
    
    Response codes:
    - 250: OK (email exists)
    - 251: User not local, will forward
    - 252: Cannot verify, but will accept
    - 550: User not found (email doesn't exist)
    - 551: User not local
    - 552: Storage exceeded
    - 553: Mailbox name not allowed
    - 450/451/452: Temporary failures
    """
    result = {
        "success": False,
        "catch_all": False,
        "mx_host": mx_host,
        "message": "",
        "smtp_code": None,
        "definitive_failure": False
    }
    
    try:
        # Connect to SMTP server
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        sock.connect((mx_host, 25))
        
        # Read greeting
        response = sock.recv(1024).decode('utf-8', errors='ignore')
        if not response.startswith('220'):
            result["message"] = f"Bad greeting: {response}"
            sock.close()
            return result
        
        # Send EHLO
        sock.send(f"EHLO verify.local\r\n".encode())
        response = sock.recv(1024).decode('utf-8', errors='ignore')
        if not (response.startswith('250') or response.startswith('220')):
            # Try HELO if EHLO fails
            sock.send(f"HELO verify.local\r\n".encode())
            response = sock.recv(1024).decode('utf-8', errors='ignore')
        
        # Send MAIL FROM
        sock.send(f"MAIL FROM:<verify@verify.local>\r\n".encode())
        response = sock.recv(1024).decode('utf-8', errors='ignore')
        if not response.startswith('250'):
            result["message"] = f"MAIL FROM rejected: {response}"
            sock.send(b"QUIT\r\n")
            sock.close()
            return result
        
        # Send RCPT TO - THIS IS THE ACTUAL VERIFICATION
        sock.send(f"RCPT TO:<{email}>\r\n".encode())
        response = sock.recv(1024).decode('utf-8', errors='ignore')
        result["smtp_code"] = response[:3] if len(response) >= 3 else None
        
        # Check for catch-all by testing a random non-existent address
        import random
        import string
        random_local = ''.join(random.choices(string.ascii_lowercase, k=20))
        fake_email = f"{random_local}@{domain}"
        
        sock.send(f"RCPT TO:<{fake_email}>\r\n".encode())
        catch_all_response = sock.recv(1024).decode('utf-8', errors='ignore')
        
        # Close connection
        sock.send(b"QUIT\r\n")
        sock.close()
        
        # Analyze responses
        if response.startswith('250') or response.startswith('251'):
            result["success"] = True
            result["message"] = "Email accepted by server"
            
            # Check if catch-all (accepts everything)
            if catch_all_response.startswith('250') or catch_all_response.startswith('251'):
                result["catch_all"] = True
                result["message"] = "Server is catch-all (accepts all addresses)"
                
        elif response.startswith('252'):
            result["success"] = True
            result["catch_all"] = True
            result["message"] = "Server cannot verify but will accept"
            
        elif response.startswith('550') or response.startswith('551') or response.startswith('553'):
            result["success"] = False
            result["definitive_failure"] = True
            result["message"] = f"Email rejected: {response.strip()}"
            
        elif response.startswith('450') or response.startswith('451') or response.startswith('452'):
            result["success"] = False
            result["message"] = f"Temporary failure: {response.strip()}"
            
        else:
            result["message"] = f"Unexpected response: {response.strip()}"
            
    except socket.timeout:
        result["message"] = f"Connection timeout to {mx_host}"
    except socket.error as e:
        result["message"] = f"Socket error: {str(e)}"
    except Exception as e:
        result["message"] = f"Error: {str(e)}"
    
    return result


# === FastAPI Server (for deployment) ===
# Uncomment below to run as a web service

# from fastapi import FastAPI, HTTPException
# from pydantic import BaseModel
# 
# app = FastAPI(title="Email Verification API")
# 
# class EmailRequest(BaseModel):
#     email: str
# 
# @app.post("/verify")
# async def verify(request: EmailRequest):
#     return verify_email(request.email)
# 
# @app.get("/verify")
# async def verify_get(email: str):
#     return verify_email(email)


# === AWS Lambda Handler ===
def lambda_handler(event, context):
    """AWS Lambda entry point"""
    # Handle API Gateway event
    if 'queryStringParameters' in event and event['queryStringParameters']:
        email = event['queryStringParameters'].get('email', '')
    elif 'body' in event and event['body']:
        body = json.loads(event['body']) if isinstance(event['body'], str) else event['body']
        email = body.get('email', '')
    else:
        email = event.get('email', '')
    
    if not email:
        return {
            'statusCode': 400,
            'body': json.dumps({'error': 'Email parameter required'})
        }
    
    result = verify_email(email)
    
    return {
        'statusCode': 200,
        'headers': {'Content-Type': 'application/json'},
        'body': json.dumps(result)
    }


# === Google Cloud Function Handler ===
def verify_email_gcf(request):
    """Google Cloud Function entry point"""
    email = request.args.get('email') or request.get_json().get('email', '')
    
    if not email:
        return json.dumps({'error': 'Email parameter required'}), 400
    
    return json.dumps(verify_email(email)), 200, {'Content-Type': 'application/json'}


# === CLI Testing ===
if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        test_email = sys.argv[1]
    else:
        test_email = "chris.lindsay@blossombi.com"
    
    print(f"\nVerifying: {test_email}\n")
    result = verify_email(test_email)
    print(json.dumps(result, indent=2))
