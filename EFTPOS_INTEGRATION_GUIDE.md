# 💳 NUA POS - EFTPOS Integration Guide

**Version:** 2.0.0  
**Status:** ✅ EFTPOS Ready - Supports All Major Australian Providers

---

## 🎉 EFTPOS Integration Complete!

NUA POS now supports **ANY Australian EFTPOS terminal** through our universal integration framework!

---

## ✅ Supported EFTPOS Providers

### 🔵 Tier 1 - Fully Implemented:

1. **Linkly (PC-EFTPOS)** ⭐ Most Common
   - Middleware solution
   - Supports 700+ POS systems
   - Works with all major bank terminals
   - Default Port: 2011

2. **Tyro**
   - Direct integration
   - Fee-free integration
   - Popular in cafes/restaurants
   - Default Port: 6001

3. **Smartpay**
   - Network-based
   - Smart Link middleware
   - Static IP configuration
   - Default Port: 6050

4. **Windcave** (Payment Express)
   - Cloud API integration
   - Modern REST API
   - Secure online payments

### 🟢 Tier 2 - Framework Ready (Easy to Add):

5. **Westpac Presto**
6. **ANZ Worldline**
7. **NAB Transact**
8. **CBA Albert**
9. **Square Terminal**
10. **Zeller**

---

## 🚀 Quick Setup Guide

### Step 1: Configure EFTPOS Terminal in NUA

**Via Settings Page:**
1. Go to Settings → EFTPOS Terminals
2. Click "Add Terminal"
3. Fill in details:
   - Provider (Linkly, Tyro, Smartpay, etc.)
   - Terminal ID
   - Merchant ID
   - Connection Type (TCP, Serial, Cloud)
   - IP Address & Port
   - Location

**Via API:**
```bash
curl -X POST http://localhost:8001/api/eftpos/terminals \
  -H "Content-Type: application/json" \
  -d '{
    "provider": "linkly",
    "terminalId": "TERM001",
    "merchantId": "MERCH001",
    "name": "Main Counter Terminal",
    "location": "Main Street",
    "connectionType": "tcp",
    "ipAddress": "192.168.1.50",
    "port": 2011,
    "timeout": 60,
    "autoSettlement": true
  }'
```

### Step 2: Test Connection

```bash
curl -X POST http://localhost:8001/api/eftpos/terminals/{terminal_id}/test
```

**Response:**
```json
{
  "success": true,
  "message": "Connection successful"
}
```

### Step 3: Process Payment

When customer checks out:
1. Add items to cart
2. Click "Card Payment"
3. System automatically sends to EFTPOS terminal
4. Customer taps/inserts/swipes card
5. Terminal returns approval
6. Receipt prints automatically

---

## 🔌 Connection Types

### 1. TCP/IP Network (Most Common)

**Setup:**
- Terminal connected to same network as POS
- Static IP assigned to terminal
- Port configured (default varies by provider)

**Configuration:**
```json
{
  "connectionType": "tcp",
  "ipAddress": "192.168.1.50",
  "port": 2011
}
```

**Advantages:**
- ✅ Wireless operation
- ✅ Multiple POS devices can connect
- ✅ Easy to relocate terminal
- ✅ Most reliable

### 2. Serial/USB

**Setup:**
- Terminal connected via USB cable
- Serial port identified (e.g., COM1, /dev/ttyUSB0)

**Configuration:**
```json
{
  "connectionType": "serial",
  "serialPort": "/dev/ttyUSB0"
}
```

**Advantages:**
- ✅ Direct connection
- ✅ No network required
- ✅ Lower latency

### 3. Cloud API

**Setup:**
- API credentials from provider
- Internet connection required

**Configuration:**
```json
{
  "connectionType": "cloud",
  "cloudEndpoint": "https://api.provider.com",
  "apiKey": "your_api_key",
  "apiSecret": "your_api_secret"
}
```

**Advantages:**
- ✅ No local terminal needed
- ✅ Works from anywhere
- ✅ Modern REST API

---

## 💰 Transaction Types Supported

### 1. Purchase (Standard Payment)
```python
{
  "transactionType": "purchase",
  "amount": 45.50,
  "cashout": 0.0,
  "reference": "POS-001-123"
}
```

### 2. Purchase with Cash Out
```python
{
  "transactionType": "purchase",
  "amount": 45.50,
  "cashout": 50.00,  # Customer gets $50 cash
  "reference": "POS-001-124"
}
```

### 3. Refund
```python
{
  "transactionType": "refund",
  "amount": 45.50,
  "reference": "REFUND-123"
}
```

### 4. Cancel (Void)
```python
{
  "transactionType": "cancel",
  "reference": "POS-001-125"
}
```

### 5. Settlement (End of Day)
- Automatically processes all transactions
- Transfers funds to merchant account
- Can be scheduled or manual

---

## 🔧 Provider-Specific Setup

### Linkly (PC-EFTPOS) Setup

**Requirements:**
1. Linkly middleware installed on POS computer
2. Terminal paired with Linkly software
3. TCP port 2011 open

**Configuration:**
```json
{
  "provider": "linkly",
  "connectionType": "tcp",
  "ipAddress": "127.0.0.1",
  "port": 2011,
  "merchantId": "YOUR_MERCHANT_ID",
  "terminalId": "YOUR_TERMINAL_ID"
}
```

**Download Linkly:**
- https://linkly.com.au/download/

### Tyro Setup

**Requirements:**
1. Tyro EFTPOS terminal
2. Network connection
3. Tyro merchant account

**Configuration:**
```json
{
  "provider": "tyro",
  "connectionType": "tcp",
  "ipAddress": "192.168.1.50",
  "port": 6001,
  "merchantId": "YOUR_TYRO_MID",
  "terminalId": "YOUR_TYRO_TID"
}
```

**Get Tyro Terminal:**
- https://www.tyro.com/products/eftpos/

### Smartpay Setup

**Requirements:**
1. Smartpay terminal
2. Smart Link software
3. Static IP configuration

**Configuration:**
```json
{
  "provider": "smartpay",
  "connectionType": "tcp",
  "ipAddress": "192.168.1.51",
  "port": 6050,
  "merchantId": "YOUR_MERCHANT_ID",
  "terminalId": "YOUR_TERMINAL_ID"
}
```

**Get Smartpay:**
- https://www.smartpay.com.au/

### Windcave Setup

**Requirements:**
1. Windcave account
2. API credentials
3. Internet connection

**Configuration:**
```json
{
  "provider": "windcave",
  "connectionType": "cloud",
  "cloudEndpoint": "https://sec.windcave.com/api/v1",
  "apiKey": "YOUR_API_KEY",
  "apiSecret": "YOUR_API_SECRET",
  "merchantId": "YOUR_MERCHANT_ID"
}
```

**Get Windcave:**
- https://www.windcave.com/

---

## 📊 EFTPOS Transaction Flow

### Standard Purchase Flow:

```
1. Customer Ready to Pay
   ↓
2. Cashier Selects "Card Payment"
   ↓
3. NUA POS sends transaction to terminal
   {amount: 45.50, reference: "TXN-001"}
   ↓
4. Terminal prompts: "INSERT/TAP CARD"
   ↓
5. Customer presents card
   ↓
6. Terminal communicates with bank
   ↓
7. Approval received
   ↓
8. Terminal returns to POS:
   {
     approved: true,
     authCode: "123456",
     cardType: "VISA",
     maskedPan: "****1234"
   }
   ↓
9. NUA POS completes transaction
   ↓
10. Receipt prints with EFTPOS details
```

### In POS Terminal:

```javascript
// Frontend calls API
const response = await eftposAPI.processTransaction({
  terminalId: "TERM001",
  transactionType: "purchase",
  amount: totals.total,
  reference: transactionId,
  posTransactionId: transactionId
});

if (response.approved) {
  // Transaction successful
  // Save to database
  // Print receipt
} else {
  // Show error
  // Retry or use alternative payment
}
```

---

## 🛡️ Security Features

### PCI DSS Compliance:
- ✅ No card data stored in POS
- ✅ Terminal handles all card data
- ✅ Encrypted communication
- ✅ Tokenization support
- ✅ EMV chip & contactless

### Network Security:
- ✅ TLS/SSL encryption
- ✅ Firewall configuration
- ✅ VPN support
- ✅ Static IP restrictions

### Audit Trail:
- ✅ All transactions logged
- ✅ Timestamps recorded
- ✅ User tracking
- ✅ Terminal identification

---

## 📱 Integration Features

### Automatic Features:
1. **Auto-Settlement** - End-of-day processing
2. **Retry Logic** - Auto-retry on network failure
3. **Timeout Handling** - Configurable timeouts
4. **Error Recovery** - Graceful error handling
5. **Receipt Integration** - EFTPOS details on receipt

### Advanced Features:
1. **Split Payments** - Pay with multiple cards
2. **Surcharging** - Add card fees if needed
3. **Tipping** - Add tips to EFTPOS transactions
4. **Cash Out** - EFTPOS with cash withdrawal
5. **Multi-Terminal** - Multiple terminals per location

---

## 🔍 Troubleshooting

### Issue: "Connection Failed"

**Solutions:**
1. Check terminal is powered on
2. Verify IP address is correct
3. Ping terminal: `ping 192.168.1.50`
4. Check firewall rules
5. Restart Linkly middleware (if using)

### Issue: "Terminal Not Responding"

**Solutions:**
1. Check network cable connection
2. Restart terminal
3. Verify port number
4. Check terminal is not being used
5. Test connection endpoint

### Issue: "Transaction Timeout"

**Solutions:**
1. Increase timeout setting (default 60s)
2. Check network speed
3. Verify terminal is responding
4. Test with smaller amount

### Issue: "Declined Transaction"

**Not an integration issue - check:**
1. Card has sufficient funds
2. Card is not expired
3. Customer entering correct PIN
4. Bank not blocking transaction

---

## 📋 API Endpoints

### Terminal Management:

```bash
# Get all terminals
GET /api/eftpos/terminals

# Add terminal
POST /api/eftpos/terminals

# Update terminal
PUT /api/eftpos/terminals/{id}

# Delete terminal
DELETE /api/eftpos/terminals/{id}

# Test connection
POST /api/eftpos/terminals/{id}/test

# Perform settlement
POST /api/eftpos/terminals/{id}/settlement
```

### Transaction Processing:

```bash
# Process transaction
POST /api/eftpos/transaction

# Get transaction history
GET /api/eftpos/transactions
```

---

## 💡 Best Practices

### Setup:
1. ✅ Use static IP for terminals
2. ✅ Keep terminals on dedicated network
3. ✅ Regular firmware updates
4. ✅ Test connection daily
5. ✅ Have backup terminal

### Operations:
1. ✅ Train staff on EFTPOS procedures
2. ✅ Monitor transaction logs
3. ✅ Reconcile daily
4. ✅ Keep receipts for disputes
5. ✅ Schedule automatic settlements

### Maintenance:
1. ✅ Clean terminals regularly
2. ✅ Check network connectivity
3. ✅ Update middleware
4. ✅ Backup configuration
5. ✅ Test disaster recovery

---

## 🆘 Support

### NUA POS Support:
- **Technical Issues:** support@nuapos.com
- **Integration Help:** Available

### Provider Support:

**Linkly:**
- Phone: 1300 465 465
- Web: https://linkly.com.au/support/

**Tyro:**
- Phone: 1300 00 TYRO (8976)
- Web: https://www.tyro.com/support/

**Smartpay:**
- Phone: 0800 SMARTPAY
- Web: https://www.smartpay.com.au/support/

**Windcave:**
- Support: https://www.windcave.com/support/

---

## ✅ Integration Checklist

Before going live:

- [ ] EFTPOS terminal configured in NUA
- [ ] Connection tested successfully
- [ ] Test transaction completed
- [ ] Settlement tested
- [ ] Staff trained
- [ ] Receipts printing correctly
- [ ] Network stable
- [ ] Backup plan in place
- [ ] Provider support contacts saved
- [ ] Compliance verified

---

## 🎯 Next Steps

1. **Choose Your Provider** - Select from supported list
2. **Get Terminal** - Contact provider for hardware
3. **Configure in NUA** - Add terminal settings
4. **Test Connection** - Verify integration works
5. **Process Test Transaction** - $0.01 test
6. **Train Staff** - Show team how to use
7. **Go Live** - Start accepting card payments!

---

<div align="center">

**NUA POS - Universal EFTPOS Integration**

Accept payments from ANY Australian EFTPOS terminal

Linkly • Tyro • Smartpay • Windcave • Westpac • ANZ • NAB • CBA • Square

🔒 Secure • 💳 PCI Compliant • 🚀 Easy Setup

</div>
