"""Payment gateway configuration placeholders for the standalone web edition.

Secrets are read only from server environment variables. This module never
accepts, stores, or returns secret values through browser APIs.
"""
from __future__ import annotations

import os
from fastapi import Depends
import api_server as api


PROVIDERS = {
    "razorpay": {
        "label": "Razorpay",
        "environment": {
            "test": ("RAZORPAY_TEST_KEY_ID", "RAZORPAY_TEST_KEY_SECRET", "RAZORPAY_TEST_WEBHOOK_SECRET"),
            "live": ("RAZORPAY_LIVE_KEY_ID", "RAZORPAY_LIVE_KEY_SECRET", "RAZORPAY_LIVE_WEBHOOK_SECRET"),
        },
    },
    "cashfree": {
        "label": "Cashfree",
        "environment": {
            "test": ("CASHFREE_TEST_CLIENT_ID", "CASHFREE_TEST_CLIENT_SECRET", "CASHFREE_TEST_WEBHOOK_SECRET"),
            "live": ("CASHFREE_LIVE_CLIENT_ID", "CASHFREE_LIVE_CLIENT_SECRET", "CASHFREE_LIVE_WEBHOOK_SECRET"),
        },
    },
    "stripe": {
        "label": "Stripe",
        "environment": {
            "test": ("STRIPE_TEST_PUBLISHABLE_KEY", "STRIPE_TEST_SECRET_KEY", "STRIPE_TEST_WEBHOOK_SECRET"),
            "live": ("STRIPE_LIVE_PUBLISHABLE_KEY", "STRIPE_LIVE_SECRET_KEY", "STRIPE_LIVE_WEBHOOK_SECRET"),
        },
    },
    "paypal": {
        "label": "PayPal",
        "environment": {
            "test": ("PAYPAL_TEST_CLIENT_ID", "PAYPAL_TEST_CLIENT_SECRET", "PAYPAL_TEST_WEBHOOK_ID"),
            "live": ("PAYPAL_LIVE_CLIENT_ID", "PAYPAL_LIVE_CLIENT_SECRET", "PAYPAL_LIVE_WEBHOOK_ID"),
        },
    },
}


def _role(user: dict) -> str:
    return str(user.get("role") or "").strip().lower()


def _admin_or_developer(user: dict) -> None:
    if _role(user) not in {"admin", "administrator", "developer", "developer / tester"}:
        from fastapi import HTTPException
        raise HTTPException(status_code=403, detail="Administrator or developer access required")


@api.app.get("/api/payments/config")
def payment_configuration(user: dict = Depends(api.get_current_user)):
    _admin_or_developer(user)
    result = {}
    for provider, definition in PROVIDERS.items():
        modes = {}
        for mode, keys in definition["environment"].items():
            present = [bool(os.environ.get(key, "").strip()) for key in keys]
            modes[mode] = {
                "configured": all(present),
                "missing_variables": [key for key, exists in zip(keys, present) if not exists],
                "variables": list(keys),
            }
        result[provider] = {"label": definition["label"], "modes": modes}
    return {
        "enabled": False,
        "currency": os.environ.get("PAYMENT_CURRENCY", "INR").upper(),
        "tax_rate_percent": os.environ.get("PAYMENT_TAX_RATE_PERCENT", ""),
        "shipping_flat_rate": os.environ.get("PAYMENT_SHIPPING_FLAT_RATE", ""),
        "providers": result,
        "notice": "Payment processing is disabled until a provider integration, credentials, webhook verification, and checkout tests are completed.",
    }


@api.app.get("/api/payments/placeholders")
def payment_placeholders(user: dict = Depends(api.get_current_user)):
    _admin_or_developer(user)
    return {
        "environment_variables": sorted({
            key
            for provider in PROVIDERS.values()
            for mode_keys in provider["environment"].values()
            for key in mode_keys
        } | {"PAYMENT_CURRENCY", "PAYMENT_TAX_RATE_PERCENT", "PAYMENT_SHIPPING_FLAT_RATE"}),
        "secret_values_exposed": False,
    }
