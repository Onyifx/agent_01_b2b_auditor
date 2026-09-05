import os
import stripe
from dotenv import load_dotenv

load_dotenv()

stripe.api_key = os.getenv("STRIPE_SECRET_KEY", "sk_test_placeholder")

def create_checkout_session(lead_id: str, domain: str) -> str:
    """
    Creates a $29 Stripe Checkout Session for a specific audit lead.
    """
    session = stripe.checkout.Session.create(
        payment_method_types=["card"],
        line_items=[{
            "price_data": {
                "currency": "usd",
                "product_data": {
                    "name": f"Full Technical & Security Fix — {domain}",
                    "description": "Complete implementation and resolution of all flagged audit issues.",
                },
                "unit_amount": 2900,  # $29.00 in cents
            },
            "quantity": 1,
        }],
        mode="payment",
        metadata={
            "lead_id": lead_id,
            "domain": domain
        },
        success_url="https://example.com/success?session_id={CHECKOUT_SESSION_ID}",
        cancel_url="https://example.com/cancel",
    )
    return session.url