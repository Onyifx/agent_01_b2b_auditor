import os
from dotenv import load_dotenv
from supabase import create_client, Client
from supabase.lib.client_options import ClientOptions

# Load environment variables
load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    raise ValueError("Missing SUPABASE_URL or SUPABASE_KEY in environment or .env file")

# Configure client options with custom PostgREST timeout to handle idle connection drops
options = ClientOptions(
    postgrest_client_timeout=30
)

# Initialize Supabase client
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY, options=options)

def test_connection():
    """Verify Supabase database connectivity by querying the leads table."""
    try:
        response = supabase.table("leads").select("*").limit(1).execute()
        print("✓ Successfully connected to Supabase!")
        print("Leads query test result:", response.data)
    except Exception as e:
        print("❌ Supabase connection test failed:", str(e))

if __name__ == "__main__":
    test_connection()