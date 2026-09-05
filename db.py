import os
from dotenv import load_dotenv
from supabase import create_client, Client

# Load environment variables
load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    raise ValueError("Missing SUPABASE_URL or SUPABASE_KEY in .env file")

# Initialize Supabase client
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

def test_connection():
    """Verify Supabase database connectivity by querying the leads table."""
    response = supabase.table("leads").select("*").limit(1).execute()
    print("✓ Successfully connected to Supabase!")
    print("Leads query test result:", response.data)

if __name__ == "__main__":
    test_connection()