# 🇹🇭 Thai Character Search Guide

## Issue: 500 Error with Thai Characters in Postman

### Problem Description
When searching for Thai names like "กิจกมน" in Postman, you might encounter a 500 error or "Invalid HTTP request" error. This is due to how Postman handles UTF-8 characters in URLs.

### ✅ Solution: Proper URL Encoding

The API **does work correctly** with Thai characters, but they need to be properly URL-encoded when sent via HTTP requests.

## 🔧 How to Fix in Postman

### Method 1: Pre-encode Thai Characters

1. **Convert Thai text to URL encoding**:
   - `กิจกมน` becomes `%E0%B8%81%E0%B8%B4%E0%B8%88%E0%B8%81%E0%B8%A1%E0%B8%99`

2. **Use the encoded string in Postman**:
   ```
   GET /admin/patients?search=%E0%B8%81%E0%B8%B4%E0%B8%88%E0%B8%81%E0%B8%A1%E0%B8%99&limit=5
   ```

### Method 2: Use Postman's Params Tab

1. **Don't type Thai characters directly in the URL**
2. **Use the Params tab in Postman**:
   - Key: `search`
   - Value: `กิจกมน` (Thai characters directly)
   - Postman will automatically URL-encode them

### Method 3: Use Request Body (Recommended)

Instead of query parameters, use POST request with JSON body:

```json
POST /admin/patients/search
Content-Type: application/json

{
    "search": "กิจกมน",
    "limit": 5
}
```

## 🧪 Testing Results

### ✅ Working Examples

**1. URL Encoded (cURL)**:
```bash
curl -X GET "http://stardust.myfirstcare.com:5054/admin/patients?search=%E0%B8%81%E0%B8%B4%E0%B8%88%E0%B8%81%E0%B8%A1%E0%B8%99&limit=5" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

**2. Python Requests**:
```python
import requests

url = 'http://stardust.myfirstcare.com:5054/admin/patients'
params = {'search': 'กิจกมน', 'limit': 5}
headers = {'Authorization': 'Bearer YOUR_TOKEN'}

response = requests.get(url, params=params, headers=headers)
print(response.json())
```

**3. JavaScript/Node.js**:
```javascript
const url = 'http://stardust.myfirstcare.com:5054/admin/patients';
const params = new URLSearchParams({
    search: 'กิจกมน',
    limit: 5
});

fetch(`${url}?${params}`, {
    headers: {
        'Authorization': 'Bearer YOUR_TOKEN'
    }
})
.then(response => response.json())
.then(data => console.log(data));
```

### ❌ What Doesn't Work

**Direct Thai characters in URL (without proper encoding)**:
```bash
# This causes "Invalid HTTP request" error
curl "http://stardust.myfirstcare.com:5054/admin/patients?search=กิจกมน&limit=5"
```

## 🔧 URL Encoding Converter

### Online Tools
- [URL Encoder/Decoder](https://www.urlencoder.org/)
- [W3Schools URL Encoder](https://www.w3schools.com/tags/ref_urlencode.ASP)

### Programmatic Encoding

**Python**:
```python
import urllib.parse
encoded = urllib.parse.quote('กิจกมน')
print(encoded)  # %E0%B8%81%E0%B8%B4%E0%B8%88%E0%B8%81%E0%B8%A1%E0%B8%99
```

**JavaScript**:
```javascript
const encoded = encodeURIComponent('กิจกมน');
console.log(encoded); // %E0%B8%81%E0%B8%B4%E0%B8%88%E0%B8%81%E0%B8%A1%E0%B8%99
```

## 🎯 Postman Collection Update

I'll update the Postman collection to include proper Thai character search examples:

### Example Request in Postman
```
GET {{base_url}}/admin/patients
```

**Params Tab**:
- `search`: `กิจกมน` (Postman will auto-encode)
- `limit`: `5`

**Headers**:
- `Authorization`: `Bearer {{access_token}}`
- `Content-Type`: `application/json; charset=utf-8`

## 🔍 Search Functionality Details

The API searches across multiple fields:
- `first_name`: First name (Thai/English)
- `last_name`: Last name (Thai/English) 
- `id_card`: National ID
- `phone`: Phone number

### Search Query Structure
```javascript
{
  "$or": [
    {"first_name": {"$regex": "กิจกมน", "$options": "i"}},
    {"last_name": {"$regex": "กิจกมน", "$options": "i"}},
    {"id_card": {"$regex": "กิจกมน", "$options": "i"}},
    {"phone": {"$regex": "กิจกมน", "$options": "i"}}
  ]
}
```

## 📊 Expected Response

```json
{
  "patients": [
    {
      "_id": "661f2b5d818cc24bd96a8722",
      "first_name": "กิจกมน",
      "last_name": "ไมตรี",
      "mobile_no": "0864077171",
      "gender": "male",
      "national_id": "35703004328442",
      // ... other patient fields
    }
  ],
  "total": 1,
  "limit": 5,
  "skip": 0
}
```

## 🚀 Best Practices

### 1. Always URL Encode Non-ASCII Characters
- Use proper encoding for Thai, Chinese, Arabic, etc.
- Don't rely on client auto-encoding

### 2. Set Proper Headers
```
Content-Type: application/json; charset=utf-8
Authorization: Bearer YOUR_TOKEN
```

### 3. Use Postman Params Tab
- Let Postman handle encoding automatically
- Avoid typing special characters directly in URLs

### 4. Test with Multiple Methods
- Test with cURL, Postman, and programming languages
- Verify encoding works consistently

## 🔧 Troubleshooting

### Error: "Invalid HTTP request received"
**Cause**: Thai characters not properly URL-encoded  
**Solution**: Use URL encoding or Postman Params tab

### Error: "500 Internal Server Error"
**Cause**: Malformed request due to encoding issues  
**Solution**: Check headers and use proper UTF-8 encoding

### No Results Found
**Cause**: Search term might not match exactly  
**Solution**: Try partial matches or check spelling

## 📞 Support

If you continue to have issues with Thai character searches:

1. **Verify URL encoding** is correct
2. **Check request headers** include UTF-8 charset
3. **Use Postman Params tab** instead of direct URL entry
4. **Test with cURL** to verify server response

---

**✅ CONFIRMED WORKING**: Thai character search functionality is fully operational with proper URL encoding.

**Last Updated**: January 2024  
**Tested With**: กิจกมน (Patient ID: 661f2b5d818cc24bd96a8722) 