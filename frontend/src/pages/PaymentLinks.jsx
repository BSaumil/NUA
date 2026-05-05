import React, { useState, useEffect } from 'react';
import { Link2, Plus, Trash2, Copy, ExternalLink } from 'lucide-react';
import { Card, CardContent } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Badge } from '../components/ui/badge';
import { useTheme } from '../contexts/ThemeContext';
import { itemsSystemAPI, productsAPI } from '../services/api';
import { toast } from 'sonner';

export default function PaymentLinks() {
  const { theme } = useTheme();
  const [links, setLinks] = useState([]);
  const [products, setProducts] = useState([]);
  const [selectedProduct, setSelectedProduct] = useState('');
  const [customPrice, setCustomPrice] = useState('');

  useEffect(() => {
    itemsSystemAPI.getPaymentLinks().then(r => setLinks(r.data)).catch(() => {});
    productsAPI.getAll().then(r => setProducts(r.data)).catch(() => {});
  }, []);

  const createLink = async () => {
    const product = products.find(p => p.id === selectedProduct);
    if (!product) { toast.error('Select a product'); return; }
    try {
      const res = await itemsSystemAPI.createPaymentLink({ productId: product.id, productName: product.name, price: parseFloat(customPrice) || product.price });
      setLinks([res.data, ...links]);
      toast.success('Payment link created');
      setSelectedProduct(''); setCustomPrice('');
    } catch { toast.error('Failed'); }
  };

  const copyLink = (url) => { navigator.clipboard.writeText(url); toast.success('Link copied to clipboard'); };

  return (
    <div className="space-y-6" data-testid="payment-links-page">
      <div><h1 className="text-2xl font-bold" style={{ color: theme.text }}>Payment Links</h1><p className="text-sm text-gray-500">Sell items directly via social media, Google, or menu links</p></div>

      <Card><CardContent className="p-4">
        <p className="text-sm font-medium mb-3">Create Payment Link</p>
        <div className="flex gap-2">
          <select className="flex-1 p-2 border rounded-md text-sm" value={selectedProduct} onChange={e => setSelectedProduct(e.target.value)} data-testid="link-product-select">
            <option value="">Select item...</option>
            {products.map(p => <option key={p.id} value={p.id}>{p.name} — ${p.price}</option>)}
          </select>
          <Input type="number" step="0.01" placeholder="Custom price (optional)" className="w-40" value={customPrice} onChange={e => setCustomPrice(e.target.value)} data-testid="link-price" />
          <Button style={{ backgroundColor: theme.primary }} onClick={createLink} data-testid="create-link-btn"><Plus size={16} className="mr-1" /> Generate Link</Button>
        </div>
      </CardContent></Card>

      <div className="space-y-2">
        {links.map(link => (
          <Card key={link.id} data-testid={`link-${link.id}`}>
            <CardContent className="p-4 flex items-center justify-between">
              <div className="flex items-center gap-3">
                <Link2 size={18} style={{ color: theme.primary }} />
                <div>
                  <p className="font-medium text-sm">{link.productName}</p>
                  <p className="text-xs text-gray-500 font-mono">{link.url}</p>
                </div>
              </div>
              <div className="flex items-center gap-2">
                <Badge style={{ backgroundColor: `${theme.primary}15`, color: theme.primary }}>${link.price}</Badge>
                <Button variant="outline" size="sm" onClick={() => copyLink(link.url)} data-testid={`copy-${link.id}`}><Copy size={13} /></Button>
                <Button variant="outline" size="sm" className="text-red-500" onClick={async () => { await itemsSystemAPI.deletePaymentLink(link.id); setLinks(links.filter(l => l.id !== link.id)); }}><Trash2 size={13} /></Button>
              </div>
            </CardContent>
          </Card>
        ))}
        {links.length === 0 && <Card className="border-dashed"><CardContent className="py-12 text-center text-gray-400"><Link2 size={40} className="mx-auto mb-3 opacity-30" /><p>No payment links yet. Create one above.</p></CardContent></Card>}
      </div>
    </div>
  );
}
