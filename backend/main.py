from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from typing import Optional, List
import uuid
import json

from database import get_db, create_tables, User as DBUser, Driver as DBDriver, Passenger as DBPassenger, Admin as DBAdmin, Ride as DBRide, KilometerEntry as DBKilometerEntry, FuelEntry as DBFuelEntry, LeaveRequest as DBLeaveRequest
from database import DriverAttendance as DBDriverAttendance
from schemas import (
    User, UserCreateAdmin, Driver, DriverCreateAdmin, Passenger, PassengerCreateAdmin, Admin, Ride, KilometerEntry, FuelEntry, LeaveRequest,
    UserLogin, Token, KilometerEntryCreate, KilometerEntryComplete, FuelEntryCreate,
    LeaveRequestCreate, LeaveRequestReview, RideCreate, RideStatus, DashboardStats,
    DriverAttendance, DriverAttendanceCreate, DriverAttendanceUpdate,
    RideAssignment, RideStart, RideComplete, LocationBase
)
from auth import get_password_hash, verify_password, create_access_token, get_current_user, get_current_admin, get_current_driver

# Create FastAPI app
app = FastAPI(title="RideShare API", version="1.0.0")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure this properly for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Create tables on startup
@app.on_event("startup")
def startup_event():
    create_tables()
    print("Database tables created successfully")
    # Create default admin user if not exists
    db = next(get_db())
    admin_user = db.query(DBUser).filter(DBUser.email == "admin@rideshare.com").first()
    if not admin_user:
        print("Creating default users...")
        # Create admin user
        admin_user = DBUser(
            id=str(uuid.uuid4()),
            name="Admin User",
            email="admin@rideshare.com",
            phone="+1234567890",
            role="admin",
            password_hash=get_password_hash("password")
        )
        db.add(admin_user)
        
        # Create admin profile
        admin_profile = DBAdmin(
            id=str(uuid.uuid4()),
            user_id=admin_user.id,
            permissions=json.dumps(["view_all", "manage_drivers", "manage_rides"])
        )
        db.add(admin_profile)
        
        # Create sample driver
        driver_user = DBUser(
            id=str(uuid.uuid4()),
            name="John Driver",
            email="driver@rideshare.com",
            phone="+1234567891",
            role="driver",
            password_hash=get_password_hash("password")
        )
        db.add(driver_user)
        
        driver_profile = DBDriver(
            id=str(uuid.uuid4()),
            user_id=driver_user.id,
            vehicle_make="Toyota",
            vehicle_model="Camry",
            vehicle_year=2020,
            license_plate="ABC-123",
            vehicle_color="Silver",
            license_number="DL123456789",
            license_expiry=datetime(2025, 12, 31),
            rating=4.8,
            total_rides=1250,
            current_km_reading=45230
        )
        db.add(driver_profile)
        
        # Create sample passenger
        passenger_user = DBUser(
            id=str(uuid.uuid4()),
            name="Jane Passenger",
            email="passenger@rideshare.com",
            phone="+1234567892",
            role="passenger",
            password_hash=get_password_hash("password")
        )
        db.add(passenger_user)
        
        passenger_profile = DBPassenger(
            id=str(uuid.uuid4()),
            user_id=passenger_user.id,
            rating=4.9,
            total_rides=89
        )
        db.add(passenger_profile)
        
        db.commit()
        print("Default users created successfully")
    else:
        print("Default users already exist")

# Test endpoint
@app.get("/test")
def test_endpoint():
    return {"message": "Backend is working!", "status": "success"}

# Authentication endpoints
@app.post("/auth/login", response_model=Token)
def login(user_credentials: UserLogin, db: Session = Depends(get_db)):
    print(f"🔐 Login attempt for email: {user_credentials.email}")
    
    user = db.query(DBUser).filter(DBUser.email == user_credentials.email).first()
    
    if not user:
        print(f"❌ User not found for email: {user_credentials.email}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password"
        )
    
    print(f"✅ User found: {user.name} (role: {user.role})")
    
    if not verify_password(user_credentials.password, user.password_hash):
        print(f"❌ Password verification failed for user: {user.email}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password"
        )
    
    print(f"✅ Password verified successfully for user: {user.email}")
    
    access_token_expires = timedelta(minutes=30)
    access_token = create_access_token(
        data={"sub": user.email}, expires_delta=access_token_expires
    )
    
    print(f"🎉 Login successful for user: {user.name}")
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": user
    }

@app.get("/auth/me", response_model=User)
def get_current_user_info(current_user: User = Depends(get_current_user)):
    return current_user

# User management endpoints (admin only)
@app.post("/users", response_model=User)
def create_user(user_data: UserCreateAdmin, db: Session = Depends(get_db), current_user: User = Depends(get_current_admin)):
    """Create a new user (admin only)"""
    # Check if user with this email already exists
    existing_user = db.query(DBUser).filter(DBUser.email == user_data.email).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="User with this email already exists")
    
    # Create new user
    new_user = DBUser(
        id=str(uuid.uuid4()),
        name=user_data.name,
        email=user_data.email,
        phone=user_data.phone,
        role=user_data.role,
        password_hash=get_password_hash("password"),  # Default password
        created_at=datetime.utcnow(),
        is_active=True
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    return new_user

@app.post("/drivers", response_model=Driver)
def create_driver(driver_data: DriverCreateAdmin, db: Session = Depends(get_db), current_user: User = Depends(get_current_admin)):
    """Create a new driver (admin only)"""
    # Check if user with this email already exists
    existing_user = db.query(DBUser).filter(DBUser.email == driver_data.user.email).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="User with this email already exists")
    
    # Create user first
    new_user = DBUser(
        id=str(uuid.uuid4()),
        name=driver_data.user.name,
        email=driver_data.user.email,
        phone=driver_data.user.phone,
        role="driver",
        password_hash=get_password_hash("password"),  # Default password
        created_at=datetime.utcnow(),
        is_active=True
    )
    db.add(new_user)
    db.flush()  # Get the user ID without committing
    
    # Create driver profile
    new_driver = DBDriver(
        id=str(uuid.uuid4()),
        user_id=new_user.id,
        vehicle_make=driver_data.vehicle_make,
        vehicle_model=driver_data.vehicle_model,
        vehicle_year=driver_data.vehicle_year,
        license_plate=driver_data.license_plate,
        vehicle_color=driver_data.vehicle_color,
        license_number=driver_data.license_number,
        license_expiry=datetime.fromisoformat(driver_data.license_expiry),
        rating=5.0,
        total_rides=0,
        is_online=False,
        current_km_reading=0,
        last_status_change=datetime.utcnow()
    )
    db.add(new_driver)
    db.commit()
    db.refresh(new_driver)
    
    return new_driver

@app.post("/passengers", response_model=Passenger)
def create_passenger(passenger_data: dict, db: Session = Depends(get_db), current_user: User = Depends(get_current_admin)):
    print("Received passenger_data:", passenger_data)
    # Try to extract name, email, phone from any structure
    name = passenger_data.get("name")
    email = passenger_data.get("email")
    phone = passenger_data.get("phone")
    # If not found, try nested under 'user'
    if not name and isinstance(passenger_data.get("user"), dict):
        name = passenger_data["user"].get("name")
        email = passenger_data["user"].get("email")
        phone = passenger_data["user"].get("phone")
    if not name or not email or not phone:
        raise HTTPException(status_code=400, detail=f"Missing required field: name, email, or phone. Received: {passenger_data}")
    # Check if user with this email already exists
    existing_user = db.query(DBUser).filter(DBUser.email == email).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="User with this email already exists")
    # Create user
    new_user = DBUser(
        id=str(uuid.uuid4()),
        name=name,
        email=email,
        phone=phone,
        role="passenger",
        password_hash=get_password_hash("password"),
        created_at=datetime.utcnow(),
        is_active=True
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    # Create passenger profile
    new_passenger = DBPassenger(
        id=str(uuid.uuid4()),
        user_id=new_user.id,
        rating=5.0,
        total_rides=0
    )
    db.add(new_passenger)
    db.commit()
    db.refresh(new_passenger)
    return new_passenger

# Passenger endpoints
@app.get("/passengers", response_model=List[Passenger])
def get_all_passengers(db: Session = Depends(get_db), current_user: User = Depends(get_current_admin)):
    """Get all passengers (admin only)"""
    passengers = db.query(DBPassenger).all()
    return passengers

@app.get("/passengers/{passenger_id}", response_model=Passenger)
def get_passenger(passenger_id: str, db: Session = Depends(get_db)):
    """Get a specific passenger"""
    passenger = db.query(DBPassenger).filter(DBPassenger.id == passenger_id).first()
    if not passenger:
        raise HTTPException(status_code=404, detail="Passenger not found")
    return passenger

@app.get("/passengers/by_user_id/{user_id}", response_model=Passenger)
def get_passenger_by_user_id(user_id: str, db: Session = Depends(get_db)):
    passenger = db.query(DBPassenger).filter(DBPassenger.user_id == user_id).first()
    if not passenger:
        raise HTTPException(status_code=404, detail="Passenger not found")
    return passenger

def db_ride_to_schema(ride):
    return Ride(
        id=ride.id,
        passenger_id=ride.passenger_id,
        driver_id=ride.driver_id,
        status=ride.status,
        pickup_latitude=ride.pickup_latitude,
        pickup_longitude=ride.pickup_longitude,
        pickup_address=ride.pickup_address,
        dropoff_latitude=ride.dropoff_latitude,
        dropoff_longitude=ride.dropoff_longitude,
        dropoff_address=ride.dropoff_address,
        requested_at=ride.requested_at,
        assigned_at=ride.assigned_at,
        accepted_at=ride.accepted_at,
        picked_up_at=ride.picked_up_at,
        completed_at=ride.completed_at,
        cancelled_at=ride.cancelled_at,
        distance=ride.distance,
        estimated_duration=ride.estimated_duration,
        actual_duration=ride.actual_duration,
        pickup_location=LocationBase(
            latitude=ride.pickup_latitude,
            longitude=ride.pickup_longitude,
            address=ride.pickup_address,
        ),
        dropoff_location=LocationBase(
            latitude=ride.dropoff_latitude,
            longitude=ride.dropoff_longitude,
            address=ride.dropoff_address,
        ),
    )

@app.post("/rides/manual", response_model=Ride)
def create_manual_ride(
    ride_data: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin)
):
    """Create a ride manually by admin (admin only)"""
    try:
        # Validate required fields
        required_fields = ['passenger_id', 'driver_id', 'pickup_address', 'dropoff_address']
        for field in required_fields:
            if field not in ride_data:
                raise HTTPException(status_code=400, detail=f"Missing required field: {field}")
        
        # Check if passenger exists
        passenger = db.query(DBPassenger).filter(DBPassenger.id == ride_data['passenger_id']).first()
        if not passenger:
            raise HTTPException(status_code=404, detail="Passenger not found")
        
        # Check if driver exists and is online
        driver = db.query(DBDriver).filter(DBDriver.id == ride_data['driver_id']).first()
        if not driver:
            raise HTTPException(status_code=404, detail="Driver not found")
        
        if not driver.is_online:
            raise HTTPException(status_code=400, detail="Driver is not online")
        
        # Create new ride with required NOT NULL fields set to default values
        new_ride = DBRide(
            id=str(uuid.uuid4()),
            passenger_id=ride_data['passenger_id'],
            driver_id=ride_data['driver_id'],
            pickup_address=ride_data['pickup_address'],
            dropoff_address=ride_data['dropoff_address'],
            pickup_latitude=0.0,
            pickup_longitude=0.0,
            dropoff_latitude=0.0,
            dropoff_longitude=0.0,
            distance=0.0,
            estimated_duration=0,
            status="assigned",  # Directly assign since admin is creating it
            requested_at=datetime.utcnow(),
            assigned_at=datetime.utcnow()
        )
        
        db.add(new_ride)
        db.commit()
        db.refresh(new_ride)
        print(f"Created ride: id={new_ride.id}, passenger_id={new_ride.passenger_id}, driver_id={new_ride.driver_id}")
        return db_ride_to_schema(new_ride)
        
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error creating ride: {str(e)}")

# Driver endpoints
@app.get("/drivers", response_model=List[Driver])
def get_all_drivers(db: Session = Depends(get_db), current_user: User = Depends(get_current_admin)):
    drivers = db.query(DBDriver).all()
    return drivers

@app.get("/drivers/{driver_id}", response_model=Driver)
def get_driver(driver_id: str, db: Session = Depends(get_db)):
    driver = db.query(DBDriver).filter(DBDriver.id == driver_id).first()
    if not driver:
        raise HTTPException(status_code=404, detail="Driver not found")
    return driver

@app.put("/drivers/{driver_id}/status")
def update_driver_status(driver_id: str, is_online: bool, db: Session = Depends(get_db)):
    driver = db.query(DBDriver).filter(DBDriver.id == driver_id).first()
    if not driver:
        raise HTTPException(status_code=404, detail="Driver not found")
    
    driver.is_online = is_online
    driver.last_status_change = datetime.utcnow()
    db.commit()
    
    return {"message": "Status updated successfully"}

@app.put("/drivers/me/status")
def update_my_status(is_online: bool, db: Session = Depends(get_db), current_user: User = Depends(get_current_driver)):
    print(f"🔧 Received status update request - is_online: {is_online} (type: {type(is_online)})")
    print(f"🔧 Current user: {current_user.name} (ID: {current_user.id})")
    driver = db.query(DBDriver).filter(DBDriver.user_id == current_user.id).first()
    if not driver:
        print(f"❌ Driver profile not found for user: {current_user.id}")
        raise HTTPException(status_code=404, detail="Driver profile not found")
    
    print(f"✅ Driver found: {driver.id}")
    print(f"🔄 Updating online status from {driver.is_online} to {is_online}")
    driver.is_online = is_online
    driver.last_status_change = datetime.utcnow()
    db.commit()
    print(f"✅ Status updated successfully")
    
    return {"message": "Status updated successfully"}

@app.put("/drivers/me/status-body")
def update_my_status_body(request: dict, db: Session = Depends(get_db), current_user: User = Depends(get_current_driver)):
    print(f"🔧 Received status update request (body) - request: {request}")
    print(f"🔧 Current user: {current_user.name} (ID: {current_user.id})")
    
    is_online = request.get("is_online")
    if is_online is None:
        raise HTTPException(status_code=400, detail="is_online parameter is required")
    
    driver = db.query(DBDriver).filter(DBDriver.user_id == current_user.id).first()
    if not driver:
        print(f"❌ Driver profile not found for user: {current_user.id}")
        raise HTTPException(status_code=404, detail="Driver profile not found")
    
    print(f"✅ Driver found: {driver.id}")
    print(f"🔄 Updating online status from {driver.is_online} to {is_online}")
    
    # Track attendance
    now = datetime.utcnow()
    if is_online and not driver.is_online:
        # Driver is going online - create attendance record
        attendance = DBDriverAttendance(
            id=str(uuid.uuid4()),
            driver_id=driver.id,
            date=now.date(),
            start_time=now,
            status="active"
        )
        db.add(attendance)
        print(f"📝 Created attendance record for driver going online")
    elif not is_online and driver.is_online:
        # Driver is going offline - complete attendance record
        active_attendance = db.query(DBDriverAttendance).filter(
            DBDriverAttendance.driver_id == driver.id,
            DBDriverAttendance.status == "active"
        ).first()
        
        if active_attendance:
            active_attendance.end_time = now
            active_attendance.status = "completed"
            # Calculate total hours
            duration = now - active_attendance.start_time
            active_attendance.total_hours = duration.total_seconds() / 3600
            print(f"📝 Completed attendance record - Total hours: {active_attendance.total_hours:.2f}")
    
    driver.is_online = is_online
    driver.last_status_change = datetime.utcnow()
    db.commit()
    print(f"✅ Status updated successfully")
    
    return {"message": "Status updated successfully"}

# Kilometer tracking endpoints
@app.post("/km-entries", response_model=KilometerEntry)
def create_km_entry(km_entry: KilometerEntryCreate, db: Session = Depends(get_db)):
    new_entry = DBKilometerEntry(
        id=str(uuid.uuid4()),
        driver_id=km_entry.driver_id,
        start_km=km_entry.start_km,
        ride_id=km_entry.ride_id,
        status="started"
    )
    db.add(new_entry)
    
    # Update driver's current km reading
    driver = db.query(DBDriver).filter(DBDriver.id == km_entry.driver_id).first()
    if driver:
        driver.current_km_reading = km_entry.start_km
    
    db.commit()
    db.refresh(new_entry)
    return new_entry

@app.put("/km-entries/{entry_id}/complete")
def complete_km_entry(entry_id: str, completion: KilometerEntryComplete, db: Session = Depends(get_db)):
    entry = db.query(DBKilometerEntry).filter(DBKilometerEntry.id == entry_id).first()
    if not entry:
        raise HTTPException(status_code=404, detail="Kilometer entry not found")
    
    entry.end_km = completion.end_km
    entry.status = "completed"
    
    # Update driver's current km reading
    driver = db.query(DBDriver).filter(DBDriver.id == entry.driver_id).first()
    if driver:
        driver.current_km_reading = completion.end_km
    
    db.commit()
    return {"message": "Kilometer entry completed"}

@app.get("/km-entries", response_model=List[KilometerEntry])
def get_km_entries(driver_id: Optional[str] = None, db: Session = Depends(get_db)):
    query = db.query(DBKilometerEntry)
    if driver_id:
        query = query.filter(DBKilometerEntry.driver_id == driver_id)
    return query.all()

# Fuel tracking endpoints
@app.post("/fuel-entries", response_model=FuelEntry)
def create_fuel_entry(fuel_entry: FuelEntryCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    new_entry = DBFuelEntry(
        id=str(uuid.uuid4()),
        driver_id=fuel_entry.driver_id,
        amount=fuel_entry.amount,
        cost=fuel_entry.cost,
        location=fuel_entry.location,
        added_by=current_user.role,
        admin_id=current_user.id if current_user.role == "admin" else None
    )
    db.add(new_entry)
    db.commit()
    db.refresh(new_entry)
    return new_entry

@app.get("/fuel-entries", response_model=List[FuelEntry])
def get_fuel_entries(driver_id: Optional[str] = None, db: Session = Depends(get_db)):
    query = db.query(DBFuelEntry)
    if driver_id:
        query = query.filter(DBFuelEntry.driver_id == driver_id)
    return query.all()

# Leave request endpoints
@app.post("/leave-requests", response_model=LeaveRequest)
def create_leave_request(leave_request: LeaveRequestCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    # For drivers, use their own ID; for admins, use the provided driver_id
    if current_user.role == "admin":
        if not leave_request.driver_id:
            raise HTTPException(status_code=400, detail="driver_id is required for admin requests")
        driver_id = leave_request.driver_id
    else:
        driver_id = current_user.id
    
    # Verify the driver exists
    driver = db.query(DBDriver).filter(DBDriver.user_id == driver_id).first()
    if not driver:
        raise HTTPException(status_code=404, detail="Driver not found")
    
    new_request = DBLeaveRequest(
        id=str(uuid.uuid4()),
        driver_id=driver.id,  # Use the driver's profile ID, not user ID
        start_date=leave_request.start_date,
        end_date=leave_request.end_date,
        reason=leave_request.reason,
        status="pending"
    )
    db.add(new_request)
    db.commit()
    db.refresh(new_request)
    return new_request

@app.put("/leave-requests/{request_id}/review")
def review_leave_request(
    request_id: str, 
    review: LeaveRequestReview, 
    db: Session = Depends(get_db), 
    current_user: User = Depends(get_current_admin)
):
    leave_request = db.query(DBLeaveRequest).filter(DBLeaveRequest.id == request_id).first()
    if not leave_request:
        raise HTTPException(status_code=404, detail="Leave request not found")
    
    leave_request.status = review.status
    leave_request.reviewed_at = datetime.utcnow()
    leave_request.reviewed_by = current_user.id
    leave_request.comments = review.comments
    
    db.commit()
    return {"message": "Leave request reviewed successfully"}

@app.get("/leave-requests", response_model=List[LeaveRequest])
def get_leave_requests(driver_id: Optional[str] = None, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    query = db.query(DBLeaveRequest)
    
    # If specific driver_id is provided (admin functionality)
    if driver_id:
        if current_user.role != "admin":
            raise HTTPException(status_code=403, detail="Only admins can view other drivers' leave requests")
        query = query.filter(DBLeaveRequest.driver_id == driver_id)
    else:
        # For drivers, show only their own requests
        if current_user.role == "driver":
            driver = db.query(DBDriver).filter(DBDriver.user_id == current_user.id).first()
            if driver:
                query = query.filter(DBLeaveRequest.driver_id == driver.id)
        # For admins, show all requests if no specific driver_id
        # (no additional filter needed)
    
    return query.all()

@app.get("/leave-requests/{request_id}", response_model=LeaveRequest)
def get_leave_request(request_id: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Get a specific leave request by ID"""
    leave_request = db.query(DBLeaveRequest).filter(DBLeaveRequest.id == request_id).first()
    if not leave_request:
        raise HTTPException(status_code=404, detail="Leave request not found")
    
    # Check permissions
    if current_user.role == "driver":
        driver = db.query(DBDriver).filter(DBDriver.user_id == current_user.id).first()
        if not driver or leave_request.driver_id != driver.id:
            raise HTTPException(status_code=403, detail="Access denied")
    # Admin can access any leave request
    
    return leave_request

# Attendance endpoints
@app.get("/attendance", response_model=List[DriverAttendance])
def get_attendance(
    driver_id: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin)
):
    """Get attendance records (admin only)"""
    query = db.query(DBDriverAttendance).join(DBDriver).join(DBUser)
    
    if driver_id:
        query = query.filter(DBDriverAttendance.driver_id == driver_id)
    
    if start_date:
        try:
            start_dt = datetime.strptime(start_date, "%Y-%m-%d")
            query = query.filter(DBDriverAttendance.date >= start_dt)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid start_date format. Use YYYY-MM-DD")
    
    if end_date:
        try:
            end_dt = datetime.strptime(end_date, "%Y-%m-%d")
            query = query.filter(DBDriverAttendance.date <= end_dt)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid end_date format. Use YYYY-MM-DD")
    
    return query.order_by(DBDriverAttendance.date.desc(), DBDriverAttendance.start_time.desc()).all()

@app.get("/attendance/export")
def export_attendance_excel(
    driver_id: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin)
):
    """Export attendance data to Excel (admin only)"""
    try:
        import pandas as pd
        from io import BytesIO
        from fastapi.responses import StreamingResponse
    except ImportError:
        raise HTTPException(status_code=500, detail="pandas is required for Excel export. Install with: pip install pandas openpyxl")
    
    # Get attendance data
    query = db.query(DBDriverAttendance).join(DBDriver).join(DBUser)
    
    if driver_id:
        query = query.filter(DBDriverAttendance.driver_id == driver_id)
    
    if start_date:
        try:
            start_dt = datetime.strptime(start_date, "%Y-%m-%d")
            query = query.filter(DBDriverAttendance.date >= start_dt)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid start_date format. Use YYYY-MM-DD")
    
    if end_date:
        try:
            end_dt = datetime.strptime(end_date, "%Y-%m-%d")
            query = query.filter(DBDriverAttendance.date <= end_dt)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid end_date format. Use YYYY-MM-DD")
    
    attendance_records = query.order_by(DBDriverAttendance.date.desc(), DBDriverAttendance.start_time.desc()).all()
    
    # Prepare data for Excel
    data = []
    for record in attendance_records:
        data.append({
            'Driver Name': record.driver.user.name if record.driver and record.driver.user else 'Unknown',
            'Driver Email': record.driver.user.email if record.driver and record.driver.user else 'Unknown',
            'Date': record.date.strftime('%Y-%m-%d'),
            'Start Time': record.start_time.strftime('%Y-%m-%d %H:%M:%S'),
            'End Time': record.end_time.strftime('%Y-%m-%d %H:%M:%S') if record.end_time else 'Active',
            'Total Hours': f"{record.total_hours:.2f}" if record.total_hours else 'N/A',
            'Status': record.status
        })
    
    # Create DataFrame and Excel file
    df = pd.DataFrame(data)
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, sheet_name='Driver Attendance', index=False)
    
    output.seek(0)
    
    # Return Excel file
    return StreamingResponse(
        BytesIO(output.read()),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename=driver_attendance_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"}
    )

# Ride endpoints
@app.post("/rides", response_model=Ride)
def create_ride(ride: RideCreate, db: Session = Depends(get_db)):
    new_ride = DBRide(
        id=str(uuid.uuid4()),
        passenger_id=ride.passenger_id,
        status="requested",
        pickup_latitude=ride.pickup_location.latitude,
        pickup_longitude=ride.pickup_location.longitude,
        pickup_address=ride.pickup_location.address,
        dropoff_latitude=ride.dropoff_location.latitude,
        dropoff_longitude=ride.dropoff_location.longitude,
        dropoff_address=ride.dropoff_location.address,
        distance=0.0,
        estimated_duration=0
    )
    db.add(new_ride)
    db.commit()
    db.refresh(new_ride)
    return db_ride_to_schema(new_ride)

@app.put("/rides/{ride_id}/status")
def update_ride_status(ride_id: str, status: RideStatus, db: Session = Depends(get_db)):
    ride = db.query(DBRide).filter(DBRide.id == ride_id).first()
    if not ride:
        raise HTTPException(status_code=404, detail="Ride not found")
    
    ride.status = status
    now = datetime.utcnow()
    
    if status == "accepted":
        ride.accepted_at = now
    elif status == "picking_up":
        ride.picked_up_at = now
    elif status == "in_progress":
        ride.picked_up_at = now
    elif status == "completed":
        ride.completed_at = now
    elif status == "cancelled":
        ride.cancelled_at = now
    
    db.commit()
    return {"message": "Ride status updated successfully"}

# Enhanced Ride Management Endpoints
@app.post("/rides/{ride_id}/assign")
def assign_ride_to_driver(
    ride_id: str,
    assignment: RideAssignment,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin)
):
    """Admin assigns a driver to a ride"""
    ride = db.query(DBRide).filter(DBRide.id == ride_id).first()
    if not ride:
        raise HTTPException(status_code=404, detail="Ride not found")
    
    if ride.status != "requested":
        raise HTTPException(status_code=400, detail="Ride is not in requested status")
    
    # Verify driver exists and is online
    driver = db.query(DBDriver).filter(DBDriver.id == assignment.driver_id).first()
    if not driver:
        raise HTTPException(status_code=404, detail="Driver not found")
    
    if not driver.is_online:
        raise HTTPException(status_code=400, detail="Driver is not online")
    
    # Update ride
    ride.driver_id = assignment.driver_id
    ride.status = "assigned"
    ride.assigned_at = datetime.utcnow()
    
    db.commit()
    return {"message": f"Ride assigned to driver successfully", "ride_id": ride_id, "driver_id": assignment.driver_id}

@app.post("/rides/{ride_id}/start")
def start_ride(
    ride_id: str,
    ride_start: RideStart,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_driver)
):
    """Driver starts a ride and enters starting kilometers"""
    # Get driver profile
    driver = db.query(DBDriver).filter(DBDriver.user_id == current_user.id).first()
    if not driver:
        raise HTTPException(status_code=404, detail="Driver profile not found")
    
    # Get ride
    ride = db.query(DBRide).filter(DBRide.id == ride_id).first()
    if not ride:
        raise HTTPException(status_code=404, detail="Ride not found")
    
    # Verify driver is assigned to this ride
    if ride.driver_id != driver.id:
        raise HTTPException(status_code=403, detail="You are not assigned to this ride")
    
    if ride.status != "assigned":
        raise HTTPException(status_code=400, detail="Ride is not in assigned status")
    
    # Update ride status
    ride.status = "in_progress"
    ride.picked_up_at = datetime.utcnow()
    
    # Create kilometer entry
    km_entry = DBKilometerEntry(
        id=str(uuid.uuid4()),
        driver_id=driver.id,
        start_km=ride_start.start_km,
        ride_id=ride_id,
        status="started"
    )
    db.add(km_entry)
    
    # Update driver's current km reading
    driver.current_km_reading = ride_start.start_km
    
    db.commit()
    return {"message": "Ride started successfully", "ride_id": ride_id, "start_km": ride_start.start_km}

@app.post("/rides/{ride_id}/complete")
def complete_ride(
    ride_id: str,
    ride_complete: RideComplete,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_driver)
):
    """Driver completes a ride and enters ending kilometers"""
    # Get driver profile
    driver = db.query(DBDriver).filter(DBDriver.user_id == current_user.id).first()
    if not driver:
        raise HTTPException(status_code=404, detail="Driver profile not found")
    
    # Get ride
    ride = db.query(DBRide).filter(DBRide.id == ride_id).first()
    if not ride:
        raise HTTPException(status_code=404, detail="Ride not found")
    
    # Verify driver is assigned to this ride
    if ride.driver_id != driver.id:
        raise HTTPException(status_code=403, detail="You are not assigned to this ride")
    
    if ride.status != "in_progress":
        raise HTTPException(status_code=400, detail="Ride is not in progress")
    
    # Update ride status
    ride.status = "completed"
    ride.completed_at = datetime.utcnow()
    ride.actual_duration = ride_complete.actual_duration
    
    # Calculate distance and update fare
    distance = ride_complete.end_km - ride.start_km if hasattr(ride, 'start_km') else 0
    ride.distance = distance
    
    # Complete kilometer entry
    km_entry = db.query(DBKilometerEntry).filter(
        DBKilometerEntry.ride_id == ride_id,
        DBKilometerEntry.status == "started"
    ).first()
    
    if km_entry:
        km_entry.end_km = ride_complete.end_km
        km_entry.status = "completed"
    
    # Update driver's current km reading and stats
    driver.current_km_reading = ride_complete.end_km
    driver.total_rides += 1
    
    db.commit()
    return {"message": "Ride completed successfully", "ride_id": ride_id, "end_km": ride_complete.end_km, "distance": distance}

@app.get("/rides/pending", response_model=List[Ride])
def get_pending_rides(db: Session = Depends(get_db), current_user: User = Depends(get_current_admin)):
    """Get all pending rides (admin only)"""
    rides = db.query(DBRide).filter(DBRide.status == "requested").all()
    return [db_ride_to_schema(r) for r in rides]

@app.get("/rides/assigned", response_model=List[Ride])
def get_assigned_rides(db: Session = Depends(get_db), current_user: User = Depends(get_current_driver)):
    """Get rides assigned to current driver"""
    driver = db.query(DBDriver).filter(DBDriver.user_id == current_user.id).first()
    if not driver:
        raise HTTPException(status_code=404, detail="Driver profile not found")
    
    rides = db.query(DBRide).filter(
        DBRide.driver_id == driver.id,
        DBRide.status.in_(["assigned", "in_progress"])
    ).all()
    return [db_ride_to_schema(r) for r in rides]

@app.get("/rides", response_model=List[Ride])
def get_rides(passenger_id: Optional[str] = None, driver_id: Optional[str] = None, db: Session = Depends(get_db)):
    print(f"/rides endpoint called with passenger_id={passenger_id}, driver_id={driver_id}")
    query = db.query(DBRide)
    if passenger_id:
        query = query.filter(DBRide.passenger_id == passenger_id)
    if driver_id:
        query = query.filter(DBRide.driver_id == driver_id)
    rides = query.all()
    print(f"Rides found for passenger_id={passenger_id}: {[r.id for r in rides]}")
    return [db_ride_to_schema(r) for r in rides]

# Dashboard endpoints
@app.get("/dashboard/stats", response_model=DashboardStats)
def get_dashboard_stats(db: Session = Depends(get_db), current_user: User = Depends(get_current_admin)):
    total_drivers = db.query(DBDriver).count()
    active_drivers = db.query(DBDriver).filter(DBDriver.is_online == True).count()
    total_rides = db.query(DBRide).count()
    pending_leave_requests = db.query(DBLeaveRequest).filter(DBLeaveRequest.status == "pending").count()
    
    fuel_expenses = db.query(DBFuelEntry).all()
    total_fuel_expenses = sum(entry.cost for entry in fuel_expenses)
    
    return DashboardStats(
        total_drivers=total_drivers,
        active_drivers=active_drivers,
        total_rides=total_rides,
        pending_leave_requests=pending_leave_requests,
        total_fuel_expenses=total_fuel_expenses
    )

@app.get("/leave-requests/stats")
def get_leave_request_stats(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Get leave request statistics for the current user or all users (admin)"""
    if current_user.role == "admin":
        # Admin sees all stats
        total_requests = db.query(DBLeaveRequest).count()
        pending_requests = db.query(DBLeaveRequest).filter(DBLeaveRequest.status == "pending").count()
        approved_requests = db.query(DBLeaveRequest).filter(DBLeaveRequest.status == "approved").count()
        rejected_requests = db.query(DBLeaveRequest).filter(DBLeaveRequest.status == "rejected").count()
    else:
        # Driver sees only their own stats
        driver = db.query(DBDriver).filter(DBDriver.user_id == current_user.id).first()
        if not driver:
            raise HTTPException(status_code=404, detail="Driver profile not found")
        
        total_requests = db.query(DBLeaveRequest).filter(DBLeaveRequest.driver_id == driver.id).count()
        pending_requests = db.query(DBLeaveRequest).filter(
            DBLeaveRequest.driver_id == driver.id,
            DBLeaveRequest.status == "pending"
        ).count()
        approved_requests = db.query(DBLeaveRequest).filter(
            DBLeaveRequest.driver_id == driver.id,
            DBLeaveRequest.status == "approved"
        ).count()
        rejected_requests = db.query(DBLeaveRequest).filter(
            DBLeaveRequest.driver_id == driver.id,
            DBLeaveRequest.status == "rejected"
        ).count()
    
    return {
        "total_requests": total_requests,
        "pending_requests": pending_requests,
        "approved_requests": approved_requests,
        "rejected_requests": rejected_requests
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)