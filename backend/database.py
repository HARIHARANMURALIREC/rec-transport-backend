from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, Boolean, ForeignKey, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from datetime import datetime
import os

# Database URL
SQLALCHEMY_DATABASE_URL = "sqlite:///./rideshare.db"

# Create engine
engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)

# Create SessionLocal class
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create Base class
Base = declarative_base()

# Database Models
class User(Base):
    __tablename__ = "users"
    
    id = Column(String, primary_key=True, index=True)
    name = Column(String, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    phone = Column(String, nullable=False)
    role = Column(String, nullable=False)  # admin, driver, passenger
    password_hash = Column(String, nullable=False)
    avatar = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    is_active = Column(Boolean, default=True)
    
    # Relationships
    driver_profile = relationship("Driver", back_populates="user", uselist=False)
    passenger_profile = relationship("Passenger", back_populates="user", uselist=False)
    admin_profile = relationship("Admin", back_populates="user", uselist=False)

class Driver(Base):
    __tablename__ = "drivers"
    
    id = Column(String, primary_key=True, index=True)
    user_id = Column(String, ForeignKey("users.id"), unique=True)
    vehicle_make = Column(String, nullable=False)
    vehicle_model = Column(String, nullable=False)
    vehicle_year = Column(Integer, nullable=False)
    license_plate = Column(String, nullable=False)
    vehicle_color = Column(String, nullable=False)
    license_number = Column(String, nullable=False)
    license_expiry = Column(DateTime, nullable=False)
    rating = Column(Float, default=5.0)
    total_rides = Column(Integer, default=0)
    is_online = Column(Boolean, default=False)
    current_km_reading = Column(Integer, default=0)
    current_latitude = Column(Float, nullable=True)
    current_longitude = Column(Float, nullable=True)
    last_status_change = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    user = relationship("User", back_populates="driver_profile")
    rides = relationship("Ride", back_populates="driver")
    km_entries = relationship("KilometerEntry", back_populates="driver")
    fuel_entries = relationship("FuelEntry", back_populates="driver")
    leave_requests = relationship("LeaveRequest", back_populates="driver")

class Passenger(Base):
    __tablename__ = "passengers"
    
    id = Column(String, primary_key=True, index=True)
    user_id = Column(String, ForeignKey("users.id"), unique=True)
    rating = Column(Float, default=5.0)
    total_rides = Column(Integer, default=0)
    
    # Relationships
    user = relationship("User", back_populates="passenger_profile")
    rides = relationship("Ride", back_populates="passenger")

class Admin(Base):
    __tablename__ = "admins"
    
    id = Column(String, primary_key=True, index=True)
    user_id = Column(String, ForeignKey("users.id"), unique=True)
    permissions = Column(Text, nullable=False)  # JSON string of permissions
    
    # Relationships
    user = relationship("User", back_populates="admin_profile")

class Ride(Base):
    __tablename__ = "rides"
    
    id = Column(String, primary_key=True, index=True)
    passenger_id = Column(String, ForeignKey("passengers.id"), nullable=False)
    driver_id = Column(String, ForeignKey("drivers.id"), nullable=True)
    status = Column(String, nullable=False)  # requested, assigned, accepted, picking_up, in_progress, completed, cancelled
    pickup_latitude = Column(Float, nullable=False)
    pickup_longitude = Column(Float, nullable=False)
    pickup_address = Column(String, nullable=False)
    dropoff_latitude = Column(Float, nullable=False)
    dropoff_longitude = Column(Float, nullable=False)
    dropoff_address = Column(String, nullable=False)
    requested_at = Column(DateTime, default=datetime.utcnow)
    assigned_at = Column(DateTime, nullable=True)
    accepted_at = Column(DateTime, nullable=True)
    picked_up_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    cancelled_at = Column(DateTime, nullable=True)
    distance = Column(Float, default=0.0)
    estimated_duration = Column(Integer, default=0)
    actual_duration = Column(Integer, nullable=True)
    
    # Relationships
    passenger = relationship("Passenger", back_populates="rides")
    driver = relationship("Driver", back_populates="rides")

class KilometerEntry(Base):
    __tablename__ = "kilometer_entries"
    
    id = Column(String, primary_key=True, index=True)
    driver_id = Column(String, ForeignKey("drivers.id"), nullable=False)
    start_km = Column(Integer, nullable=False)
    end_km = Column(Integer, nullable=True)
    date = Column(DateTime, default=datetime.utcnow)
    ride_id = Column(String, ForeignKey("rides.id"), nullable=True)
    status = Column(String, nullable=False)  # started, completed
    
    # Relationships
    driver = relationship("Driver", back_populates="km_entries")

class FuelEntry(Base):
    __tablename__ = "fuel_entries"
    
    id = Column(String, primary_key=True, index=True)
    driver_id = Column(String, ForeignKey("drivers.id"), nullable=False)
    amount = Column(Float, nullable=False)  # liters
    cost = Column(Float, nullable=False)
    date = Column(DateTime, default=datetime.utcnow)
    location = Column(String, nullable=False)
    added_by = Column(String, nullable=False)  # driver, admin
    admin_id = Column(String, nullable=True)
    
    # Relationships
    driver = relationship("Driver", back_populates="fuel_entries")

class LeaveRequest(Base):
    __tablename__ = "leave_requests"
    
    id = Column(String, primary_key=True, index=True)
    driver_id = Column(String, ForeignKey("drivers.id"), nullable=False)
    start_date = Column(DateTime, nullable=False)
    end_date = Column(DateTime, nullable=False)
    reason = Column(Text, nullable=False)
    status = Column(String, default="pending")  # pending, approved, rejected
    requested_at = Column(DateTime, default=datetime.utcnow)
    reviewed_at = Column(DateTime, nullable=True)
    reviewed_by = Column(String, nullable=True)
    comments = Column(Text, nullable=True)
    
    # Relationships
    driver = relationship("Driver", back_populates="leave_requests")

class DriverAttendance(Base):
    __tablename__ = "driver_attendance"
    
    id = Column(String, primary_key=True, index=True)
    driver_id = Column(String, ForeignKey("drivers.id"), nullable=False)
    date = Column(DateTime, nullable=False)  # Date of attendance
    start_time = Column(DateTime, nullable=False)  # When driver went online
    end_time = Column(DateTime, nullable=True)  # When driver went offline
    total_hours = Column(Float, nullable=True)  # Calculated total hours
    status = Column(String, default="active")  # active, completed
    
    # Relationships
    driver = relationship("Driver")

# Dependency to get DB session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Create all tables
def create_tables():
    Base.metadata.create_all(bind=engine)