import React from 'react';
import { Button } from '../ui/button';
import { Input } from '../ui/input';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '../ui/dialog';

/**
 * Create / edit a promotion. Pure presentational — all state lives in the
 * parent (Products.jsx).
 */
export const PromotionDialog = ({
  open, onClose,
  theme,
  editingPromo,
  promoForm, setPromoForm,
  onSave,
}) => (
  <Dialog open={open} onOpenChange={(o) => { if (!o) onClose(); }}>
    <DialogContent className="max-w-md" data-testid="promo-dialog">
      <DialogHeader>
        <DialogTitle>{editingPromo ? 'Edit Promotion' : 'Create Promotion'}</DialogTitle>
      </DialogHeader>
      <div className="space-y-3 py-2 max-h-[65vh] overflow-y-auto">
        <Input
          placeholder="Promotion name"
          value={promoForm.name}
          onChange={e => setPromoForm({ ...promoForm, name: e.target.value })}
          data-testid="promo-name-input"
        />
        <select
          className="w-full p-2 border rounded-md text-sm"
          value={promoForm.type}
          onChange={e => setPromoForm({ ...promoForm, type: e.target.value })}
        >
          <option value="category">Category Discount</option>
          <option value="bundle">Bundle Deal</option>
        </select>
        <Input
          type="number" step="0.1"
          placeholder="Discount %"
          value={promoForm.discount}
          onChange={e => setPromoForm({ ...promoForm, discount: e.target.value })}
          data-testid="promo-discount-input"
        />

        <div>
          <label className="text-xs font-medium text-gray-500 mb-1 block">
            Date Range (optional — leave blank for always)
          </label>
          <div className="grid grid-cols-2 gap-2">
            <Input type="date" value={promoForm.startDate}
              onChange={e => setPromoForm({ ...promoForm, startDate: e.target.value })}
              data-testid="promo-start-date" />
            <Input type="date" value={promoForm.endDate}
              onChange={e => setPromoForm({ ...promoForm, endDate: e.target.value })}
              data-testid="promo-end-date" />
          </div>
        </div>

        <div>
          <label className="text-xs font-medium text-gray-500 mb-1 block">
            Active Days (select none for everyday)
          </label>
          <div className="flex flex-wrap gap-1.5">
            {['Monday','Tuesday','Wednesday','Thursday','Friday','Saturday','Sunday'].map(day => {
              const on = promoForm.activeDays.includes(day);
              return (
                <button
                  key={day} type="button"
                  onClick={() => setPromoForm({
                    ...promoForm,
                    activeDays: on ? promoForm.activeDays.filter(d => d !== day) : [...promoForm.activeDays, day],
                  })}
                  className={`px-2.5 py-1 text-xs rounded-full font-medium transition-colors ${on ? 'bg-gray-900 text-white' : 'bg-gray-100 text-gray-600 hover:bg-gray-200'}`}
                  data-testid={`promo-day-${day.toLowerCase()}`}
                >{day.slice(0, 3)}</button>
              );
            })}
          </div>
        </div>

        <div>
          <label className="text-xs font-medium text-gray-500 mb-1 block">
            Time Window (optional)
          </label>
          <div className="grid grid-cols-2 gap-2">
            <Input type="time" value={promoForm.startTime}
              onChange={e => setPromoForm({ ...promoForm, startTime: e.target.value })}
              data-testid="promo-start-time" />
            <Input type="time" value={promoForm.endTime}
              onChange={e => setPromoForm({ ...promoForm, endTime: e.target.value })}
              data-testid="promo-end-time" />
          </div>
        </div>

        <Input
          placeholder="Schedule note (e.g. Happy Hour)"
          value={promoForm.schedule}
          onChange={e => setPromoForm({ ...promoForm, schedule: e.target.value })}
          data-testid="promo-schedule-input"
        />
        <label className="flex items-center gap-2 text-sm">
          <input
            type="checkbox"
            checked={promoForm.active}
            onChange={e => setPromoForm({ ...promoForm, active: e.target.checked })}
          /> Active
        </label>
        <Button
          className="w-full" style={{ backgroundColor: theme.primary }}
          onClick={onSave} data-testid="save-promo-btn"
        >
          {editingPromo ? 'Update Promotion' : 'Create Promotion'}
        </Button>
      </div>
    </DialogContent>
  </Dialog>
);
