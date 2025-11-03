from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
from datetime import datetime
import uuid

class EFTPOSConfig(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    provider: str  # tyro, linkly, smartpay, windcave, westpac, anz, nab, cba, square
    terminalId: str
    merchantId: str
    name: str
    location: str
    connectionType: str  # tcp, serial, cloud, usb
    ipAddress: Optional[str] = None
    port: int = 0
    serialPort: Optional[str] = None
    apiKey: Optional[str] = None
    apiSecret: Optional[str] = None
    cloudEndpoint: Optional[str] = None
    timeout: int = 60  # seconds
    autoSettlement: bool = True
    status: str = "active"  # active, inactive, error
    lastPing: Optional[datetime] = None
    metadata: Dict[str, Any] = {}

class EFTPOSConfigCreate(BaseModel):
    provider: str
    terminalId: str
    merchantId: str
    name: str
    location: str
    connectionType: str
    ipAddress: Optional[str] = None
    port: int = 0
    serialPort: Optional[str] = None
    apiKey: Optional[str] = None
    apiSecret: Optional[str] = None
    cloudEndpoint: Optional[str] = None
    timeout: int = 60
    autoSettlement: bool = True

class EFTPOSTransaction(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    terminalId: str
    provider: str
    transactionType: str  # purchase, refund, cash_out, cancel
    amount: float
    cashout: float = 0.0
    reference: str
    posTransactionId: str  # Link to POS transaction
    cardType: Optional[str] = None  # visa, mastercard, eftpos, amex
    maskedPan: Optional[str] = None  # Last 4 digits
    authCode: Optional[str] = None
    rrn: Optional[str] = None  # Retrieval Reference Number
    stan: Optional[str] = None  # System Trace Audit Number
    responseCode: str
    responseText: str
    approved: bool
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    settlementDate: Optional[datetime] = None
    metadata: Dict[str, Any] = {}

class EFTPOSTransactionRequest(BaseModel):
    terminalId: str
    transactionType: str
    amount: float
    cashout: float = 0.0
    reference: str
    posTransactionId: str
