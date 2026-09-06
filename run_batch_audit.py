import time
from db import supabase, execute_supabase_query
from main import process_full_audit

def process_discovered_queue(batch_size: int = 5):
    """Queries pending DISCOVERED leads from Supabase and audits them safely."""
    print("⏰ Fetching pending DISCOVERED leads from Supabase...")
    try:
        response = execute_supabase_query(
            lambda: supabase.table("leads").select("id, domain, contact_email").eq("status", "DISCOVERED").limit(batch_size).execute()
        )
    except Exception as e:
        print(f"❌ Failed to fetch pending leads from Supabase: {str(e)}")
        return

    leads = response.data or [] if response else []
    if not leads:
        print("  ℹ️ No pending DISCOVERED leads found.")
        return

    print(f"🚀 Found {len(leads)} leads ready for audit.")
    for lead in leads:
        print(f"\n--- Auditing: {lead['domain']} ({lead['contact_email']}) ---")
        try:
            process_full_audit(lead["id"], lead["domain"], lead["contact_email"])
        except Exception as audit_err:
            print(f"❌ Unhandled exception while auditing {lead['domain']}: {str(audit_err)}")
            print("  ⏭️ Skipping lead and continuing batch pipeline...")
        time.sleep(2)

if __name__ == "__main__":
    process_discovered_queue()