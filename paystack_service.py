import os
import requests
from dotenv import load_dotenv

load_dotenv()

PAYSTACK_SECRET_KEY = os.getenv("PAYSTACK_SECRET_KEY", "sk_test_placeholder")

def create_paystack_checkout(lead_id: str, domain: str, email: str) -> str:
    """
    Initializes a Paystack transaction for an audit lead.
    Supports international cards via NGN conversion.
    """
    if not PAYSTACK_SECRET_KEY or "placeholder" in PAYSTACK_SECRET_KEY or not PAYSTACK_SECRET_KEY.startswith("sk_"):
        print("⚠️ No valid Paystack key found in .env — returning mock checkout URL.")
        return f"https://checkout.paystack.com/mock_session_{lead_id}"

    url = "https://api.paystack.co/transaction/initialize"
    headers = {
        "Authorization": f"Bearer {PAYSTACK_SECRET_KEY}",
        "Content-Type": "application/json"
    }
    
    # ₦45,000 (~$29 USD) in kobo
    payload = {
        "email": email,
        "amount": 4500000,
        "currency": "NGN",
        "metadata": {
            "lead_id": lead_id,
            "domain": domain
        },
        "callback_url": "https://example.com/success"
    }

    try:
        response = requests.post(url, json=payload, headers=headers)
        res_data = response.json()

        if response.status_code == 200 and res_data.get("status"):
            return res_data["data"]["authorization_url"]
        else:
            error_msg = res_data.get("message", "Paystack initialization failed")
            raise Exception(f"Paystack Error: {error_msg}")
    except Exception as e:
        print(f"❌ Paystack Initialization Exception: {str(e)}")
        raise e