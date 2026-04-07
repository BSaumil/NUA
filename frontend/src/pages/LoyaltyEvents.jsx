import React, { useState, useEffect } from 'react';
import {
  Award, Gift, Star, Crown, Shield, Ticket, Plus, Trash2,
  Users, TrendingUp, Calendar, ChevronRight
} from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Badge } from '../components/ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../components/ui/tabs';
import {
  Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter
} from '../components/ui/dialog';
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue
} from '../components/ui/select';
import { useTheme } from '../contexts/ThemeContext';
import { loyaltyAPI, eventsAPI } from '../services/api';
import { toast } from 'sonner';

const TIER_COLORS = {
  Bronze: { color: '#B45309', bg: '#FEF3C7', icon: Shield },
  Silver: { color: '#6B7280', bg: '#F3F4F6', icon: Star },
  Gold: { color: '#F59E0B', bg: '#FFFBEB', icon: Crown },
  Platinum: { color: '#818CF8', bg: '#EEF2FF', icon: Crown },
};

const EVENT_TYPE_COLORS = {
  dining: '#10B981', wine_pairing: '#8B5CF6', cooking_class: '#F59E0B',
  live_music: '#EC4899', private: '#6366F1',
};

export default function LoyaltyEvents() {
  const { theme } = useTheme();
  const [tab, setTab] = useState('tiers');
  const [tiers, setTiers] = useState([]);
  const [rewards, setRewards] = useState([]);
  const [events, setEvents] = useState([]);
  const [rewardDialog, setRewardDialog] = useState(false);
  const [eventDialog, setEventDialog] = useState(false);
  const [rewardForm, setRewardForm] = useState({ name: '', description: '', pointsCost: 100, rewardType: 'discount', discountAmount: 10 });
  const [eventForm, setEventForm] = useState({ name: '', description: '', date: '', time: '19:00', duration: 120, capacity: 50, ticketPrice: 0, eventType: 'dining' });

  useEffect(() => {
    loyaltyAPI.getTiers().then(r => setTiers(r.data)).catch(console.error);
    loyaltyAPI.getRewards().then(r => setRewards(r.data)).catch(console.error);
    eventsAPI.getAll().then(r => setEvents(r.data)).catch(console.error);
  }, []);

  const handleCreateReward = async () => {
    if (!rewardForm.name) { toast.error('Name required'); return; }
    try {
      await loyaltyAPI.createReward(rewardForm);
      toast.success('Reward created');
      setRewardDialog(false);
      loyaltyAPI.getRewards().then(r => setRewards(r.data));
    } catch (e) { toast.error('Failed'); }
  };

  const handleDeleteReward = async (id) => {
    try { await loyaltyAPI.deleteReward(id); loyaltyAPI.getRewards().then(r => setRewards(r.data)); }
    catch (e) { toast.error('Failed'); }
  };

  const handleCreateEvent = async () => {
    if (!eventForm.name || !eventForm.date) { toast.error('Name and date required'); return; }
    try {
      await eventsAPI.create(eventForm);
      toast.success('Event created');
      setEventDialog(false);
      eventsAPI.getAll().then(r => setEvents(r.data));
    } catch (e) { toast.error('Failed'); }
  };

  return (
    <div className="space-y-6" data-testid="loyalty-events-page">
      <div className="flex items-center gap-3">
        <div className="w-12 h-12 rounded-xl flex items-center justify-center" style={{ background: 'linear-gradient(135deg, #F59E0B, #EF4444)' }}>
          <Award size={24} className="text-white" />
        </div>
        <div>
          <h1 className="text-2xl font-bold" style={{ color: theme.text }}>Loyalty & Events</h1>
          <p className="text-sm text-gray-500">Membership tiers, rewards & experiences</p>
        </div>
      </div>

      <Tabs value={tab} onValueChange={setTab}>
        <TabsList>
          <TabsTrigger value="tiers" data-testid="tab-tiers">Membership Tiers</TabsTrigger>
          <TabsTrigger value="rewards" data-testid="tab-rewards">Rewards</TabsTrigger>
          <TabsTrigger value="events" data-testid="tab-events">Events & Experiences</TabsTrigger>
        </TabsList>

        <TabsContent value="tiers" className="mt-4">
          <div className="grid grid-cols-4 gap-4">
            {tiers.map((tier, i) => {
              const tc = TIER_COLORS[tier.name] || TIER_COLORS.Bronze;
              const Icon = tc.icon;
              return (
                <Card key={i} className="border-0 shadow-sm overflow-hidden" data-testid={`tier-${tier.name.toLowerCase()}`}>
                  <div className="h-2" style={{ background: tc.color }} />
                  <CardContent className="p-5">
                    <div className="flex items-center gap-2 mb-3">
                      <div className="w-10 h-10 rounded-full flex items-center justify-center" style={{ background: tc.bg }}>
                        <Icon size={20} style={{ color: tc.color }} />
                      </div>
                      <div>
                        <h3 className="font-bold" style={{ color: tc.color }}>{tier.name}</h3>
                        <p className="text-[10px] text-gray-500">{tier.minPoints}+ points</p>
                      </div>
                    </div>
                    <p className="text-sm font-medium mb-2">
                      <span style={{ color: tc.color }}>{tier.multiplier}x</span> points multiplier
                    </p>
                    <div className="space-y-1.5">
                      {tier.perks.map((perk, j) => (
                        <div key={j} className="flex items-center gap-2 text-xs text-gray-600">
                          <div className="w-1.5 h-1.5 rounded-full" style={{ background: tc.color }} />
                          {perk}
                        </div>
                      ))}
                    </div>
                  </CardContent>
                </Card>
              );
            })}
          </div>
        </TabsContent>

        <TabsContent value="rewards" className="mt-4 space-y-4">
          <div className="flex justify-end">
            <Button onClick={() => setRewardDialog(true)} style={{ background: theme.primary }} data-testid="create-reward-btn">
              <Plus size={16} className="mr-1" /> New Reward
            </Button>
          </div>
          <div className="grid grid-cols-3 gap-4">
            {rewards.length === 0 ? (
              <Card className="col-span-3 border-0 shadow-sm">
                <CardContent className="py-12 text-center text-gray-400">
                  <Gift size={40} className="mx-auto mb-3 opacity-30" />
                  <p>No rewards configured yet. Create your first reward!</p>
                </CardContent>
              </Card>
            ) : rewards.map(r => (
              <Card key={r.id} className="border-0 shadow-sm" data-testid={`reward-${r.id}`}>
                <CardContent className="p-5">
                  <div className="flex items-start justify-between">
                    <div className="flex items-center gap-2">
                      <Gift size={18} style={{ color: theme.primary }} />
                      <h3 className="font-semibold" style={{ color: theme.text }}>{r.name}</h3>
                    </div>
                    <Button variant="ghost" size="sm" className="h-6 px-1 text-red-400" onClick={() => handleDeleteReward(r.id)}>
                      <Trash2 size={12} />
                    </Button>
                  </div>
                  {r.description && <p className="text-xs text-gray-500 mt-1">{r.description}</p>}
                  <div className="flex items-center gap-2 mt-3">
                    <Badge style={{ background: `${theme.primary}15`, color: theme.primary }}>{r.pointsCost} pts</Badge>
                    <Badge variant="outline" className="text-[10px] capitalize">{r.rewardType?.replace('_', ' ')}</Badge>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        </TabsContent>

        <TabsContent value="events" className="mt-4 space-y-4">
          <div className="flex justify-end">
            <Button onClick={() => setEventDialog(true)} style={{ background: theme.primary }} data-testid="create-event-btn">
              <Plus size={16} className="mr-1" /> New Event
            </Button>
          </div>
          <div className="grid grid-cols-2 gap-4">
            {events.length === 0 ? (
              <Card className="col-span-2 border-0 shadow-sm">
                <CardContent className="py-12 text-center text-gray-400">
                  <Ticket size={40} className="mx-auto mb-3 opacity-30" />
                  <p>No upcoming events. Create an experience for your guests!</p>
                </CardContent>
              </Card>
            ) : events.map(evt => {
              const etColor = EVENT_TYPE_COLORS[evt.eventType] || theme.primary;
              const remaining = evt.capacity - (evt.ticketsBooked || 0);
              return (
                <Card key={evt.id} className="border-0 shadow-sm overflow-hidden" data-testid={`event-${evt.id}`}>
                  <div className="h-1.5" style={{ background: etColor }} />
                  <CardContent className="p-5">
                    <div className="flex items-start justify-between mb-2">
                      <h3 className="font-bold text-lg" style={{ color: theme.text }}>{evt.name}</h3>
                      <Badge style={{ background: `${etColor}15`, color: etColor }} className="text-[10px] capitalize">
                        {evt.eventType?.replace('_', ' ')}
                      </Badge>
                    </div>
                    {evt.description && <p className="text-sm text-gray-500 mb-3">{evt.description}</p>}
                    <div className="grid grid-cols-3 gap-3 text-center py-2 border-t border-b">
                      <div>
                        <Calendar size={14} className="mx-auto text-gray-400 mb-1" />
                        <p className="text-xs font-medium">{evt.date}</p>
                        <p className="text-[10px] text-gray-500">{evt.time}</p>
                      </div>
                      <div>
                        <Users size={14} className="mx-auto text-gray-400 mb-1" />
                        <p className="text-xs font-medium">{evt.ticketsBooked || 0}/{evt.capacity}</p>
                        <p className="text-[10px] text-gray-500">{remaining} left</p>
                      </div>
                      <div>
                        <Ticket size={14} className="mx-auto text-gray-400 mb-1" />
                        <p className="text-xs font-medium">${evt.ticketPrice}</p>
                        <p className="text-[10px] text-gray-500">per ticket</p>
                      </div>
                    </div>
                    <div className="mt-3">
                      <div className="w-full h-1.5 bg-gray-200 rounded-full">
                        <div className="h-full rounded-full" style={{
                          width: `${(evt.ticketsBooked || 0) / evt.capacity * 100}%`,
                          background: etColor
                        }} />
                      </div>
                    </div>
                  </CardContent>
                </Card>
              );
            })}
          </div>
        </TabsContent>
      </Tabs>

      {/* Reward Dialog */}
      <Dialog open={rewardDialog} onOpenChange={setRewardDialog}>
        <DialogContent className="max-w-sm" data-testid="reward-dialog">
          <DialogHeader><DialogTitle>Create Reward</DialogTitle></DialogHeader>
          <div className="space-y-3">
            <div><label className="text-xs font-medium text-gray-500 mb-1 block">Name *</label>
              <Input data-testid="reward-name" value={rewardForm.name} onChange={e => setRewardForm(f => ({ ...f, name: e.target.value }))} /></div>
            <div><label className="text-xs font-medium text-gray-500 mb-1 block">Description</label>
              <Input value={rewardForm.description} onChange={e => setRewardForm(f => ({ ...f, description: e.target.value }))} /></div>
            <div><label className="text-xs font-medium text-gray-500 mb-1 block">Points Cost</label>
              <Input type="number" value={rewardForm.pointsCost} onChange={e => setRewardForm(f => ({ ...f, pointsCost: parseInt(e.target.value) || 0 }))} /></div>
            <div><label className="text-xs font-medium text-gray-500 mb-1 block">Type</label>
              <Select value={rewardForm.rewardType} onValueChange={v => setRewardForm(f => ({ ...f, rewardType: v }))}>
                <SelectTrigger><SelectValue /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="discount">Discount</SelectItem>
                  <SelectItem value="free_item">Free Item</SelectItem>
                  <SelectItem value="experience">Experience</SelectItem>
                </SelectContent>
              </Select></div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setRewardDialog(false)}>Cancel</Button>
            <Button onClick={handleCreateReward} style={{ background: theme.primary }} data-testid="save-reward-btn">Create</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Event Dialog */}
      <Dialog open={eventDialog} onOpenChange={setEventDialog}>
        <DialogContent className="max-w-md" data-testid="event-dialog">
          <DialogHeader><DialogTitle>Create Event</DialogTitle></DialogHeader>
          <div className="space-y-3">
            <div><label className="text-xs font-medium text-gray-500 mb-1 block">Event Name *</label>
              <Input data-testid="event-name" value={eventForm.name} onChange={e => setEventForm(f => ({ ...f, name: e.target.value }))} /></div>
            <div><label className="text-xs font-medium text-gray-500 mb-1 block">Description</label>
              <Input value={eventForm.description} onChange={e => setEventForm(f => ({ ...f, description: e.target.value }))} /></div>
            <div className="grid grid-cols-2 gap-3">
              <div><label className="text-xs font-medium text-gray-500 mb-1 block">Date *</label>
                <Input type="date" value={eventForm.date} onChange={e => setEventForm(f => ({ ...f, date: e.target.value }))} data-testid="event-date" /></div>
              <div><label className="text-xs font-medium text-gray-500 mb-1 block">Time</label>
                <Input type="time" value={eventForm.time} onChange={e => setEventForm(f => ({ ...f, time: e.target.value }))} /></div>
              <div><label className="text-xs font-medium text-gray-500 mb-1 block">Capacity</label>
                <Input type="number" value={eventForm.capacity} onChange={e => setEventForm(f => ({ ...f, capacity: parseInt(e.target.value) || 0 }))} /></div>
              <div><label className="text-xs font-medium text-gray-500 mb-1 block">Ticket Price ($)</label>
                <Input type="number" value={eventForm.ticketPrice} onChange={e => setEventForm(f => ({ ...f, ticketPrice: parseFloat(e.target.value) || 0 }))} /></div>
            </div>
            <div><label className="text-xs font-medium text-gray-500 mb-1 block">Type</label>
              <Select value={eventForm.eventType} onValueChange={v => setEventForm(f => ({ ...f, eventType: v }))}>
                <SelectTrigger><SelectValue /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="dining">Special Dining</SelectItem>
                  <SelectItem value="wine_pairing">Wine Pairing</SelectItem>
                  <SelectItem value="cooking_class">Cooking Class</SelectItem>
                  <SelectItem value="live_music">Live Music</SelectItem>
                  <SelectItem value="private">Private Event</SelectItem>
                </SelectContent>
              </Select></div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setEventDialog(false)}>Cancel</Button>
            <Button onClick={handleCreateEvent} style={{ background: theme.primary }} data-testid="save-event-btn">Create Event</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
