import React, { useState, useEffect } from 'react';
import { Award, Gift, Star, Crown, Shield, Ticket, Plus, Edit, Trash2, Users, Calendar, Save } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Badge } from '../components/ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../components/ui/tabs';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '../components/ui/dialog';
import { useTheme } from '../contexts/ThemeContext';
import { loyaltyAPI, eventsAPI } from '../services/api';
import { toast } from 'sonner';

const TIER_COLORS = { Bronze: '#B45309', Silver: '#6B7280', Gold: '#F59E0B', Platinum: '#818CF8' };

export default function LoyaltyEvents() {
  const { theme } = useTheme();
  const [tab, setTab] = useState('tiers');
  const [tiers, setTiers] = useState([]);
  const [rewards, setRewards] = useState([]);
  const [events, setEvents] = useState([]);
  const [editingTier, setEditingTier] = useState(null);
  const [showRewardDialog, setShowRewardDialog] = useState(false);
  const [editingReward, setEditingReward] = useState(null);
  const [rewardForm, setRewardForm] = useState({ name: '', description: '', pointsCost: 100, rewardType: 'discount', discountAmount: 10, startDate: '', startTime: '', endDate: '', endTime: '' });
  const [showEventDialog, setShowEventDialog] = useState(false);
  const [editingEvent, setEditingEvent] = useState(null);
  const [eventForm, setEventForm] = useState({ name: '', description: '', date: '', time: '19:00', duration: 120, capacity: 50, ticketPrice: 0, eventType: 'dining' });

  useEffect(() => { fetchAll(); }, []);
  const fetchAll = () => {
    loyaltyAPI.getTiers().then(r => setTiers(r.data)).catch(() => {});
    loyaltyAPI.getRewards().then(r => setRewards(r.data)).catch(() => {});
    eventsAPI.getAll().then(r => setEvents(r.data)).catch(() => {});
  };

  // TIER EDIT
  const saveTier = async (tier) => {
    try { await loyaltyAPI.updateTier(tier.id, tier); toast.success('Tier updated'); setEditingTier(null); fetchAll(); } catch { toast.error('Failed'); }
  };

  // REWARD CRUD
  const openAddReward = () => { setEditingReward(null); setRewardForm({ name: '', description: '', pointsCost: 100, rewardType: 'discount', discountAmount: 10, startDate: '', startTime: '', endDate: '', endTime: '' }); setShowRewardDialog(true); };
  const openEditReward = (r) => { setEditingReward(r); setRewardForm({ name: r.name, description: r.description || '', pointsCost: r.pointsCost, rewardType: r.rewardType, discountAmount: r.discountAmount || 10, startDate: r.startDate || '', startTime: r.startTime || '', endDate: r.endDate || '', endTime: r.endTime || '' }); setShowRewardDialog(true); };
  const saveReward = async () => {
    if (!rewardForm.name) { toast.error('Name required'); return; }
    try {
      if (editingReward) { await loyaltyAPI.updateReward(editingReward.id, rewardForm); toast.success('Reward updated'); }
      else { await loyaltyAPI.createReward(rewardForm); toast.success('Reward created'); }
      setShowRewardDialog(false); fetchAll();
    } catch { toast.error('Failed'); }
  };
  const deleteReward = async (id) => { try { await loyaltyAPI.deleteReward(id); fetchAll(); } catch {} };

  // EVENT CRUD
  const openAddEvent = () => { setEditingEvent(null); setEventForm({ name: '', description: '', date: '', time: '19:00', duration: 120, capacity: 50, ticketPrice: 0, eventType: 'dining' }); setShowEventDialog(true); };
  const openEditEvent = (e) => { setEditingEvent(e); setEventForm({ name: e.name, description: e.description || '', date: e.date, time: e.time || '19:00', duration: e.duration || 120, capacity: e.capacity, ticketPrice: e.ticketPrice, eventType: e.eventType }); setShowEventDialog(true); };
  const saveEvent = async () => {
    if (!eventForm.name || !eventForm.date) { toast.error('Name and date required'); return; }
    try {
      if (editingEvent) { await eventsAPI.update(editingEvent.id, eventForm); toast.success('Event updated'); }
      else { await eventsAPI.create(eventForm); toast.success('Event created'); }
      setShowEventDialog(false); fetchAll();
    } catch { toast.error('Failed'); }
  };

  return (
    <div className="space-y-6" data-testid="loyalty-events-page">
      <div className="flex items-center gap-3">
        <div className="w-12 h-12 rounded-xl flex items-center justify-center" style={{ background: 'linear-gradient(135deg, #F59E0B, #EF4444)' }}><Award size={24} className="text-white" /></div>
        <div><h1 className="text-2xl font-bold" style={{ color: theme.text }}>Loyalty & Events</h1><p className="text-sm text-gray-500">Editable membership tiers, rewards & experiences</p></div>
      </div>

      <Tabs value={tab} onValueChange={setTab}>
        <TabsList><TabsTrigger value="tiers">Membership Tiers</TabsTrigger><TabsTrigger value="rewards">Rewards</TabsTrigger><TabsTrigger value="events">Events & Experiences</TabsTrigger></TabsList>

        {/* TIERS — Editable */}
        <TabsContent value="tiers" className="mt-4">
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
            {tiers.map((tier) => {
              const color = TIER_COLORS[tier.name] || theme.primary;
              const isEditing = editingTier?.id === tier.id;
              return (
                <Card key={tier.id || tier.name} className="border-0 shadow-sm overflow-hidden" data-testid={`tier-${tier.name?.toLowerCase()}`}>
                  <div className="h-2" style={{ background: color }} />
                  <CardContent className="p-4">
                    {isEditing ? (
                      <div className="space-y-2">
                        <Input className="h-8 text-sm font-bold" value={editingTier.name} onChange={e => setEditingTier({ ...editingTier, name: e.target.value })} />
                        <Input type="number" className="h-8 text-sm" placeholder="Min Points" value={editingTier.minPoints} onChange={e => setEditingTier({ ...editingTier, minPoints: parseInt(e.target.value) || 0 })} />
                        <Input type="number" step="0.1" className="h-8 text-sm" placeholder="Multiplier" value={editingTier.multiplier} onChange={e => setEditingTier({ ...editingTier, multiplier: parseFloat(e.target.value) || 1 })} />
                        <textarea className="w-full p-2 text-xs border rounded" placeholder="Perks (one per line)" value={(editingTier.perks || []).join('\n')} onChange={e => setEditingTier({ ...editingTier, perks: e.target.value.split('\n').filter(Boolean) })} rows={4} />
                        <div className="flex gap-2"><Button size="sm" style={{ backgroundColor: theme.primary }} onClick={() => saveTier(editingTier)} data-testid={`save-tier-${tier.id}`}><Save size={12} className="mr-1" /> Save</Button><Button size="sm" variant="outline" onClick={() => setEditingTier(null)}>Cancel</Button></div>
                      </div>
                    ) : (
                      <>
                        <div className="flex items-center justify-between mb-2">
                          <h3 className="font-bold" style={{ color }}>{tier.name}</h3>
                          <Button variant="ghost" size="sm" className="h-6 w-6 p-0" onClick={() => setEditingTier({ ...tier })} data-testid={`edit-tier-${tier.id}`}><Edit size={12} /></Button>
                        </div>
                        <p className="text-xs text-gray-500 mb-1">{tier.minPoints}+ pts | {tier.multiplier}x multiplier</p>
                        <div className="space-y-1">{(tier.perks || []).map((p, i) => <p key={i} className="text-xs text-gray-600 flex items-center gap-1"><span className="w-1.5 h-1.5 rounded-full" style={{ background: color }} />{p}</p>)}</div>
                      </>
                    )}
                  </CardContent>
                </Card>
              );
            })}
          </div>
        </TabsContent>

        {/* REWARDS — Full CRUD with dates */}
        <TabsContent value="rewards" className="mt-4 space-y-4">
          <div className="flex justify-end"><Button onClick={openAddReward} style={{ background: theme.primary }} data-testid="create-reward-btn"><Plus size={16} className="mr-1" /> New Reward</Button></div>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {rewards.map(r => (
              <Card key={r.id} className="border-0 shadow-sm" data-testid={`reward-${r.id}`}>
                <CardContent className="p-5">
                  <div className="flex items-start justify-between"><div className="flex items-center gap-2"><Gift size={18} style={{ color: theme.primary }} /><h3 className="font-semibold">{r.name}</h3></div>
                    <div className="flex gap-1"><Button variant="ghost" size="sm" className="h-6 px-1" onClick={() => openEditReward(r)}><Edit size={12} /></Button><Button variant="ghost" size="sm" className="h-6 px-1 text-red-400" onClick={() => deleteReward(r.id)}><Trash2 size={12} /></Button></div>
                  </div>
                  {r.description && <p className="text-xs text-gray-500 mt-1">{r.description}</p>}
                  <div className="flex items-center gap-2 mt-3"><Badge style={{ background: `${theme.primary}15`, color: theme.primary }}>{r.pointsCost} pts</Badge><Badge variant="outline" className="text-[10px] capitalize">{r.rewardType?.replace('_', ' ')}</Badge></div>
                  {(r.startDate || r.endDate) && <p className="text-[10px] text-gray-400 mt-2">{r.startDate} {r.startTime} → {r.endDate} {r.endTime}</p>}
                </CardContent>
              </Card>
            ))}
            {rewards.length === 0 && <Card className="col-span-3 border-dashed"><CardContent className="py-12 text-center text-gray-400"><Gift size={40} className="mx-auto mb-3 opacity-30" /><p>No rewards yet</p></CardContent></Card>}
          </div>
        </TabsContent>

        {/* EVENTS — Full CRUD */}
        <TabsContent value="events" className="mt-4 space-y-4">
          <div className="flex justify-end"><Button onClick={openAddEvent} style={{ background: theme.primary }} data-testid="create-event-btn"><Plus size={16} className="mr-1" /> New Event</Button></div>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {events.map(evt => (
              <Card key={evt.id} className="border-0 shadow-sm overflow-hidden" data-testid={`event-${evt.id}`}>
                <div className="h-1.5" style={{ background: theme.primary }} />
                <CardContent className="p-5">
                  <div className="flex items-start justify-between mb-2">
                    <h3 className="font-bold text-lg">{evt.name}</h3>
                    <div className="flex gap-1"><Button variant="ghost" size="sm" className="h-6 px-1" onClick={() => openEditEvent(evt)} data-testid={`edit-event-${evt.id}`}><Edit size={12} /></Button></div>
                  </div>
                  {evt.description && <p className="text-sm text-gray-500 mb-3">{evt.description}</p>}
                  <div className="grid grid-cols-3 gap-3 text-center py-2 border-t border-b text-sm">
                    <div><Calendar size={14} className="mx-auto text-gray-400 mb-1" /><p className="font-medium text-xs">{evt.date}</p><p className="text-[10px] text-gray-500">{evt.time}</p></div>
                    <div><Users size={14} className="mx-auto text-gray-400 mb-1" /><p className="font-medium text-xs">{evt.ticketsBooked || 0}/{evt.capacity}</p></div>
                    <div><Ticket size={14} className="mx-auto text-gray-400 mb-1" /><p className="font-medium text-xs">${evt.ticketPrice}</p></div>
                  </div>
                </CardContent>
              </Card>
            ))}
            {events.length === 0 && <Card className="col-span-2 border-dashed"><CardContent className="py-12 text-center text-gray-400"><Ticket size={40} className="mx-auto mb-3 opacity-30" /><p>No events</p></CardContent></Card>}
          </div>
        </TabsContent>
      </Tabs>

      {/* Reward Dialog */}
      <Dialog open={showRewardDialog} onOpenChange={setShowRewardDialog}>
        <DialogContent className="max-w-sm" data-testid="reward-dialog">
          <DialogHeader><DialogTitle>{editingReward ? 'Edit Reward' : 'New Reward'}</DialogTitle></DialogHeader>
          <div className="space-y-3 py-2">
            <Input placeholder="Reward name" value={rewardForm.name} onChange={e => setRewardForm({ ...rewardForm, name: e.target.value })} data-testid="reward-name" />
            <Input placeholder="Description" value={rewardForm.description} onChange={e => setRewardForm({ ...rewardForm, description: e.target.value })} />
            <div className="grid grid-cols-2 gap-2">
              <Input type="number" placeholder="Points cost" value={rewardForm.pointsCost} onChange={e => setRewardForm({ ...rewardForm, pointsCost: parseInt(e.target.value) || 0 })} />
              <select className="p-2 border rounded-md text-sm" value={rewardForm.rewardType} onChange={e => setRewardForm({ ...rewardForm, rewardType: e.target.value })}>
                <option value="discount">Discount</option><option value="free_item">Free Item</option><option value="experience">Experience</option>
              </select>
            </div>
            <div className="grid grid-cols-2 gap-2">
              <div><label className="text-xs text-gray-500">Start Date</label><Input type="date" value={rewardForm.startDate} onChange={e => setRewardForm({ ...rewardForm, startDate: e.target.value })} data-testid="reward-start-date" /></div>
              <div><label className="text-xs text-gray-500">Start Time</label><Input type="time" value={rewardForm.startTime} onChange={e => setRewardForm({ ...rewardForm, startTime: e.target.value })} /></div>
              <div><label className="text-xs text-gray-500">End Date</label><Input type="date" value={rewardForm.endDate} onChange={e => setRewardForm({ ...rewardForm, endDate: e.target.value })} data-testid="reward-end-date" /></div>
              <div><label className="text-xs text-gray-500">End Time</label><Input type="time" value={rewardForm.endTime} onChange={e => setRewardForm({ ...rewardForm, endTime: e.target.value })} /></div>
            </div>
            <Button className="w-full" style={{ backgroundColor: theme.primary }} onClick={saveReward} data-testid="save-reward-btn">{editingReward ? 'Update' : 'Create'} Reward</Button>
          </div>
        </DialogContent>
      </Dialog>

      {/* Event Dialog */}
      <Dialog open={showEventDialog} onOpenChange={setShowEventDialog}>
        <DialogContent className="max-w-md" data-testid="event-dialog">
          <DialogHeader><DialogTitle>{editingEvent ? 'Edit Event' : 'New Event'}</DialogTitle></DialogHeader>
          <div className="space-y-3 py-2">
            <Input placeholder="Event name" value={eventForm.name} onChange={e => setEventForm({ ...eventForm, name: e.target.value })} data-testid="event-name" />
            <textarea className="w-full min-h-[50px] p-2 border rounded-md text-sm" placeholder="Description" value={eventForm.description} onChange={e => setEventForm({ ...eventForm, description: e.target.value })} />
            <div className="grid grid-cols-2 gap-2">
              <Input type="date" value={eventForm.date} onChange={e => setEventForm({ ...eventForm, date: e.target.value })} data-testid="event-date" />
              <Input type="time" value={eventForm.time} onChange={e => setEventForm({ ...eventForm, time: e.target.value })} />
              <Input type="number" placeholder="Capacity" value={eventForm.capacity} onChange={e => setEventForm({ ...eventForm, capacity: parseInt(e.target.value) || 0 })} />
              <Input type="number" step="0.01" placeholder="Ticket price" value={eventForm.ticketPrice} onChange={e => setEventForm({ ...eventForm, ticketPrice: parseFloat(e.target.value) || 0 })} />
            </div>
            <select className="w-full p-2 border rounded-md text-sm" value={eventForm.eventType} onChange={e => setEventForm({ ...eventForm, eventType: e.target.value })}>
              <option value="dining">Special Dining</option><option value="wine_pairing">Wine Pairing</option><option value="cooking_class">Cooking Class</option><option value="live_music">Live Music</option><option value="private">Private Event</option>
            </select>
            <Button className="w-full" style={{ backgroundColor: theme.primary }} onClick={saveEvent} data-testid="save-event-btn">{editingEvent ? 'Update' : 'Create'} Event</Button>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
}
