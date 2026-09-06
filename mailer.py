import os
import hmac
import hashlib
import requests
import uvicorn
from fastapi import FastAPI, BackgroundTasks, HTTPException, Request, Header
from pydantic import BaseModel
from auditor import audit_website
from analyzer import analyze_audit_data
from pdf_generator import generate_pdf_report
from mailer import send_audit_email
from db import supabase
from paystack_service import create_paystack_checkout

app = FastAPI(title="B2B Website Auditor Agent API")

PAYSTACK_SECRET_KEY = os.getenv("PAYSTACK_SECRET_KEY", "")

class AuditRequest(BaseModel):
    domain: str
    contact_email: str
    business_name: str = ""
    niche: str = ""
    city: str = ""

class PaymentLinkRequest(BaseModel):
    lead_id: str

def process_full_audit(lead_id: str, domain: str, contact_email: str):
    """Audits site, generates AI summary & PDF, generates Paystack link, and sends email pitch."""
    try:
        supabase.table("leads").update({"status": "PROCESSING"}).eq("id", lead_id).execute()

        # 1. Technical Audit & Gemini Analysis
        audit_data = audit_website(domain)
        ai_analysis = analyze_audit_data(audit_data)
        
        # 2. Render PDF Report
        pdf_filename = f"{domain.replace('.', '_')}_audit.pdf"
        generate_pdf_report(audit_data, ai_analysis, pdf_filename)

        # 3. Create Paystack Checkout Link automatically
        try:
            checkout_url = create_paystack_checkout(lead_id, domain, contact_email)
        except Exception as e:
            print(f"  ⚠️ Checkout creation notice: {str(e)}")
            checkout_url = ""

        # 4. Email PDF with embedded checkout button
        send_audit_email(contact_email, domain, pdf_filename, checkout_url=checkout_url)

        # 5. Log audit metrics to Supabase
        supabase.table("audit_logs").insert({
            "lead_id": lead_id,
            "load_time_seconds": audit_data.get("load_time_seconds"),
            "is_ssl": audit_data.get("is_ssl"),
            "missing_title": audit_data.get("missing_title"),
            "missing_viewport": audit_data.get("missing_viewport"),
            "top_errors": audit_data.get("top_errors"),
            "pdf_generated": True,
        }).execute()

        supabase.table("leads").update({"status": "AUDITED"}).eq("id", lead_id).execute()

        if os.path.exists(pdf_filename):
            os.remove(pdf_filename)

        print(f"✓ Completed end-to-end audit for {domain}")

    except Exception as e:
        print(f"❌ Error processing audit for {domain}: {str(e)}")
        supabase.table("leads").update({"status": "FAILED"}).eq("id", lead_id).execute()

@app.get("/")
def health_check():
    return {"status": "online", "service": "B2B Website Auditor API"}

@app.post("/audit")
def trigger_audit(req: AuditRequest, background_tasks: BackgroundTasks):
    existing = supabase.table("leads").select("id").eq("domain", req.domain).execute()

    if existing.data:
        lead_id = existing.data[0]["id"]
        supabase.table("leads").update({"status": "PROCESSING"}).eq("id", lead_id).execute()
    else:
        new_lead = supabase.table("leads").insert({
            "domain": req.domain,
            "contact_email": req.contact_email,
            "business_name": req.business_name,
            "niche": req.niche,
            "city": req.city,
            "status": "PROCESSING"
        }).execute()
        lead_id = new_lead.data[0]["id"]

    background_tasks.add_task(process_full_audit, lead_id, req.domain, req.contact_email)

    return {
        "message": "Audit process queued successfully",
        "lead_id": lead_id,
        "domain": req.domain,
        "status": "PROCESSING"
    }

@app.post("/create-checkout")
def generate_payment_link(req: PaymentLinkRequest):
    lead = supabase.table("leads").select("id, domain, contact_email").eq("id", req.lead_id).execute()
    if not lead.data:
        raise HTTPException(status_code=404, detail="Lead not found")

    domain = lead.data[0]["domain"]
    contact_email = lead.data[0]["contact_email"]

    try:
        checkout_url = create_paystack_checkout(req.lead_id, domain, contact_email)
        return {"checkout_url": checkout_url}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/verify-payment/{reference}")
def verify_payment(reference: str):
    if not PAYSTACK_SECRET_KEY:
        raise HTTPException(status_code=500, detail="PAYSTACK_SECRET_KEY missing")

    url = f"https://api.paystack.co/transaction/verify/{reference}"
    headers = {"Authorization": f"Bearer {PAYSTACK_SECRET_KEY}"}

    try:
        response = requests.get(url, headers=headers)
        res_data = response.json()

        if response.status_code == 200 and res_data.get("status") and res_data.get("data", {}).get("status") == "success":
            transaction_data = res_data["data"]
            metadata = transaction_data.get("metadata", {})
            lead_id = metadata.get("lead_id")
            amount = transaction_data.get("amount", 0) / 100.0
            customer_email = transaction_data.get("customer", {}).get("email", "")

            if lead_id:
                supabase.table("sales").insert({
                    "lead_id": lead_id,
                    "customer_email": customer_email,
                    "amount": amount,
                    "status": "PAID",
                    "stripe_session_id": reference
                }).execute()
                
                supabase.table("leads").update({"status": "CONVERTED"}).eq("id", lead_id).execute()
                print(f"💰 Direct verification succeeded for lead ID: {lead_id}")

            return {"status": "verified", "lead_id": lead_id, "amount": amount, "reference": reference}
        else:
            return {"status": "unverified", "message": res_data.get("message", "Transaction incomplete")}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/webhook/paystack")
async def paystack_webhook(request: Request, x_paystack_signature: str = Header(None)):
    payload = await request.body()

    if PAYSTACK_SECRET_KEY and x_paystack_signature:
        computed_signature = hmac.new(
            PAYSTACK_SECRET_KEY.encode('utf-8'),
            payload,
            hashlib.sha512
        ).hexdigest()

        if computed_signature != x_paystack_signature:
            raise HTTPException(status_code=400, detail="Invalid Paystack signature")

    data = await request.json()
    if data.get("event") == "charge.success":
        transaction_data = data.get("data", {})
        metadata = transaction_data.get("metadata", {})
        lead_id = metadata.get("lead_id")
        reference = transaction_data.get("reference")
        amount = transaction_data.get("amount", 4500000) / 100.0
        customer_email = transaction_data.get("customer", {}).get("email", "")

        if lead_id:
            supabase.table("sales").insert({
                "lead_id": lead_id,
                "customer_email": customer_email,
                "amount": amount,
                "status": "PAID",
                "stripe_session_id": reference
            }).execute()
            supabase.table("leads").update({"status": "CONVERTED"}).eq("id", lead_id).execute()
            print(f"💰 Paystack conversion logged via webhook for lead ID: {lead_id}")

    return {"status": "success"}

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000)