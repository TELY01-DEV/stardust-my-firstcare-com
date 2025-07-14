# Postman Collection Setup Guide

## 🚀 Quick Setup Instructions

### 1. Import the Collection
- Import `My_FirstCare_Opera_Panel_API_CRUD.postman_collection.json` into Postman

### 2. Create Environment Variables

Create a new Postman Environment with these variables:

| Variable Name | Value | Type |
|---------------|-------|------|
| `base_url` | `http://localhost:5054` | default |
| `username` | `admin` | default |
| `password` | `Sim!443355` | secret |
| `jwt_token` | *(leave empty - auto-populated)* | default |
| `hospital_user_id` | *(leave empty - auto-populated)* | default |

### 3. Manual Token Setup (Recommended)

If you encounter pre-request script issues, manually get your token:

#### Step 1: Login Request
```bash
curl -X POST "http://localhost:5054/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "Sim!443355"}'
```

#### Step 2: Copy the access_token
Response will look like:
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "user_id": "admin",
  "role": "superadmin"
}
```

#### Step 3: Set JWT Token in Postman
- Go to your Environment
- Set `jwt_token` to the `access_token` value (without "Bearer " prefix)

### 4. Test the Setup

1. **Test Authentication**: 
   - Run `Authentication > Login` request
   - Verify the token is automatically set in environment

2. **Test Hospital Users**:
   - Run `Hospital Users - CRUD > Get All Hospital Users`
   - Should return list of users successfully

## 🔧 Troubleshooting

### Pre-request Script Error
If you get `"Cannot read properties of undefined (reading 'code')"`:

1. **Disable Pre-request Script**:
   - Go to Collection Settings
   - Delete the pre-request script content
   - Use manual token method above

2. **Check Environment Variables**:
   - Ensure `base_url`, `username`, `password` are set
   - Values should not have quotes around them

3. **Check Server Status**:
   ```bash
   curl http://localhost:5054/health
   ```

### Common Issues

| Issue | Solution |
|-------|----------|
| "Invalid or expired token" | Manually get new token using login request |
| "Connection refused" | Ensure Docker container is running on port 5054 |
| "404 Not Found" | Check endpoint URLs match the API routes |
| Environment not found | Create and select the environment in Postman |

## 📋 Available Endpoints

### Hospital Users CRUD
- ✅ `GET /admin/hospital-users` - List all users
- ✅ `GET /admin/hospital-users/{id}` - Get specific user  
- ✅ `POST /admin/hospital-users` - Create new user
- ✅ `PUT /admin/hospital-users/{id}` - Update user
- ✅ `DELETE /admin/hospital-users/{id}` - Delete user
- ✅ `POST /admin/hospital-users/search` - Advanced search
- ✅ `GET /admin/hospital-users/stats/summary` - Statistics

### Sample Test Data
The collection includes pre-filled test data for creating hospital users. Update the `hospital_id` and `type` fields with valid values from your database.

## 🎯 Testing Workflow

1. **Start with Authentication** - Run login to get token
2. **List Hospital Users** - Verify basic functionality  
3. **Create Test User** - Use the create endpoint
4. **Update Test User** - Modify the created user
5. **Search Users** - Test filtering capabilities
6. **View Statistics** - Check data aggregation
7. **Delete Test User** - Clean up test data

The collection includes automatic tests that validate responses and extract IDs for chaining requests. 