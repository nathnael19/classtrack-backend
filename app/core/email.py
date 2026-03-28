import resend
from .config import settings

resend.api_key = settings.RESEND_API_KEY

def send_setup_password_email(email: str, token: str):
    setup_url = f"{settings.FRONTEND_URL}/setup-password?token={token}"
    
    params = {
        "from": "ClassTrack <onboarding@resend.dev>",
        "to": [email],
        "subject": "Set Up Your ClassTrack Account",
        "html": f"""
        <div style="font-family: sans-serif; max-width: 600px; margin: 0 auto; padding: 20px; border: 1px solid #eee; rounded: 10px;">
            <h2 style="color: #4F46E5;">Welcome to ClassTrack!</h2>
            <p>An administrator has created an account for you. To get started, please set up your password by clicking the button below:</p>
            <div style="text-align: center; margin: 30px 0;">
                <a href="{setup_url}" style="background-color: #4F46E5; color: white; padding: 12px 24px; text-decoration: none; border-radius: 5px; font-weight: bold;">Set Up Password</a>
            </div>
            <p>This link will expire in 24 hours.</p>
            <p>If the button doesn't work, you can copy and paste this link into your browser:</p>
            <p style="word-break: break-all; color: #666;">{setup_url}</p>
            <hr style="border: 0; border-top: 1px solid #eee; margin: 20px 0;">
            <p style="font-size: 12px; color: #999;">If you didn't expect this email, you can safely ignore it.</p>
        </div>
        """,
    }

    try:
        response = resend.Emails.send(params)
        return response
    except Exception as e:
        print(f"Error sending email: {e}")
        return None


def send_password_reset_email(email: str, token: str):
    reset_url = f"{settings.FRONTEND_URL}/reset-password?token={token}"

    params = {
        "from": "ClassTrack <onboarding@resend.dev>",
        "to": [email],
        "subject": "Reset Your ClassTrack Password",
        "html": f"""
        <div style="font-family: sans-serif; max-width: 600px; margin: 0 auto; padding: 30px; background: #f8f9ff; border-radius: 16px;">
            <div style="background: white; padding: 32px; border-radius: 12px; box-shadow: 0 2px 8px rgba(0,0,0,0.08);">
                <h2 style="color: #4F46E5; margin: 0 0 12px;">Password Reset Request</h2>
                <p style="color: #555; margin: 0 0 24px;">We received a request to reset the password for your ClassTrack account. Click the button below to set a new password.</p>
                <div style="text-align: center; margin: 28px 0;">
                    <a href="{reset_url}" style="background-color: #4F46E5; color: white; padding: 14px 32px; text-decoration: none; border-radius: 8px; font-weight: bold; font-size: 15px;">Reset Password</a>
                </div>
                <p style="color: #888; font-size: 13px;">This link expires in <strong>1 hour</strong>. If you didn't request a password reset, you can safely ignore this email — your password won't change.</p>
                <hr style="border: 0; border-top: 1px solid #eee; margin: 24px 0;">
                <p style="font-size: 12px; color: #aaa;">Having trouble? Copy and paste this URL into your browser:</p>
                <p style="font-size: 12px; color: #6366f1; word-break: break-all;">{reset_url}</p>
            </div>
        </div>
        """,
    }

    try:
        response = resend.Emails.send(params)
        return response
    except Exception as e:
        print(f"Error sending password reset email: {e}")
        return None
