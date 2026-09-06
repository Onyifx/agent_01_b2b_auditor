import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication

GMAIL_USER = os.getenv("GMAIL_USER", "")
GMAIL_APP_PASSWORD = os.getenv("GMAIL_APP_PASSWORD", "")

def send_audit_email(recipient_email: str, domain: str, pdf_path: str, checkout_url: str = "") -> dict:
    """Sends audit PDF report with Paystack checkout link using Gmail SMTP for free."""
    if not GMAIL_USER or not GMAIL_APP_PASSWORD:
        raise ValueError("Missing GMAIL_USER or GMAIL_APP_PASSWORD environment variables.")

    if not os.path.exists(pdf_path):
        raise FileNotFoundError(f"PDF file not found at {pdf_path}")

    msg = MIMEMultipart()
    msg["From"] = f"B2B Audit Team <{GMAIL_USER}>"
    msg["To"] = recipient_email
    msg["Subject"] = f"Website Audit Report for {domain}"

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

    msg.attach(MIMEText(html_content, "html"))

    # Attach PDF report
    with open(pdf_path, "rb") as f:
        pdf_attachment = MIMEApplication(f.read(), _subtype="pdf")
        pdf_attachment.add_header("Content-Disposition", "attachment", filename=os.path.basename(pdf_path))
        msg.attach(pdf_attachment)

    # Connect to Gmail SMTP server on port 465
    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(GMAIL_USER, GMAIL_APP_PASSWORD)
        server.send_message(msg)

    print(f"✓ Email successfully sent to {recipient_email} via Gmail SMTP")
    return {"status": "sent", "recipient": recipient_email}