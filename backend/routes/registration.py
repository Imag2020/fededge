"""
Registration Routes
Handles node registration and verification endpoints
"""

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, EmailStr

router = APIRouter()


class RegistrationRequest(BaseModel):
    email: EmailStr
    name: str = ""
    client_public_ip: str = None  # Optional: public IP sent by frontend


@router.post("/register")
async def register_node(request: Request, data: RegistrationRequest):
    """
    Register a new node with email and optional name
    """
    try:
        # Get client IP from headers
        client_ip = None
        if hasattr(request, 'headers'):
            x_forwarded_for = request.headers.get('x-forwarded-for')
            x_real_ip = request.headers.get('x-real-ip')
            if x_forwarded_for:
                client_ip = x_forwarded_for.split(',')[0].strip()
            elif x_real_ip:
                client_ip = x_real_ip

        if not client_ip and hasattr(request.client, 'host'):
            client_ip = request.client.host

        # Use public IP sent by frontend if available, otherwise use detected IP
        final_client_ip = data.client_public_ip or client_ip

        print(f"🌐 /api/register - Detected IP: {client_ip}, Frontend public IP: {data.client_public_ip}, Using: {final_client_ip}")

        # Use the FedEdgeNodeClient to register
        from fededge_node_client import FedEdgeNodeClient
        node_client = FedEdgeNodeClient()

        result = node_client.register_user(
            email=data.email,
            name=data.name,
            client_ip=final_client_ip
        )

        return result

    except Exception as e:
        print(f"❌ Error in /api/register: {e}")
        import traceback
        traceback.print_exc()
        return {
            "success": False,
            "message": f"Registration error: {str(e)}"
        }


@router.post("/resend-verification")
async def resend_verification(request: Request):
    """
    Resend verification email for current node
    """
    try:
        # Get client IP
        client_ip = None
        if hasattr(request, 'headers'):
            x_forwarded_for = request.headers.get('x-forwarded-for')
            x_real_ip = request.headers.get('x-real-ip')
            if x_forwarded_for:
                client_ip = x_forwarded_for.split(',')[0].strip()
            elif x_real_ip:
                client_ip = x_real_ip

        if not client_ip and hasattr(request.client, 'host'):
            client_ip = request.client.host

        # Use the FedEdgeNodeClient to resend verification
        from fededge_node_client import FedEdgeNodeClient
        node_client = FedEdgeNodeClient()

        # Get node info to get the email
        info = node_client.get_node_info()

        if not info.get('user_email'):
            return {
                "success": False,
                "message": "No email registered for this node"
            }

        # Re-register to trigger verification email
        result = node_client.register_user(
            email=info['user_email'],
            name=info.get('user_name', ''),
            client_ip=client_ip
        )

        if result.get('success'):
            return {
                "success": True,
                "message": "Verification email resent successfully"
            }
        else:
            return result

    except Exception as e:
        print(f"❌ Error in /api/resend-verification: {e}")
        import traceback
        traceback.print_exc()
        return {
            "success": False,
            "message": f"Error resending verification: {str(e)}"
        }
