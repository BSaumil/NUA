// Shared browser-print receipt builder — Dashboard.jsx and Accounting.jsx
// each used to hand-roll their own near-identical version of this HTML
// string. They'd already drifted once: the split-payment breakdown got
// added to both files' on-screen JSX preview by hand, but never to this
// separately-built print string, so "Print" produced a receipt missing the
// split detail the screen right next to it was showing. One builder, used
// by both the preview and the print popup, means that can't happen again.

function esc(value) {
  return String(value ?? '').replace(/[&<>"']/g, (c) => ({
    '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;',
  }[c]));
}

export function buildReceiptHtml(txn) {
  const items = (txn.items || []).map(i =>
    `<div class="row"><span>${esc(i.productName)} x${i.quantity}</span><span>$${((i.price || 0) * (i.quantity || 0)).toFixed(2)}</span></div>`
  ).join('');

  const splitDetails = txn.splitDetails || [];
  const splitSection = splitDetails.length > 0 ? `
    <hr/>
    <p style="font-weight:bold;text-transform:uppercase;font-size:11px;margin:4px 0">Split payment</p>
    ${splitDetails.map(s => `
      <div class="row"><span>${esc(s.payerName)} (${esc(s.method)})</span><span>$${(s.amount || 0).toFixed(2)}</span></div>
      ${(s.items || []).length > 0
        ? `<p style="color:#888;font-size:11px;padding-left:8px;margin:2px 0">${s.items.map(it => `${it.quantity}× ${esc(it.name)}`).join(' · ')}</p>`
        : ''}
    `).join('')}
  ` : '';

  return `<html><head><title>Receipt</title><style>
    body{font-family:monospace;max-width:320px;margin:20px auto;font-size:12px}
    h2{text-align:center;margin:0}
    hr{border:1px dashed #ccc}
    .row{display:flex;justify-content:space-between}
    .total{font-weight:bold;font-size:14px}
  </style></head><body>
    <h2>NUA</h2>
    <p style="text-align:center">Receipt #${esc(txn.receiptNumber || txn.id)}</p>
    <hr/>
    <p>Date: ${new Date(txn.timestamp).toLocaleString()}</p>
    <p>Cashier: ${esc(txn.cashier || 'Staff')}</p>
    <hr/>
    ${items}
    <hr/>
    <div class="row"><span>Subtotal</span><span>$${(txn.subtotal || 0).toFixed(2)}</span></div>
    ${(txn.discountAmount || txn.discount)
      ? `<div class="row"><span>Discount</span><span>-$${(txn.discountAmount || txn.discount).toFixed(2)}</span></div>`
      : ''}
    <div class="row"><span>GST</span><span>$${(txn.gst || 0).toFixed(2)}</span></div>
    <div class="row total"><span>TOTAL</span><span>$${(txn.total || 0).toFixed(2)}</span></div>
    ${splitSection}
    <hr/>
    <p style="text-align:center">Payment: ${esc(txn.paymentMethod)}</p>
    <p style="text-align:center;margin-top:20px">Thank you!</p>
  </body></html>`;
}
