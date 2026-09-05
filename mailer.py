import os
import resend
from dotenv import load_dotenv

load_dotenv()

RESEND_API_KEY = os.getenv("RESEND_API_KEY")

def send_audit_email(recipient_email: str, domain: str, pdf_path: str) -> dict:
    """
    Sends the generated PDF audit report to the target email address using Resend.
    """
    if not RESEND_API_KEY or RESEND_API_KEY == "your_resend_api_key_here":
        raise ValueError("Missing or default RESEND_API_KEY in .env file.")

    resend.api_key = RESEND_API_KEY

    # Read PDF file as byte list for Resend attachment payload
    with open(pdf_path, "rb") as f:
        pdf_bytes = list(f.read())

    params: resend.Emails.SendParams = {
        "from": "onboarding@resend.dev",  # Resend default testing sender
        "to": [recipient_email],
        "subject": f"Technical Audit & Performance Report: {domain}",
        "html": f"""
            <h2>B2B Audit Report for {domain}</h2>
            <p>Hello,</p>
            <p>Our automated engine completed a technical performance and security scan for <strong>{domain}</strong>.</p>
            <p>Please find your full executive PDF report attached.</p>
            <br>
            <p>Best regards,<br><em>Automated B2B Audit Team</em></p>
        """,
        "attachments": [
            {
                "filename": f"{domain}_audit_report.pdf",
                "content": pdf_bytes
            }
        ]
    }

    response = resend.Emails.send(params)
    print(f"✓ Email sent successfully to {recipient_email} (ID: {response.get('id')})")
    return response

if __name__ == "__main__":
    test_email = "delivered@resend.dev"  # Default test address provided by Resend
    test_domain = "example.com"
    pdf_file = "test_audit_report.pdf"

    if os.path.exists(pdf_file):
        print(f"Sending audit report to {test_email}...")
        send_audit_email(test_email, test_domain, pdf_file)
    else:
        print(f"Error: {pdf_file} not found. Run pdf_generator.py first.")