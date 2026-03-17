from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, Boolean
from sqlalchemy.orm import relationship
from datetime import datetime
from ..db.session import Base

class DeviceFingerprint(Base):
    __tablename__ = "device_fingerprints"

    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey("users.id"))
    device_id = Column(String, index=True) # Unique hardware/software hash
    device_model = Column(String, nullable=True)
    last_used_at = Column(DateTime, default=datetime.utcnow)
    is_trusted = Column(Boolean, default=True)

    student = relationship("User", backref="device_fingerprints")
