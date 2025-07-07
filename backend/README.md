# RideShare Backend API

A Python FastAPI backend with SQLite database for the RideShare mobile application.

## Features

- **User Authentication**: JWT-based authentication with role-based access control
- **Driver Management**: Complete driver profile management with vehicle information
- **Kilometer Tracking**: Track driver kilometers for each ride
- **Fuel Management**: Track fuel expenses (can be added by drivers or admins)
- **Leave Requests**: Driver leave request system with admin approval
- **Ride Management**: Complete ride lifecycle management
- **Real-time Status**: Driver online/offline status tracking
- **Admin Dashboard**: Comprehensive admin controls and analytics

## Setup

1. **Install Dependencies**:
   ```bash
   cd backend
   pip install -r requirements.txt
   ```

2. **Environment Variables**:
   Copy `.env` file and update the SECRET_KEY for production:
   ```bash
   cp .env.example .env
   ```

3. **Run the Server**:
   ```bash
   python main.py
   ```
   
   Or using uvicorn directly:
   ```bash
   uvicorn main:app --reload --host 0.0.0.0 --port 8000
   ```

4. **Access API Documentation**:
   - Swagger UI: http://localhost:8000/docs
   - ReDoc: http://localhost:8000/redoc

## Default Users

The system creates default users on first startup:

- **Admin**: admin@rideshare.com / password
- **Driver**: driver@rideshare.com / password  
- **Passenger**: passenger@rideshare.com / password

## API Endpoints

### Authentication
- `POST /auth/login` - User login
- `GET /auth/me` - Get current user info

### Drivers
- `GET /drivers` - Get all drivers (admin only)
- `GET /drivers/{driver_id}` - Get specific driver
- `PUT /drivers/{driver_id}/status` - Update driver status (admin)
- `PUT /drivers/me/status` - Update own status (driver)

### Kilometer Tracking
- `POST /km-entries` - Create kilometer entry
- `PUT /km-entries/{entry_id}/complete` - Complete kilometer entry
- `GET /km-entries` - Get kilometer entries

### Fuel Management
- `POST /fuel-entries` - Create fuel entry
- `GET /fuel-entries` - Get fuel entries

### Leave Requests
- `POST /leave-requests` - Create leave request
- `PUT /leave-requests/{request_id}/review` - Review leave request (admin)
- `GET /leave-requests` - Get leave requests

### Rides
- `POST /rides` - Create new ride
- `PUT /rides/{ride_id}/status` - Update ride status
- `GET /rides` - Get rides

### Dashboard
- `GET /dashboard/stats` - Get dashboard statistics (admin)

## Database Schema

The SQLite database includes the following tables:
- `users` - User accounts
- `drivers` - Driver profiles and vehicle info
- `passengers` - Passenger profiles
- `admins` - Admin profiles
- `rides` - Ride information
- `kilometer_entries` - Kilometer tracking
- `fuel_entries` - Fuel expense tracking
- `leave_requests` - Driver leave requests

## Security

- JWT tokens for authentication
- Role-based access control (admin, driver, passenger)
- Password hashing with bcrypt
- CORS enabled for frontend integration

## Production Deployment

1. Change the SECRET_KEY in `.env`
2. Configure proper CORS origins
3. Use a production WSGI server like Gunicorn
4. Consider using PostgreSQL for production instead of SQLite
5. Set up proper logging and monitoring

## Integration with Mobile App

The mobile app should:
1. Store the JWT token after login
2. Include the token in Authorization header: `Bearer <token>`
3. Handle token expiration and refresh
4. Update API base URL to point to your backend server

Example API integration in React Native:
```javascript
const API_BASE_URL = 'http://your-backend-url:8000';

const apiCall = async (endpoint, options = {}) => {
  const token = await AsyncStorage.getItem('token');
  
  const response = await fetch(`${API_BASE_URL}${endpoint}`, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${token}`,
      ...options.headers,
    },
  });
  
  return response.json();
};
```