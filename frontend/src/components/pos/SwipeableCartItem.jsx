import React, { useState } from 'react';
import { Minus, Plus } from 'lucide-react';
import { Card, CardContent } from '../ui/card';
import { Button } from '../ui/button';

/**
 * Left-swipe deletes a cart line; right-swipe repeats (+1 quantity).
 * Extracted from POSTerminal for readability and reuse.
 */
export default function SwipeableCartItem({ item, onUpdateQty, onRemove, onRepeat, theme }) {
  const [dragX, setDragX] = useState(0);
  const startXRef = React.useRef(null);
  const isDraggingRef = React.useRef(false);
  const THRESHOLD = 80;

  const onPointerDown = (e) => {
    if (e.target.closest('[data-no-swipe]')) return;
    startXRef.current = e.clientX;
    isDraggingRef.current = true;
    e.currentTarget.setPointerCapture(e.pointerId);
  };
  const onPointerMove = (e) => {
    if (!isDraggingRef.current || startXRef.current === null) return;
    setDragX(e.clientX - startXRef.current);
  };
  const onPointerUp = (e) => {
    if (!isDraggingRef.current) return;
    isDraggingRef.current = false;
    try { e.currentTarget.releasePointerCapture(e.pointerId); } catch {}
    if (dragX <= -THRESHOLD) {
      setDragX(-400);
      setTimeout(() => onRemove(item.id), 180);
    } else if (dragX >= THRESHOLD) {
      onRepeat(item);
      setDragX(0);
    } else {
      setDragX(0);
    }
    startXRef.current = null;
  };

  const bgIntensity = Math.min(Math.abs(dragX) / THRESHOLD, 1);

  return (
    <div className="relative overflow-hidden rounded-lg" data-testid={`cart-item-wrapper-${item.id}`}>
      <div className="absolute inset-y-0 left-0 flex items-center pl-4 text-white font-bold text-xs"
        style={{ backgroundColor: '#10b981', opacity: dragX > 0 ? bgIntensity : 0, width: '100%' }}
        data-testid={`swipe-repeat-bg-${item.id}`}>
        <span>+1 REPEAT →</span>
      </div>
      <div className="absolute inset-y-0 right-0 flex items-center justify-end pr-4 text-white font-bold text-xs"
        style={{ backgroundColor: '#ef4444', opacity: dragX < 0 ? bgIntensity : 0, width: '100%' }}
        data-testid={`swipe-delete-bg-${item.id}`}>
        <span>← DELETE</span>
      </div>
      <Card
        onPointerDown={onPointerDown}
        onPointerMove={onPointerMove}
        onPointerUp={onPointerUp}
        onPointerCancel={onPointerUp}
        style={{ transform: `translateX(${dragX}px)`, transition: isDraggingRef.current ? 'none' : 'transform 0.2s ease-out', touchAction: 'pan-y' }}
        className="relative bg-white cursor-grab active:cursor-grabbing select-none"
        data-testid={`cart-item-${item.id}`}
      >
        <CardContent className="p-3">
          <div className="flex items-center gap-3">
            <img src={item.image || 'https://placehold.co/56x56/e5e7eb/9ca3af?text=NUA'} alt={item.name}
              className="w-14 h-14 object-cover rounded-md flex-shrink-0" draggable={false} />
            <div className="flex-1 min-w-0">
              <p className="font-semibold text-sm truncate">{item.name}</p>
              <p className="text-xs text-gray-500">${item.price.toFixed(2)} each</p>
              {item.selectedModifiers && item.selectedModifiers.length > 0 && (
                <div className="mt-0.5 space-y-0.5" data-testid={`cart-mods-${item.id}`}>
                  {item.selectedModifiers.map((sm, i) => (
                    <p key={i} className="text-[10px] text-gray-600 leading-tight">
                      <span className="text-gray-400">{sm.modifierName}:</span>{' '}
                      {(sm.options || []).map(o => o.name + (o.price > 0 ? ` (+$${o.price.toFixed(2)})` : '')).join(', ')}
                    </p>
                  ))}
                </div>
              )}
            </div>
            <div className="flex items-center gap-1.5" data-no-swipe>
              <Button size="sm" variant="outline" onClick={() => onUpdateQty(item.id, item.quantity - 1)} className="w-7 h-7 p-0" data-testid={`cart-minus-${item.id}`}><Minus size={12} /></Button>
              <span className="font-semibold w-6 text-center text-sm">{item.quantity}</span>
              <Button size="sm" variant="outline" onClick={() => onUpdateQty(item.id, item.quantity + 1)} className="w-7 h-7 p-0" data-testid={`cart-plus-${item.id}`}><Plus size={12} /></Button>
            </div>
          </div>
          <div className="flex items-center justify-between mt-1.5">
            <span className="text-[10px] text-gray-300 italic">← swipe delete · repeat swipe →</span>
            <span className="font-bold" style={{ color: theme.primary }}>${(item.price * item.quantity).toFixed(2)}</span>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
