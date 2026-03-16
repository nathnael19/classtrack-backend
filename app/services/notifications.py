from typing import List, Optional
from sqlalchemy.orm import Session
from ..models.user import User
import requests # Placeholder for real FCM HTTP v1 API

class NotificationService:
    @staticmethod
    def send_push_notification(user_id: int, title: str, body: str, db: Session):
        """
        Sends a push notification to a specific user via FCM.
        """
        user = db.query(User).filter(User.id == user_id).first()
        if not user or not user.fcm_token:
            print(f"DEBUG: Skipping notification for user {user_id} - No FCM token found.")
            return False
            
        # Stub logic for FCM request
        payload = {
            "message": {
                "token": user.fcm_token,
                "notification": {
                    "title": title,
                    "body": body
                }
            }
        }
        print(f"DEBUG: Sending FCM notification to {user.email}: {title} - {body}")
        # In production: requests.post("https://fcm.googleapis.com/v1/projects/myproject/messages:send", json=payload, headers=headers)
        return True

    @staticmethod
    def notify_course_students(course_id: int, title: str, body: str, db: Session):
        """
        Sends a notification to all students enrolled in a course.
        """
        # Implementation would fetch course students and call send_push_notification
        pass

notification_service = NotificationService()
