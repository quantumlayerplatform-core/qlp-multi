"""
Common dependencies for FastAPI endpoints
"""
from fastapi import Request, HTTPException
from temporalio.client import Client

def get_temporal_client(request: Request) -> Client:
    """Get the shared Temporal client from app state"""
    client = getattr(request.app.state, 'temporal_client', None)
    if client is None:
        raise HTTPException(
            status_code=503,
            detail="Temporal service is not available. Please try again later."
        )
    return client