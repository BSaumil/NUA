// Station docket printing (80mm thermal / browser print).
// Separate from services/printer.js, which formats the CUSTOMER receipt —
// a station docket is a kitchen-facing production ticket.

// "Bar Printer" -> "BAR", "Pizza Station" -> "PIZZA", "Kitchen Printer" -> "KITCHEN"
export function stationLabel(printerName) {
  return String(printerName || '')
    .replace(/\s*(printer|station)\s*$/i, '')
    .trim()
    .toUpperCase() || 'KITCHEN';
}

// Every docket lists ALL sections the order fires from (bottom-left), with
// this docket's own section highlighted — so the pizza station can see the
// coffee is coming from the bar, and the server knows where to collect from.
export function generateDocketHTML(job) {
  const own = stationLabel(job.printer);
  const stations = (job.orderStations && job.orderStations.length > 0
    ? job.orderStations : [job.printer]).map(stationLabel);
  const time = job.createdAt ? new Date(job.createdAt).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) : '';

  const itemsRows = (job.items || []).map(item => `
      <tr>
        <td class="qty">${item.quantity || 1}×</td>
        <td class="name">${item.productName || item.name || ''}</td>
      </tr>
      ${item.notes ? `<tr><td></td><td class="note">» ${item.notes}</td></tr>` : ''}
  `).join('');

  const stationChips = stations.map(s =>
    `<span class="chip${s === own ? ' own' : ''}">${s}</span>`
  ).join('');

  return `
    <!DOCTYPE html>
    <html>
    <head>
      <title>Docket ${job.orderId || job.id}</title>
      <style>
        body { font-family: 'Courier New', monospace; width: 80mm; margin: 0 auto; padding: 4mm; font-size: 13px; color: #000; }
        .station { text-align: center; font-size: 22px; font-weight: bold; letter-spacing: 2px; border: 2px solid #000; padding: 4px 0; }
        .meta { display: flex; justify-content: space-between; margin: 6px 0 2px; font-size: 12px; }
        .prio { font-weight: bold; }
        .sep { border-top: 1px dashed #000; margin: 5px 0; }
        table { width: 100%; border-collapse: collapse; }
        td { padding: 3px 0; vertical-align: top; }
        .qty { width: 34px; font-weight: bold; font-size: 15px; }
        .name { font-size: 15px; font-weight: bold; }
        .note { font-size: 11px; font-style: italic; }
        /* Bottom-left sections strip: every section this order fires from */
        .sections { margin-top: 10px; text-align: left; }
        .sections .label { font-size: 10px; letter-spacing: 1px; }
        .chip { display: inline-block; border: 1px solid #000; padding: 1px 6px; margin: 2px 3px 0 0; font-size: 11px; font-weight: bold; }
        .chip.own { background: #000; color: #fff; }
      </style>
    </head>
    <body>
      <div class="station">${own}</div>
      <div class="meta">
        <span>${job.tableNumber ? `TABLE ${job.tableNumber}` : (job.orderId || '')}</span>
        <span class="prio">P${job.priority || 2}${time ? ` · ${time}` : ''}</span>
      </div>
      ${job.tableNumber && job.orderId ? `<div class="meta"><span>${job.orderId}</span></div>` : ''}
      <div class="sep"></div>
      <table>${itemsRows}</table>
      <div class="sep"></div>
      <div class="sections">
        <div class="label">ORDER SECTIONS:</div>
        ${stationChips}
      </div>
    </body>
    </html>
  `;
}

export function printDocket(job) {
  const w = window.open('', '_blank');
  if (!w) return;
  w.document.write(generateDocketHTML(job));
  w.document.close();
  w.focus();
  setTimeout(() => { w.print(); w.close(); }, 250);
}
