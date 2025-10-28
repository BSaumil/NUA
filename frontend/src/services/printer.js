// Printer service for LAN/Network receipt printing
// Uses ESC/POS commands for thermal printers

class PrinterService {
  constructor() {
    this.encoder = new TextEncoder();
  }

  // ESC/POS Commands
  ESC_POS = {
    INIT: '\x1B\x40',                // Initialize printer
    FEED: '\x1B\x64',                 // Paper feed
    CUT: '\x1D\x56\x00',              // Full cut
    ALIGN_LEFT: '\x1B\x61\x00',       // Align left
    ALIGN_CENTER: '\x1B\x61\x01',     // Align center
    ALIGN_RIGHT: '\x1B\x61\x02',      // Align right
    BOLD_ON: '\x1B\x45\x01',          // Bold on
    BOLD_OFF: '\x1B\x45\x00',         // Bold off
    DOUBLE_HEIGHT: '\x1B\x21\x10',    // Double height
    NORMAL_SIZE: '\x1B\x21\x00',      // Normal size
    UNDERLINE_ON: '\x1B\x2D\x01',     // Underline on
    UNDERLINE_OFF: '\x1B\x2D\x00',    // Underline off
  };

  // Format receipt text
  formatReceipt(transaction, businessInfo = {}) {
    let receipt = '';

    // Initialize
    receipt += this.ESC_POS.INIT;

    // Header - Business Info
    receipt += this.ESC_POS.ALIGN_CENTER;
    receipt += this.ESC_POS.BOLD_ON;
    receipt += this.ESC_POS.DOUBLE_HEIGHT;
    receipt += `${businessInfo.name || 'Ananta POS'}\n`;
    receipt += this.ESC_POS.NORMAL_SIZE;
    receipt += this.ESC_POS.BOLD_OFF;
    
    if (businessInfo.address) {
      receipt += `${businessInfo.address}\n`;
    }
    if (businessInfo.phone) {
      receipt += `Tel: ${businessInfo.phone}\n`;
    }
    if (businessInfo.abn) {
      receipt += `ABN: ${businessInfo.abn}\n`;
    }
    
    receipt += '================================\n';

    // Transaction details
    receipt += this.ESC_POS.ALIGN_LEFT;
    receipt += `Receipt: ${transaction.id}\n`;
    receipt += `Date: ${new Date(transaction.timestamp).toLocaleString()}\n`;
    receipt += `Cashier: ${transaction.cashier}\n`;
    if (transaction.customerName) {
      receipt += `Customer: ${transaction.customerName}\n`;
    }
    receipt += `Location: ${transaction.location}\n`;
    receipt += '================================\n\n`;

    // Items
    receipt += this.ESC_POS.BOLD_ON;
    receipt += `Item${' '.repeat(18)}Qty  Price\n`;
    receipt += this.ESC_POS.BOLD_OFF;
    receipt += '--------------------------------\n';

    transaction.items.forEach(item => {
      const name = item.productName.substring(0, 18).padEnd(18);
      const qty = item.quantity.toString().padStart(3);
      const price = `$${(item.price * item.quantity).toFixed(2)}`.padStart(7);
      receipt += `${name}${qty} ${price}\n`;

      // Add modifiers
      if (item.modifiers && item.modifiers.length > 0) {
        item.modifiers.forEach(mod => {
          const modText = `  + ${mod.optionName}`;
          const modPrice = mod.price > 0 ? `+$${mod.price.toFixed(2)}` : '';
          receipt += `${modText.padEnd(26)}${modPrice.padStart(6)}\n`;
        });
      }
    });

    receipt += '--------------------------------\n';

    // Totals
    receipt += `Subtotal:${' '.repeat(16)}$${transaction.subtotal.toFixed(2).padStart(7)}\n`;
    
    if (transaction.discount && transaction.discountAmount > 0) {
      const discountText = transaction.discount.type === 'percentage' 
        ? `Discount (${transaction.discount.value}%)` 
        : 'Discount';
      receipt += `${discountText}:${' '.repeat(20 - discountText.length)}-$${transaction.discountAmount.toFixed(2).padStart(6)}\n`;
    }

    receipt += `GST (10%):${' '.repeat(15)}$${transaction.gst.toFixed(2).padStart(7)}\n`;
    receipt += '================================\n';
    receipt += this.ESC_POS.BOLD_ON;
    receipt += this.ESC_POS.DOUBLE_HEIGHT;
    receipt += `TOTAL:${' '.repeat(13)}$${transaction.total.toFixed(2).padStart(7)}\n`;
    receipt += this.ESC_POS.NORMAL_SIZE;
    receipt += this.ESC_POS.BOLD_OFF;
    receipt += '================================\n\n';

    // Payment method
    receipt += `Payment: ${transaction.paymentMethod}\n\n`;

    // Footer
    receipt += this.ESC_POS.ALIGN_CENTER;
    receipt += 'Thank you for your business!\n';
    receipt += 'Please come again\n\n';
    
    if (businessInfo.website) {
      receipt += `${businessInfo.website}\n`;
    }

    // Feed and cut
    receipt += this.ESC_POS.FEED + '\x03'; // Feed 3 lines
    receipt += this.ESC_POS.CUT;

    return receipt;
  }

  // Print to network printer
  async printToNetwork(printerConfig, transaction) {
    try {
      const receiptText = this.formatReceipt(transaction);
      const encoded = this.encoder.encode(receiptText);

      // Send to printer via network
      const response = await fetch(`http://${printerConfig.ipAddress}:${printerConfig.port}`, {
        method: 'POST',
        body: encoded,
        headers: {
          'Content-Type': 'application/octet-stream',
        },
      });

      if (response.ok) {
        console.log('✅ Receipt printed successfully');
        return true;
      } else {
        throw new Error('Printer communication failed');
      }
    } catch (error) {
      console.error('Error printing receipt:', error);
      // Fallback to browser print
      this.printBrowser(transaction);
      return false;
    }
  }

  // Fallback browser print
  printBrowser(transaction) {
    const printWindow = window.open('', '_blank');
    const html = this.generateHTMLReceipt(transaction);
    
    printWindow.document.write(html);
    printWindow.document.close();
    printWindow.focus();
    
    setTimeout(() => {
      printWindow.print();
      printWindow.close();
    }, 250);
  }

  // Generate HTML receipt for browser printing
  generateHTMLReceipt(transaction) {
    return `
      <!DOCTYPE html>
      <html>
      <head>
        <title>Receipt - ${transaction.id}</title>
        <style>
          body {
            font-family: 'Courier New', monospace;
            width: 80mm;
            margin: 0 auto;
            padding: 10mm;
            font-size: 12px;
          }
          .center { text-align: center; }
          .bold { font-weight: bold; }
          .large { font-size: 18px; }
          table { width: 100%; border-collapse: collapse; }
          td { padding: 2px 0; }
          .separator { border-top: 1px dashed #000; margin: 5px 0; }
          .total { font-size: 16px; font-weight: bold; }
        </style>
      </head>
      <body>
        <div class="center bold large">Ananta POS</div>
        <div class="center">123 Main St, Sydney NSW 2000</div>
        <div class="center">Tel: +61 2 9876 5432</div>
        <div class="separator"></div>
        <table>
          <tr><td>Receipt:</td><td class="bold">${transaction.id}</td></tr>
          <tr><td>Date:</td><td>${new Date(transaction.timestamp).toLocaleString()}</td></tr>
          <tr><td>Cashier:</td><td>${transaction.cashier}</td></tr>
          ${transaction.customerName ? `<tr><td>Customer:</td><td>${transaction.customerName}</td></tr>` : ''}
        </table>
        <div class="separator"></div>
        <table>
          ${transaction.items.map(item => `
            <tr>
              <td>${item.productName}</td>
              <td style="text-align: right">${item.quantity} x $${item.price.toFixed(2)}</td>
            </tr>
            ${item.modifiers && item.modifiers.length > 0 ? item.modifiers.map(mod => `
              <tr>
                <td style="padding-left: 10px">+ ${mod.optionName}</td>
                <td style="text-align: right">${mod.price > 0 ? `+$${mod.price.toFixed(2)}` : ''}</td>
              </tr>
            `).join('') : ''}
          `).join('')}
        </table>
        <div class="separator"></div>
        <table>
          <tr><td>Subtotal:</td><td style="text-align: right">$${transaction.subtotal.toFixed(2)}</td></tr>
          ${transaction.discount && transaction.discountAmount > 0 ? `
            <tr><td>Discount:</td><td style="text-align: right">-$${transaction.discountAmount.toFixed(2)}</td></tr>
          ` : ''}
          <tr><td>GST (10%):</td><td style="text-align: right">$${transaction.gst.toFixed(2)}</td></tr>
          <tr class="total"><td>TOTAL:</td><td style="text-align: right">$${transaction.total.toFixed(2)}</td></tr>
        </table>
        <div class="separator"></div>
        <div>Payment: ${transaction.paymentMethod}</div>
        <div class="separator"></div>
        <div class="center">Thank you for your business!</div>
        <div class="center">Please come again</div>
      </body>
      </html>
    `;
  }
}

export default new PrinterService();
