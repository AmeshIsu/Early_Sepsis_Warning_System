from sqlalchemy import Column, Integer, Float, String, Boolean
from backend.app.database import Base

class SystemSetting(Base):
    __tablename__ = "system_settings"

    id = Column(Integer, primary_key=True, index=True)
    key = Column(String, unique=True, index=True)
    value_str = Column(String, nullable=True)
    value_float = Column(Float, nullable=True)
    value_int = Column(Integer, nullable=True)
    value_bool = Column(Boolean, nullable=True)
    description = Column(String, nullable=True)
