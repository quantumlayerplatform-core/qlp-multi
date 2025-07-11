#!/usr/bin/env python3
"""
Simple authentication module for QLP endpoints
"""

from typing import Dict, Any


def get_current_user() -> Dict[str, Any]:
    """
    Simple authentication function that returns a default user
    In production, this would validate JWT tokens, API keys, etc.
    """
    return {
        "user_id": "default-user",
        "tenant_id": "default-tenant",
        "role": "admin",
        "authenticated": True
    }