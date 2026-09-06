import os
import time
import httpx
from dotenv import load_dotenv
from supabase import create_client, Client, ClientOptions

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

def execute_supabase_query(query_func, max_retries: int = 3, delay: int = 2):
    """Universal resilient query handler for Supabase operations with automatic retries."""
    for attempt in range(max_retries):
        try:
            return query_func()
        except (httpx.RemoteProtocolError, httpx.ConnectError, httpx.ReadTimeout, httpx.HTTPError) as e:
            if attempt < max_retries - 1:
                print(f"⚠️ Supabase network glitch ({type(e).__name__}). Retrying in {delay}s... ({attempt + 1}/{max_retries})")
                time.sleep(delay)
            else:
                print(f"❌ Failed Supabase query after {max_retries} attempts.")
                raise e
        except Exception as e:
            err_msg = str(e).lower()
            if ("disconnected" in err_msg or "remoteprotocolerror" in err_msg or "timeout" in err_msg) and attempt < max_retries - 1:
                print(f"⚠️ Supabase connection exception ({str(e)}). Retrying in {delay}s... ({attempt + 1}/{max_retries})")
                time.sleep(delay)
            else:
                raise e

def test_connection():
    """Verify Supabase database connectivity by querying the leads table."""
    try:
        response = execute_supabase_query(
            lambda: supabase.table("leads").select("*").limit(1).execute()
        )
        print("✓ Successfully connected to Supabase!")
        print("Leads query test result:", response.data)
    except Exception as e:
        print("❌ Supabase connection test failed:", str(e))

if __name__ == "__main__":
    test_connection()