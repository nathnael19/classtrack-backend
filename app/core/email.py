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
