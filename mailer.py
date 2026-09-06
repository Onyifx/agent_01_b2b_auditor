import os
import resend
from dotenv import load_dotenv

load_dotenv()

resend.api_key = os.getenv("RESEND_API_KEY")

def send_audit_email(recipient_email: str, domain: str, pdf_path: str, checkout_url: str = "") -> dict:
    """Sends audit PDF report with an optional Paystack checkout URL via Resend."""
    if not os.path.exists(pdf_path):
        raise FileNotFoundError(f"PDF file not found at {pdf_path}")

    with open(pdf_path, "rb") as f:
        pdf_bytes = list(f.read())

    subject = f"Website Audit Report for {domain}"

    button_html = f'''
    <p style="margin-top: 20px;">
        <a href="{checkout_url}" style="background-color: #00C853; color: white; padding: 12px 24px; text-decoration: none; font-weight: bold; border-radius: 5px; display: inline-block;">
            Fix These Issues Now
        </a>
    </p>
    ''' if checkout_url else ""

    html_content = f"""
    <h2>Website Audit Summary for {domain}</h2>
    <p>We've completed a full technical performance and conversion audit of your website.</p>
    <p>Please find your detailed PDF audit report attached to this email.</p>
    {button_html}
    <p>Best regards,<br>B2B Audit Team</p>
    """

    params = {
        "from": "Audit Team <onboarding@resend.dev>",
        "to": [recipient_email],
        "subject": subject,
        "html": html_content,
        "attachments": [
            {
                "filename": os.path.basename(pdf_path),
                "content": pdf_bytes
            }
        ]
    }

    response = resend.Emails.send(params)
    return response