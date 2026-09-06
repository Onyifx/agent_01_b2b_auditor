import time
from db import supabase
from main import process_full_audit

def process_discovered_queue(batch_size: int = 5):
    """Queries pending DISCOVERED leads from Supabase and audits them."""
    print("⏰ Fetching pending DISCOVERED leads from Supabase...")
    response = supabase.table("leads").select("id, domain, contact_email").eq("status", "DISCOVERED").limit(batch_size).execute()
    
    leads = response.data or []
    if not leads:
        print("  ℹ️ No pending DISCOVERED leads found.")
        return

    print(f"🚀 Found {len(leads)} leads ready for audit.")
    for lead in leads:
        print(f"\n--- Auditing: {lead['domain']} ({lead['contact_email']}) ---")
        process_full_audit(lead["id"], lead["domain"], lead["contact_email"])
        time.sleep(2)

if __name__ == "__main__":
    process_discovered_queue()