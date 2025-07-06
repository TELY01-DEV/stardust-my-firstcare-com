# My FirstCare Opera Panel - RBAC Implementation Guide

## Role-Based Access Control (RBAC)

The My FirstCare Opera Panel implements a comprehensive RBAC system integrated with Stardust-V1 JWT authentication. The system supports a hierarchical role structure where higher roles inherit permissions from lower roles.

## Role Hierarchy

```
superadmin > admin > operator > viewer
```

### Role Definitions

1. **superadmin** - Full system access
   - Inherits: admin, operator, viewer permissions
   - Additional: System configuration, user management

2. **admin** - Administrative access
   - Inherits: operator, viewer permissions
   - Additional: Delete data, modify configurations

3. **operator** - Operational access
   - Inherits: viewer permissions
   - Additional: Submit device data, manage devices

4. **viewer** - Read-only access
   - Basic: View data, statistics, device lists

## API Endpoint Permissions

### Authentication Endpoints (`/auth`)
- `POST /auth/login` - **Public** (no authentication required)
- `GET /auth/me` - **Authenticated** (any valid user)
- `POST /auth/validate` - **Authenticated** (any valid user)
- `GET /auth/test/viewer` - **Viewer+** (viewer, operator, admin, superadmin)
- `GET /auth/test/operator` - **Operator+** (operator, admin, superadmin)
- `GET /auth/test/admin` - **Admin+** (admin, superadmin)
- `GET /auth/test/superadmin` - **Superadmin** (superadmin only)

### AVA4 Device Endpoints (`/api/ava4`)
- `GET /api/ava4/devices` - **Viewer+** (read device list)
- `GET /api/ava4/data` - **Viewer+** (read device data)
- `GET /api/ava4/stats` - **Viewer+** (read statistics)
- `POST /api/ava4/data` - **Operator+** (submit device data)
- `DELETE /api/ava4/data/{record_id}` - **Admin+** (delete data records)

### Kati Watch Endpoints (`/api/kati`)
- `GET /api/kati/devices` - **Viewer+** (read device list)
- `GET /api/kati/data` - **Viewer+** (read device data)
- `GET /api/kati/stats` - **Viewer+** (read statistics)
- `POST /api/kati/data` - **Operator+** (submit device data)
- `DELETE /api/kati/data/{record_id}` - **Admin+** (delete data records)

### Qube-Vital Endpoints (`/api/qube-vital`)
- `GET /api/qube-vital/devices` - **Viewer+** (read device list)
- `GET /api/qube-vital/data` - **Viewer+** (read device data)
- `GET /api/qube-vital/stats` - **Viewer+** (read statistics)
- `POST /api/qube-vital/data` - **Operator+** (submit device data)

### Medical History Endpoints (`/api/history`)
- `GET /api/history/{data_type}` - **Viewer+** (read medical history)

### Admin Panel (`/admin`)
- `GET /admin/` - **Viewer+** (access admin dashboard)
- Various admin endpoints - **Admin+** or **Superadmin** (based on functionality)

## Implementation Details

### Role Checking with Hierarchy
The system implements intelligent role checking that respects the hierarchy:

```python
role_hierarchy = {
    "superadmin": ["superadmin", "admin", "operator", "viewer"],
    "admin": ["admin", "operator", "viewer"],
    "operator": ["operator", "viewer"],
    "viewer": ["viewer"]
}
```

### FastAPI Dependencies
The system uses FastAPI dependency injection for role enforcement:

```python
# Role-based dependencies
async def require_superadmin(user: Dict[str, Any] = Depends(get_current_user))
async def require_admin(user: Dict[str, Any] = Depends(get_current_user))
async def require_operator(user: Dict[str, Any] = Depends(get_current_user))
async def require_viewer(user: Dict[str, Any] = Depends(get_current_user))
```

### Integration with Stardust-V1
- JWT tokens are validated against the Stardust-V1 authentication service
- User roles are extracted from the JWT payload
- No local user management - all authentication is centralized

## Security Features

1. **JWT Token Validation**: All protected endpoints require valid JWT tokens
2. **Role-based Authorization**: Endpoints check user roles before granting access
3. **Hierarchical Permissions**: Higher roles automatically inherit lower role permissions
4. **Centralized Authentication**: Integrates with Stardust-V1 for consistent user management
5. **Audit Logging**: All admin actions and data access are logged for security auditing

## Usage Examples

### Testing Role Hierarchy
```bash
# Login and get token
TOKEN=$(curl -s -X POST "http://localhost:5055/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "password"}' | jq -r '.access_token')

# Test different permission levels
curl -H "Authorization: Bearer $TOKEN" "http://localhost:5055/auth/test/viewer"
curl -H "Authorization: Bearer $TOKEN" "http://localhost:5055/auth/test/operator"  
curl -H "Authorization: Bearer $TOKEN" "http://localhost:5055/auth/test/admin"
curl -H "Authorization: Bearer $TOKEN" "http://localhost:5055/auth/test/superadmin"
```

### Access Device Data
```bash
# View devices (requires viewer+ role)
curl -H "Authorization: Bearer $TOKEN" "http://localhost:5055/api/ava4/devices"

# Submit device data (requires operator+ role)
curl -X POST -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"device_id": "AA:BB:CC:DD:EE:FF", "data": {...}}' \
  "http://localhost:5055/api/ava4/data"
```

## Error Responses

When access is denied due to insufficient permissions:
```json
{
  "detail": "Admin role or higher required"
}
```

When authentication is missing or invalid:
```json
{
  "detail": "Authentication required"
}
```

## Configuration

The RBAC system is configured through environment variables:
- `JWT_AUTH_BASE_URL`: Stardust-V1 authentication service URL
- `ENABLE_JWT_AUTH`: Enable/disable JWT authentication (default: true)

## Future Enhancements

1. **Scope-based Permissions**: Add fine-grained permissions beyond roles
2. **Organization-level Access**: Multi-tenant support with organization isolation
3. **API Rate Limiting**: Role-based API usage limits
4. **Permission Caching**: Cache user permissions for improved performance
5. **Audit Dashboard**: Web interface for viewing access logs and security events
