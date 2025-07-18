# Postman Collections

This directory contains Postman collection files for testing the My FirstCare Opera Panel API.

## Files

### Main Collections
- `Updated_MyFirstCare_API_Collection.json` - Updated API collection with all endpoints
- `My_FirstCare_Opera_Panel_API_COMPLETE_AUTH.postman_collection.json` - Complete collection with authentication
- `My_FirstCare_Opera_Panel_API_UPDATED_AUTH.postman_collection.json` - Updated collection with enhanced authentication

### Environment Files
- `Updated_MyFirstCare_API_Environment.json` - Environment configuration for API testing

## Usage

### Importing Collections
1. Open Postman
2. Click "Import" button
3. Select the collection file you want to import
4. Import the environment file for proper configuration

### Environment Setup
1. Import the environment file
2. Set the `base_url` variable to your API endpoint
3. Configure authentication tokens as needed

### Testing Workflow
1. Start with authentication endpoints
2. Test device management endpoints
3. Test patient management endpoints
4. Test analytics and monitoring endpoints

## Features

- **Complete API Coverage**: All endpoints included
- **Authentication Ready**: Pre-configured with JWT authentication
- **Environment Variables**: Configurable for different environments
- **Request Examples**: Sample requests for all endpoints
- **Response Validation**: Expected response structures included

## Environment Variables

- `base_url`: API base URL (e.g., http://localhost:5054)
- `auth_token`: JWT authentication token
- `patient_id`: Sample patient ID for testing
- `device_id`: Sample device ID for testing 