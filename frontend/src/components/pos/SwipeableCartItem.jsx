import React, { useState, useRef } from 'react';
import { Minus, Plus } from 'lucide-react';
import { Card, CardContent } from '../ui/card';
import { Button } from '../ui/button';

/**
 * Left-swipe deletes a cart line; right-swipe repeats (+1 quantity).
 * Uses BOTH pointer events (desktop / most modern browsers) AND explicit
 * touch events (older tablet browsers / iPadOS Safari where setPointerCapture
 * is flaky) so the swipe works everywhere a POS runs.
 */
export default function SwipeableCartItem({ item, onUpdateQty, onRemove, onRepeat, theme }) {
  const [dragX, setDragX] = useState(0);
  const startXRef = useRef(null);
  const startYRef = useRef(null);
  const isDraggingRef = useRef(false);
  const axisRef = useRef(null); // 'x' | 'y' | null — locked after ~6px of movement
  const THRESHOLD = 80;

  const beginDrag = (clientX, clientY) => {
    startXRef.current = clientX;
    startYRef.current = clientY;
    isDraggingRef.current = true;
    axisRef.current = null;
    setDragX(0);
  };
  const moveDrag = (clientX, clientY, evt) => {
    if (!isDraggingRef.current || startXRef.current === null) return;
    const dx = clientX - startXRef.current;
    const dy = clientY - startYRef.current;
    // Axis lock — decide once movement is meaningful.
    if (axisRef.current === null) {
      const ax = Math.abs(dx), ay = Math.abs(dy);
      if (ax < 6 && ay < 6) return;
      axisRef.current = ax > ay ? 'x' : 'y';
    }
    if (axisRef.current !== 'x') return; // vertical scroll — let the page have it
    // Block native scroll only while we're horizontally dragging.
    if (evt && evt.cancelable) { try { evt.preventDefault(); } catch { /* ignore */ } }
    setDragX(dx);
  };
  const endDrag = () => {
    if (!isDraggingRef.current) return;
    isDraggingRef.current = false;
    const finalX = dragX;
    axisRef.current = null;
    startXRef.current = null;
    startYRef.current = null;
    if (finalX <= -THRESHOLD) {
      setDragX(-400);
      setTimeout(() => onRemove(item.id), 180);
    } else if (finalX >= THRESHOLD) {
      onRepeat(item);
      setDragX(0);
    } else {
      setDragX(0);
    }
  };

  // Pointer handlers (desktop mouse + modern touch)
  const onPointerDown = (e) => {
    if (e.target.closest('[data-no-swipe]')) return;
    beginDrag(e.clientX, e.clientY);
    try { e.currentTarget.setPointerCapture(e.pointerId); } catch { /* ignore */ }
  };
  const onPointerMove = (e) => moveDrag(e.clientX, e.clientY, e);
  const onPointerUp = (e) => {
    try { e.currentTarget.releasePointerCapture(e.pointerId); } catch { /* ignore */ }
    endDrag();
  };

  // Touch fallback — some tablet browsers (iPadOS Safari, older Android WebView,
  // some POS terminal browsers) don't reliably fire pointer events for touch.
  const onTouchStart = (e) => {
    if (e.target.closest('[data-no-swipe]')) return;
    const t = e.touches[0]; if (!t) return;
    beginDrag(t.clientX, t.clientY);
  };
  const onTouchMove = (e) => {
    const t = e.touches[0]; if (!t) return;
    moveDrag(t.clientX, t.clientY, e);
  };
  const onTouchEnd = () => endDrag();

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
        onTouchStart={onTouchStart}
        onTouchMove={onTouchMove}
        onTouchEnd={onTouchEnd}
        onTouchCancel={onTouchEnd}
        style={{
          transform: `translateX(${dragX}px)`,
          transition: isDraggingRef.current ? 'none' : 'transform 0.2s ease-out',
          touchAction: 'pan-y',
          userSelect: 'none',
        }}
        className="relative bg-white cursor-grab active:cursor-grabbing select-none"
        data-testid={`cart-item-${item.id}`}
      >
        <CardContent className="p-3">
          <div className="flex items-center gap-3">
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
