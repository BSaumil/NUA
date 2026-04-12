# Test Credentials

## Staff Login (JWT Auth)
- **Owner**: owner@ananta.com / AnantaOwner2026! (full access)
- **Manager**: manager@ananta.com / Staff2026! (most features, no payRate visibility)
- **Cashier**: cashier@ananta.com / Staff2026! (POS, Tables, Customers only)
- **Kitchen**: kitchen@ananta.com / Staff2026! (Kitchen, Pre-Shift only)

## Member Portal (Public)
- Members can signup at /join with email/phone/password
- New members get 50 bonus points + Welcome 15% Off voucher

## API Authentication
- POST /api/auth/login returns JWT token
- Use `Authorization: Bearer <token>` header for protected endpoints
- Cookies also set (access_token, refresh_token) with httpOnly
