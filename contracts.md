# NUA POS Clone - Backend Implementation Contracts

## API Contracts

### Products API
- `GET /api/products` - Get all products with filters (category, search)
- `POST /api/products` - Create new product
- `PUT /api/products/:id` - Update product
- `DELETE /api/products/:id` - Delete product
- `GET /api/products/:id` - Get single product

### Promotions API
- `GET /api/promotions` - Get all promotions
- `POST /api/promotions` - Create promotion
- `PUT /api/promotions/:id` - Update promotion
- `DELETE /api/promotions/:id` - Delete promotion
- `GET /api/promotions/active` - Get active promotions

### Customers API
- `GET /api/customers` - Get all customers with search
- `POST /api/customers` - Create new customer
- `PUT /api/customers/:id` - Update customer
- `GET /api/customers/:id` - Get single customer
- `PUT /api/customers/:id/points` - Update customer points

### Transactions API
- `GET /api/transactions` - Get all transactions with filters (date range, location, cashier)
- `POST /api/transactions` - Create new transaction
- `GET /api/transactions/:id` - Get single transaction
- `GET /api/transactions/hourly` - Get hourly breakdown

### Accounting API
- `GET /api/accounting/summary` - Get financial summary
- `GET /api/accounting/p-and-l` - Get P&L statement
- `GET /api/accounting/reports` - Get various reports

### BAS/GST API
- `GET /api/bas-gst/reports` - Get all BAS reports
- `POST /api/bas-gst/reports` - Generate new BAS report
- `POST /api/bas-gst/submit/:id` - Submit BAS report (mock or API)
- `GET /api/bas-gst/config` - Get ATO API configuration
- `PUT /api/bas-gst/config` - Update ATO API configuration

### Locations API
- `GET /api/locations` - Get all locations
- `POST /api/locations` - Create location
- `PUT /api/locations/:id` - Update location

### Users API
- `GET /api/users` - Get all users
- `POST /api/users` - Create user
- `PUT /api/users/:id` - Update user

### Settings API
- `GET /api/settings/business` - Get business info
- `PUT /api/settings/business` - Update business info
- `GET /api/settings/theme` - Get theme settings
- `PUT /api/settings/theme` - Update theme settings

## MongoDB Data Models

### Product
```
{
  _id: ObjectId,
  id: string (UUID),
  name: string,
  category: string,
  price: number,
  cost: number,
  stock: number,
  sku: string,
  image: string,
  gstRate: number,
  createdAt: datetime,
  updatedAt: datetime
}
```

### Promotion
```
{
  _id: ObjectId,
  id: string (UUID),
  name: string,
  type: string (bundle/category),
  products: [string], // product IDs for bundles
  category: string, // for category-type
  originalPrice: number,
  discountedPrice: number,
  discount: number,
  active: boolean,
  schedule: string,
  createdAt: datetime
}
```

### Customer
```
{
  _id: ObjectId,
  id: string (UUID),
  name: string,
  email: string,
  phone: string,
  membershipTier: string (Bronze/Silver/Gold/Platinum),
  totalSpent: number,
  visits: number,
  joinDate: datetime,
  points: number
}
```

### Transaction
```
{
  _id: ObjectId,
  id: string (TXN-YYYYMMDD-XXX),
  timestamp: datetime,
  items: [{
    productId: string,
    productName: string,
    quantity: number,
    price: number
  }],
  subtotal: number,
  gst: number,
  total: number,
  paymentMethod: string,
  customerId: string (optional),
  customerName: string (optional),
  location: string,
  cashier: string,
  status: string
}
```

### BASReport
```
{
  _id: ObjectId,
  id: string (UUID),
  quarter: string,
  period: string,
  totalSales: number,
  gstCollected: number,
  gstPaid: number,
  netGst: number,
  status: string (draft/submitted),
  submittedDate: datetime (optional),
  dueDate: datetime,
  transactions: [ObjectId] // reference to transactions
}
```

### Location
```
{
  _id: ObjectId,
  id: string (UUID),
  name: string,
  address: string,
  phone: string,
  status: string (active/inactive)
}
```

### User
```
{
  _id: ObjectId,
  id: string (UUID),
  name: string,
  email: string,
  role: string (Admin/Cashier/Accountant),
  locations: [string], // location IDs
  status: string (active/inactive)
}
```

### Settings
```
{
  _id: ObjectId,
  type: string (business/theme),
  data: object // flexible schema for different settings
}
```

## Mock Data to Replace

From `mockData.js`:
- products array → MongoDB products collection
- promotions array → MongoDB promotions collection
- customers array → MongoDB customers collection
- transactions array → MongoDB transactions collection
- basReports array → MongoDB bas_reports collection
- locations array → MongoDB locations collection
- users array → MongoDB users collection

## Frontend Integration Changes

### Files to Update:
1. `pages/Dashboard.jsx` - Replace mock imports with API calls
2. `pages/POSTerminal.jsx` - Connect to transactions API
3. `pages/Products.jsx` - Connect to products & promotions API
4. `pages/Customers.jsx` - Connect to customers API
5. `pages/Inventory.jsx` - Connect to products API
6. `pages/Accounting.jsx` - Connect to accounting & transactions API
7. `pages/BASGST.jsx` - Connect to BAS/GST API
8. `pages/Settings.jsx` - Connect to settings, locations, users API

### New Utility File:
- `src/services/api.js` - Centralized API service with axios

## Implementation Steps

1. **Database Setup**
   - Create MongoDB collections
   - Seed initial data from mockData.js
   - Create indexes for performance

2. **Backend API Development**
   - Implement all CRUD endpoints
   - Add validation and error handling
   - Implement GST calculations
   - Add filtering and search capabilities

3. **Frontend Integration**
   - Create API service layer
   - Replace mock data with API calls
   - Add loading states
   - Add error handling

4. **Testing**
   - Test all CRUD operations
   - Test POS transaction flow
   - Test accounting calculations
   - Test BAS/GST generation
