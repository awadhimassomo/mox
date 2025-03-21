# Gas Delivery System URL Guide

## Quick Access Links

### 🏠 Main Pages
- **Home Page**: `/`
- **Operations Dashboard**: `/dashboard/`
- **Rider Dashboard**: `/rider/orders/`
- **Business Dashboard**: `/businesses/`

## 🔐 Authentication URLs

### Operations Team
- **Login**: `http://127.0.0.1:8000/ofdashboard/login/`
- **Register**: `/register/`
- **Logout**: `/logout/`

### Riders
- **Login**: `/rider/login/`
- **Register**: `/rider/register/`
- **Logout**: `/logout/`

### Business Users
- **Login**: `/`
- **Registration**: `/Registration`
- **OTP Verification**: `/Otp`

## 👨‍💼 Operations Dashboard

### Order Management
- **All Orders**: `/orders/`
- **Dashboard Overview**: `/dashboard/`
- **Business List**: `/businesses/`

### API Endpoints
- **Dashboard Data**: `/api/dashboard-data/`
- **Assign Rider**: `/api/orders/<order_id>/assign/<rider_id>/`
- **Find Nearby Riders**: `/api/orders/<order_id>/nearby-riders/`

## 🚴 Rider Portal

### Main Pages
- **Orders Dashboard**: `/rider/orders/`
- **Profile**: `/rider/profile/`
- **Earnings**: `/rider/earnings/`
- **Delivery History**: `/rider/history/`

### Rider API Endpoints
- **Available Orders**: `/api/available-orders/`
- **Accept Order**: `/api/rider/accept-order/<order_id>/`
- **Decline Order**: `/api/rider/decline-order/<order_id>/`
- **Start Delivery**: `/api/rider/start-delivery/<order_id>/`
- **Complete Order**: `/api/rider/complete-order/<order_id>/`
- **Update Location**: `/api/rider/update-location/`
- **Update Profile**: `/api/rider/update-profile/`
- **Check Orders**: `/api/rider/check-orders/`

## 🏢 Business Portal

### Registration Flow
1. **Start Registration**: `/Registration`
2. **Enter OTP**: `/Otp`
3. **Complete Setup**: `/postsignUp/`

## 📱 Mobile App Endpoints

### Authentication
- **Rider Registration**: `/api/rider/register/`
- **Rider Login**: `/api/rider/login/`

### Order Management
- **Check Orders**: `/api/rider/check-orders/`
- **Available Orders**: `/api/available-orders/`
- **Accept Order**: `/api/rider/accept-order/<order_id>/`
- **Start Delivery**: `/api/rider/start-delivery/<order_id>/`
- **Complete Order**: `/api/rider/complete-order/<order_id>/`

## Web Interface URLs

### Operations Module

#### Orders
- `/operations/orders/` - List all orders
- `/operations/orders/<tracking_number>/` - View details of a specific order

#### Kijiwe Locations
- `/operations/kijiwe/` - List all kijiwe locations
- `/operations/kijiwe/<id>/` - View details of a specific kijiwe location

### Customer Module
- `/customers/register/` - Customer registration page
- `/customers/login/` - Customer login page
- `/customers/logout/` - Customer logout
- `/customers/dashboard/` - Customer dashboard

### Rider Module
- `/riders/register/` - Rider registration page
- `/riders/login/` - Rider login page
- `/riders/logout/` - Rider logout
- `/riders/dashboard/` - Rider dashboard

### Business Module
- `/business/register/` - Business registration page
- `/business/login/` - Business login page
- `/business/logout/` - Business logout
- `/business/dashboard/` - Business dashboard

## API Endpoints

### Operations API
- `/api/orders/` - List all orders (GET)
- `/api/orders/<tracking_number>/` - Get order details (GET)
- `/api/kijiwe/` - List all kijiwe locations (GET)
- `/api/kijiwe/<id>/` - Get kijiwe details (GET)

### Authentication
- `/api-auth/` - DRF authentication endpoints
- `/api-auth/login/` - API login
- `/api-auth/logout/` - API logout

## Admin Interface
- `/admin/` - Django admin interface

## Development Tools
- `/__reload__/` - Django browser reload endpoint (development only)

## Tips for URL Usage

1. **Role-Based Access**:
   - Operations team uses `/login/`
   - Riders use `/rider/login/`
   - Businesses use the main page `/`

2. **Dashboard Access**:
   - Operations: `/dashboard/`
   - Riders: `/rider/orders/`
   - Businesses: View through mobile app

3. **API Pattern**:
   - Rider APIs start with `/api/rider/`
   - Dashboard APIs start with `/api/dashboard-data/`
   - Order management APIs use `/api/orders/`

4. **URL Parameters**:
   - `<order_id>`: Replace with actual order ID
   - `<rider_id>`: Replace with actual rider ID

## Common Tasks

### For Operations Team
1. **Assign Order to Rider**:
   - View orders at `/orders/`
   - Find nearby riders at `/api/orders/<order_id>/nearby-riders/`
   - Assign rider at `/api/orders/<order_id>/assign/<rider_id>/`

### For Riders
1. **Start Working**:
   - Login at `/rider/login/`
   - View orders at `/rider/orders/`
   - Check earnings at `/rider/earnings/`

### For Businesses
1. **Register Business**:
   - Start at `/Registration`
   - Complete OTP verification at `/Otp`
   - Finish setup at `/postsignUp/`
