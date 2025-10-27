// Mock data for Square POS Clone

export const products = [
  {
    id: '1',
    name: 'Espresso',
    category: 'Beverages',
    price: 4.50,
    cost: 1.20,
    stock: 150,
    sku: 'BEV-ESP-001',
    image: 'https://images.unsplash.com/photo-1510591509098-f4fdc6d0ff04?w=200',
    gstRate: 10
  },
  {
    id: '2',
    name: 'Cappuccino',
    category: 'Beverages',
    price: 5.00,
    cost: 1.50,
    stock: 200,
    sku: 'BEV-CAP-001',
    image: 'https://images.unsplash.com/photo-1572442388796-11668a67e53d?w=200',
    gstRate: 10
  },
  {
    id: '3',
    name: 'Chocolate Cake',
    category: 'Bakery',
    price: 6.50,
    cost: 2.00,
    stock: 50,
    sku: 'BAK-CHO-001',
    image: 'https://images.unsplash.com/photo-1578985545062-69928b1d9587?w=200',
    gstRate: 10
  },
  {
    id: '4',
    name: 'Beef Burger',
    category: 'Food',
    price: 12.00,
    cost: 4.50,
    stock: 80,
    sku: 'FOD-BUR-001',
    image: 'https://images.unsplash.com/photo-1568901346375-23c9450c58cd?w=200',
    gstRate: 10
  },
  {
    id: '5',
    name: 'Soft Drink',
    category: 'Beverages',
    price: 3.50,
    cost: 0.80,
    stock: 300,
    sku: 'BEV-SOD-001',
    image: 'https://images.unsplash.com/photo-1629203851122-3726ecdf080e?w=200',
    gstRate: 10
  },
  {
    id: '6',
    name: 'Caesar Salad',
    category: 'Food',
    price: 10.00,
    cost: 3.50,
    stock: 60,
    sku: 'FOD-SAL-001',
    image: 'https://images.unsplash.com/photo-1546793665-c74683f339c1?w=200',
    gstRate: 10
  }
];

export const promotions = [
  {
    id: 'promo-1',
    name: 'Coffee & Cake Deal',
    type: 'bundle',
    products: ['1', '3'],
    originalPrice: 11.00,
    discountedPrice: 9.00,
    discount: 18,
    active: true,
    schedule: 'All Day'
  },
  {
    id: 'promo-2',
    name: 'Burger & Drink Combo',
    type: 'bundle',
    products: ['4', '5'],
    originalPrice: 15.50,
    discountedPrice: 13.00,
    discount: 16,
    active: true,
    schedule: 'All Day'
  },
  {
    id: 'promo-3',
    name: 'Happy Hour - 20% Off Beverages',
    type: 'category',
    category: 'Beverages',
    discount: 20,
    active: true,
    schedule: '3:00 PM - 6:00 PM'
  }
];

export const customers = [
  {
    id: 'cust-1',
    name: 'Sarah Johnson',
    email: 'sarah.j@email.com',
    phone: '+61 412 345 678',
    membershipTier: 'Gold',
    totalSpent: 2450.00,
    visits: 87,
    joinDate: '2023-06-15',
    points: 2450
  },
  {
    id: 'cust-2',
    name: 'Michael Chen',
    email: 'mchen@email.com',
    phone: '+61 423 456 789',
    membershipTier: 'Platinum',
    totalSpent: 5680.00,
    visits: 156,
    joinDate: '2023-01-20',
    points: 5680
  },
  {
    id: 'cust-3',
    name: 'Emma Wilson',
    email: 'emma.w@email.com',
    phone: '+61 434 567 890',
    membershipTier: 'Silver',
    totalSpent: 890.00,
    visits: 34,
    joinDate: '2024-03-10',
    points: 890
  },
  {
    id: 'cust-4',
    name: 'James Brown',
    email: 'jbrown@email.com',
    phone: '+61 445 678 901',
    membershipTier: 'Bronze',
    totalSpent: 245.00,
    visits: 12,
    joinDate: '2024-10-05',
    points: 245
  }
];

export const transactions = [
  {
    id: 'TXN-20250115-001',
    timestamp: '2025-01-15T09:15:32',
    items: [{ productId: '1', quantity: 2, price: 4.50 }, { productId: '3', quantity: 1, price: 6.50 }],
    subtotal: 15.50,
    gst: 1.55,
    total: 17.05,
    paymentMethod: 'Card',
    customerId: 'cust-1',
    location: 'Main Street',
    cashier: 'John Doe',
    status: 'completed'
  },
  {
    id: 'TXN-20250115-002',
    timestamp: '2025-01-15T09:23:18',
    items: [{ productId: '4', quantity: 1, price: 12.00 }, { productId: '5', quantity: 1, price: 3.50 }],
    subtotal: 15.50,
    gst: 1.55,
    total: 17.05,
    paymentMethod: 'Cash',
    customerId: null,
    location: 'Main Street',
    cashier: 'John Doe',
    status: 'completed'
  },
  {
    id: 'TXN-20250115-003',
    timestamp: '2025-01-15T09:45:07',
    items: [{ productId: '2', quantity: 3, price: 5.00 }],
    subtotal: 15.00,
    gst: 1.50,
    total: 16.50,
    paymentMethod: 'Digital Wallet',
    customerId: 'cust-2',
    location: 'Mall Branch',
    cashier: 'Jane Smith',
    status: 'completed'
  }
];

export const locations = [
  {
    id: 'loc-1',
    name: 'Main Street',
    address: '123 Main St, Sydney NSW 2000',
    phone: '+61 2 9876 5432',
    status: 'active'
  },
  {
    id: 'loc-2',
    name: 'Mall Branch',
    address: '456 Shopping Mall, Sydney NSW 2001',
    phone: '+61 2 9876 5433',
    status: 'active'
  }
];

export const users = [
  {
    id: 'user-1',
    name: 'John Doe',
    email: 'john@company.com',
    role: 'Admin',
    locations: ['loc-1', 'loc-2'],
    status: 'active'
  },
  {
    id: 'user-2',
    name: 'Jane Smith',
    email: 'jane@company.com',
    role: 'Cashier',
    locations: ['loc-2'],
    status: 'active'
  },
  {
    id: 'user-3',
    name: 'Robert Wilson',
    email: 'robert@company.com',
    role: 'Accountant',
    locations: ['loc-1', 'loc-2'],
    status: 'active'
  }
];

export const basReports = [
  {
    id: 'bas-q4-2024',
    quarter: 'Q4 2024',
    period: 'Oct - Dec 2024',
    totalSales: 145680.00,
    gstCollected: 14568.00,
    gstPaid: 3240.00,
    netGst: 11328.00,
    status: 'submitted',
    submittedDate: '2025-01-28',
    dueDate: '2025-02-28'
  },
  {
    id: 'bas-q1-2025',
    quarter: 'Q1 2025',
    period: 'Jan - Mar 2025',
    totalSales: 48920.00,
    gstCollected: 4892.00,
    gstPaid: 1120.00,
    netGst: 3772.00,
    status: 'draft',
    submittedDate: null,
    dueDate: '2025-04-28'
  }
];
