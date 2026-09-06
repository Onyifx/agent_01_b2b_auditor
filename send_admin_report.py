import os
from datetime import datetime, timedelta, timezone
import resend
from db import supabase

resend.api_key = os.getenv("RESEND_API_KEY")
ADMIN_EMAIL = os.getenv("ADMIN_EMAIL")  # Set in GitHub Secrets or environment variables

def fetch_6hour_metrics():
    """Queries Supabase for activity logged in the past 6 hours."""
    six_hours_ago = (datetime.now(timezone.utc) - timedelta(hours=6)).isoformat()

    # 1. Leads discovered in last 6 hours
    leads_res = supabase.table("leads").select("id", count="exact").gte("created_at", six_hours_ago).execute()
    new_leads = leads_res.count if leads_res.count is not None else len(leads_res.data or [])

    # 2. Audits completed in last 6 hours
    audits_res = supabase.table("audit_logs").select("id", count="exact").gte("created_at", six_hours_ago).execute()
    audits_completed = audits_res.count if audits_res.count is not None else len(audits_res.data or [])

    # 3. Overall database pipeline totals
    total_leads = supabase.table("leads").select("id", count="exact").execute().count
    total_audited = supabase.table("leads").select("id", count="exact").eq("status", "AUDITED").execute().count
    total_converted = supabase.table("leads").select("id", count="exact").eq("status", "CONVERTED").execute().count

    # 4. Recent Revenue
    sales_res = supabase.table("sales").select("amount").gte("created_at", six_hours_ago).execute()
    revenue_6h = sum(item.get("amount", 0) for item in (sales_res.data or []))

    return {
        "new_leads": new_leads,
        "audits_completed": audits_completed,
        "total_leads": total_leads or 0,
        "total_audited": total_audited or 0,
        "total_converted": total_converted or 0,
        "revenue_6h": revenue_6h
    }

def send_admin_digest():
    """Formats and emails the 6-hour run summary to your personal inbox."""
    if not ADMIN_EMAIL:
        print("⚠️ ADMIN_EMAIL environment variable not set. Skipping admin update email.")
        return

    metrics = fetch_6hour_metrics()
    now_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    html_content = f"""
    <div style="font-family: Arial, sans-serif; padding: 20px; color: #333; max-width: 600px; border: 1px solid #e0e0e0; border-radius: 8px;">
        <h2 style="color: #0052CC; margin-top: 0;">🚀 6-Hour Engine Status Update</h2>
        <p style="font-size: 14px; color: #666;">Timestamp: <strong>{now_str}</strong></p>

        <hr style="border: None; border-top: 1px solid #eee; margin: 20px 0;" />

        <h3>📊 Last 6 Hours Activity:</h3>
        <ul>
            <li>🔍 <strong>Web Search & Lead Scrapes:</strong> Collected <strong>{metrics['new_leads']}</strong> new contact emails</li>
            <li>⚡ <strong>Technical Audits & PDFs:</strong> Generated <strong>{metrics['audits_completed']}</strong> audit reports</li>
            <li>📧 <strong>Pitch Emails Sent:</strong> Emailed <strong>{metrics['audits_completed']}</strong> leads with Paystack checkout links</li>
            <li>💰 <strong>Recent Revenue:</strong> ₦{metrics['revenue_6h']:,.2f}</li>
        </ul>

        <h3>🌐 Overall Database Pipeline Status:</h3>
        <table style="width: 100%; border-collapse: collapse; text-align: left; font-size: 14px;">
            <tr style="background-color: #f8f9fa;">
                <th style="padding: 8px; border: 1px solid #ddd;">Total Discovered</th>
                <th style="padding: 8px; border: 1px solid #ddd;">Total Audited & Emailed</th>
                <th style="padding: 8px; border: 1px solid #ddd;">Converted Clients</th>
            </tr>
            <tr>
                <td style="padding: 8px; border: 1px solid #ddd;">{metrics['total_leads']}</td>
                <td style="padding: 8px; border: 1px solid #ddd;">{metrics['total_audited']}</td>
                <td style="padding: 8px; border: 1px solid #ddd; font-weight: bold; color: #2e7d32;">{metrics['total_converted']}</td>
            </tr>
        </table>

        <p style="margin-top: 25px; font-weight: bold; color: #00C853;">
            ⏳ Expecting payouts automatically as leads click checkout links!
        </p>
    </div>
    """

    params = {
        "from": "Engine Monitor <onboarding@resend.dev>",
        "to": [ADMIN_EMAIL],
        "subject": f"⚡ Autonomous Engine Report: {metrics['new_leads']} New Leads & {metrics['audits_completed']} Audits Sent",
        "html": html_content
    }

    try:
        resend.Emails.send(params)
        print(f"✅ Admin summary email successfully sent to {ADMIN_EMAIL}")
    except Exception as e:
        print(f"❌ Failed to send admin summary email: {str(e)}")

if __name__ == "__main__":
    send_admin_digest()