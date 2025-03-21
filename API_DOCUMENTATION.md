# Gas Delivery Management System API Documentation

This document provides a comprehensive overview of all available APIs in the gas delivery management system.

## Authentication APIs

### 1. Rider Registration
- **Endpoint**: `/api/rider/register`
- **Method**: POST
- **Description**: Register a new rider in the system
- **Required Fields**:
  - first_name
  - last_name
  - phone_number
  - email (optional)
  - password
  - kijiwe_id
- **Response**: Success/failure message with rider details

### 2. Rider Login
- **Endpoint**: `/api/rider/login`
- **Method**: POST
- **Description**: Authenticate a rider
- **Required Fields**:
  - phone_number/email
  - password
- **Response**: Authentication token and rider details

### 3. Change Password
- **Endpoint**: `/api/rider/change-password`
- **Method**: POST
- **Description**: Allow riders to change their password
- **Authentication**: Required
- **Required Fields**:
  - current_password
  - new_password

## Profile Management APIs

### 1. Update Profile
- **Endpoint**: `/api/rider/update-profile`
- **Method**: PUT
- **Description**: Update rider profile information
- **Authentication**: Required
- **Fields**: Profile details that can be updated

### 2. Get Profile
- **Endpoint**: `/api/rider/profile`
- **Method**: GET
- **Description**: Get rider profile information
- **Authentication**: Required

## Order Management APIs

### 1. Available Orders
- **Endpoint**: `/api/orders/available`
- **Method**: GET
- **Description**: Get list of available orders near rider's location
- **Authentication**: Required
- **Parameters**:
  - latitude
  - longitude
  - radius (optional)

### 2. Order Details
- **Endpoint**: `/api/orders/{order_id}`
- **Method**: GET
- **Description**: Get detailed information about a specific order
- **Authentication**: Required
- **Response**: Complete order details including timeline

### 3. Accept Order
- **Endpoint**: `/api/orders/{order_id}/accept`
- **Method**: POST
- **Description**: Allow rider to accept an available order
- **Authentication**: Required

### 4. Decline Order
- **Endpoint**: `/api/orders/{order_id}/decline`
- **Method**: POST
- **Description**: Allow rider to decline an assigned order
- **Authentication**: Required

### 5. Complete Order
- **Endpoint**: `/api/orders/{order_id}/complete`
- **Method**: POST
- **Description**: Mark an order as completed
- **Authentication**: Required

### 6. Order Tracking
- **Endpoint**: `/api/orders/track/{tracking_number}`
- **Method**: GET
- **Description**: Get order status by tracking number
- **Authentication**: Required

## Business Management APIs

### 1. Business List
- **Endpoint**: `/api/businesses`
- **Method**: GET
- **Description**: Get list of registered businesses
- **Authentication**: Required

### 2. Create Business
- **Endpoint**: `/api/businesses`
- **Method**: POST
- **Description**: Register a new business
- **Authentication**: Required
- **Required Fields**: Business details

## Earnings and Statistics APIs

### 1. Earnings Statistics
- **Endpoint**: `/api/rider/earnings/stats`
- **Method**: GET
- **Description**: Get rider earnings statistics
- **Authentication**: Required
- **Parameters**:
  - date_range (today/week/month)

### 2. Earnings Chart Data
- **Endpoint**: `/api/rider/earnings/chart`
- **Method**: GET
- **Description**: Get earnings data for charts
- **Authentication**: Required
- **Parameters**:
  - period (daily/weekly/monthly)

### 3. Delivery History
- **Endpoint**: `/api/rider/delivery-history`
- **Method**: GET
- **Description**: Get rider's delivery history
- **Authentication**: Required
- **Parameters**:
  - date_range (today/week/month)
  - status (optional)
  - sort (date/status)
  - page

## Utility APIs

### 1. Calculate Delivery Fee
- **Endpoint**: `/api/calculate-delivery-fee`
- **Method**: POST
- **Description**: Calculate estimated delivery fee
- **Required Fields**:
  - pickup_location
  - delivery_location
  - gas_type
  - tank_size

### 2. Dashboard Data
- **Endpoint**: `/api/dashboard/data`
- **Method**: GET
- **Description**: Get dashboard statistics and data
- **Authentication**: Required

## Operations API Endpoints

### Orders

#### List Orders
- **URL**: `/api/orders/`
- **Method**: `GET`
- **Auth Required**: Yes
- **Response**: List of all orders with their details
```json
[
    {
        "id": 1,
        "tracking_number": "ABC123XY",
        "customer_name": "John Doe",
        "pickup_location": "Business Location",
        "delivery_location": "Customer Address",
        "status": "pending",
        "price": "50.00",
        "delivery_fee": "10.00",
        "total_amount": "60.00",
        "created_at": "2025-03-02T16:30:00Z"
    }
]
```

#### Get Order Details
- **URL**: `/api/orders/{tracking_number}/`
- **Method**: `GET`
- **Auth Required**: Yes
- **Response**: Detailed information about a specific order
```json
{
    "id": 1,
    "tracking_number": "ABC123XY",
    "customer_name": "John Doe",
    "pickup_location": "Business Location",
    "delivery_location": "Customer Address",
    "delivery_latitude": "-6.776012",
    "delivery_longitude": "39.178326",
    "status": "pending",
    "price": "50.00",
    "delivery_fee": "10.00",
    "total_amount": "60.00",
    "surge_fee": "5.00",
    "bulk_discount": "0.00",
    "quantity": 1,
    "created_at": "2025-03-02T16:30:00Z",
    "updated_at": "2025-03-02T16:30:00Z"
}
```

### Kijiwe Locations

#### List Kijiwe Locations
- **URL**: `/api/kijiwe/`
- **Method**: `GET`
- **Auth Required**: Yes
- **Response**: List of all kijiwe locations
```json
[
    {
        "id": 1,
        "name": "Kijiwe 1",
        "latitude": "-6.776012",
        "longitude": "39.178326",
        "address": "Street Address",
        "created_at": "2025-03-02T16:30:00Z"
    }
]
```

#### Get Kijiwe Details
- **URL**: `/api/kijiwe/{id}/`
- **Method**: `GET`
- **Auth Required**: Yes
- **Response**: Detailed information about a specific kijiwe location
```json
{
    "id": 1,
    "name": "Kijiwe 1",
    "latitude": "-6.776012",
    "longitude": "39.178326",
    "address": "Street Address",
    "created_at": "2025-03-02T16:30:00Z",
    "updated_at": "2025-03-02T16:30:00Z"
}
```

## General Notes

1. **Authentication**:
   - Most endpoints require authentication via Bearer token
   - Token should be included in Authorization header

2. **Error Handling**:
   - All APIs return appropriate HTTP status codes
   - Error responses include a message explaining the error

3. **Rate Limiting**:
   - APIs may have rate limiting applied
   - Respect the rate limit headers in responses

4. **Data Formats**:
   - All request/response bodies are in JSON format
   - Dates are in ISO 8601 format
   - Coordinates are in decimal degrees (latitude, longitude)

5. **Pagination**:
   - List endpoints support pagination
   - Use page parameter for pagination
   - Response includes total count and next/previous page links

## Error Responses
All endpoints may return the following error responses:

### 401 Unauthorized
```json
{
    "detail": "Authentication credentials were not provided."
}
```

### 404 Not Found
```json
{
    "detail": "Not found."
}
```

### 500 Internal Server Error
```json
{
    "error": "Internal server error message"
}
