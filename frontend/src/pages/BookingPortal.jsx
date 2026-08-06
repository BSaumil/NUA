import React, { useState, useEffect } from 'react';
import {
  CalendarDays, Clock, Users, MapPin, ChevronRight, Check,
  Phone, Mail, User, UtensilsCrossed, Music, Ticket, Star, ClipboardList
} from 'lucide-react';
import { Card, CardContent } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Badge } from '../components/ui/badge';
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue
} from '../components/ui/select';
import { publicAPI } from '../services/api';
import { toast } from 'sonner';

const STEPS = ['select', 'details', 'confirmed'];
const EVENT_ICONS = { dining: UtensilsCrossed, wine_pairing: Star, cooking_class: UtensilsCrossed, live_music: Music, private: Ticket };

export default function BookingPortal() {
  const [tab, setTab] = useState('reserve'); // reserve, waitlist, events, menu
  const [step, setStep] = useState('select');
  const [menu, setMenu] = useState([]);
  const [events, setEvents] = useState([]);
  const [slots, setSlots] = useState([]);
  const [form, setForm] = useState({
    guestName: '', guestPhone: '', guestEmail: '',
    partySize: 2, date: new Date().toISOString().split('T')[0],
    time: '', duration: 90, specialRequests: '',
  });
  const [waitlistForm, setWaitlistForm] = useState({ guestName: '', guestPhone: '', partySize: 2, preferences: '' });
  const [confirmData, setConfirmData] = useState(null);

  useEffect(() => {
    publicAPI.getMenu().then(r => setMenu(r.data.categories || [])).catch(() => {});
    publicAPI.getEvents().then(r => setEvents(r.data || [])).catch(() => {});
  }, []);

  useEffect(() => {
    if (form.date && form.partySize) {
      publicAPI.getAvailableSlots(form.date, form.partySize)
        .then(r => setSlots(r.data.slots || []))
        .catch(() => setSlots([]));
    }
  }, [form.date, form.partySize]);

  const handleBook = async () => {
    if (!form.guestName || !form.date || !form.time) { toast.error('Please fill in all required fields'); return; }
    try {
      const res = await publicAPI.book(form);
      setConfirmData(res.data);
      setStep('confirmed');
      toast.success('Reservation confirmed!');
    } catch (e) { toast.error('Booking failed. Please try again.'); }
  };

  const handleJoinWaitlist = async () => {
    if (!waitlistForm.guestName) { toast.error('Name is required'); return; }
    try {
      const res = await publicAPI.joinWaitlist(waitlistForm);
      setConfirmData(res.data);
      setStep('confirmed');
      toast.success(`You're #${res.data.position} on the waitlist!`);
    } catch (e) { toast.error('Failed to join waitlist'); }
  };

  const reset = () => { setStep('select'); setConfirmData(null); setForm(f => ({ ...f, time: '' })); };

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-900 via-gray-800 to-gray-900" data-testid="booking-portal">
      {/* Header */}
      <div className="max-w-4xl mx-auto pt-10 pb-6 px-4">
        <div className="text-center">
          <h1 className="text-4xl font-bold text-white tracking-tight">NUA</h1>
        </div>

        {/* Tab Navigation */}
        <div className="flex flex-wrap justify-center gap-2 mt-6 sm:mt-8">
          {[
            { id: 'reserve', label: 'Reserve', fullLabel: 'Reserve a Table', icon: CalendarDays },
            { id: 'waitlist', label: 'Waitlist', fullLabel: 'Join Waitlist', icon: ClipboardList },
            { id: 'events', label: 'Events', fullLabel: 'Events', icon: Ticket },
            { id: 'menu', label: 'Menu', fullLabel: 'View Menu', icon: UtensilsCrossed },
          ].map(t => (
            <button key={t.id} onClick={() => { setTab(t.id); reset(); }}
              className={`flex items-center gap-1.5 sm:gap-2 px-3 sm:px-5 py-2 sm:py-2.5 rounded-full text-xs sm:text-sm font-medium transition-all ${tab === t.id ? 'bg-white text-gray-900' : 'text-gray-400 hover:text-white hover:bg-white/10'}`}
              data-testid={`portal-tab-${t.id}`}>
              <t.icon size={14} className="sm:w-4 sm:h-4" /> <span className="hidden sm:inline">{t.fullLabel}</span><span className="sm:hidden">{t.label}</span>
            </button>
          ))}
        </div>
      </div>

      <div className="max-w-2xl mx-auto px-4 pb-16">
        {/* RESERVE A TABLE */}
        {tab === 'reserve' && step !== 'confirmed' && (
          <Card className="border-0 shadow-2xl bg-white/95 backdrop-blur">
            <CardContent className="p-8">
              {step === 'select' && (
                <div className="space-y-6">
                  <h2 className="text-xl font-bold text-gray-900">Find a Table</h2>
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                    <div>
                      <label className="text-xs font-medium text-gray-500 mb-1.5 block">Date</label>
                      <Input type="date" value={form.date} onChange={e => setForm(f => ({ ...f, date: e.target.value }))}
                        min={new Date().toISOString().split('T')[0]} data-testid="portal-date" />
                    </div>
                    <div>
                      <label className="text-xs font-medium text-gray-500 mb-1.5 block">Party Size</label>
                      <Select value={String(form.partySize)} onValueChange={v => setForm(f => ({ ...f, partySize: parseInt(v) }))}>
                        <SelectTrigger data-testid="portal-party-size"><SelectValue /></SelectTrigger>
                        <SelectContent>
                          {[1, 2, 3, 4, 5, 6, 7, 8, 10, 12, 15, 20].map(n => (
                            <SelectItem key={n} value={String(n)}>{n} {n === 1 ? 'guest' : 'guests'}</SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                    </div>
                  </div>

                  <div>
                    <label className="text-xs font-medium text-gray-500 mb-2 block">Available Times</label>
                    {slots.length === 0 ? (
                      <p className="text-sm text-gray-400 text-center py-6">No slots available for this date/party size</p>
                    ) : (
                      <div className="grid grid-cols-3 sm:grid-cols-4 gap-2 max-h-48 overflow-y-auto">
                        {slots.map(s => (
                          <button key={s.time} onClick={() => setForm(f => ({ ...f, time: s.time }))}
                            className={`px-3 py-2.5 rounded-lg text-sm font-medium border transition-all ${form.time === s.time ? 'bg-gray-900 text-white border-gray-900' : 'bg-white text-gray-700 border-gray-200 hover:border-gray-400'}`}
                            data-testid={`slot-${s.time}`}>
                            {s.time}
                          </button>
                        ))}
                      </div>
                    )}
                  </div>

                  <Button className="w-full h-12 bg-gray-900 hover:bg-gray-800 text-white" disabled={!form.time}
                    onClick={() => setStep('details')} data-testid="portal-continue-btn">
                    Continue <ChevronRight size={16} className="ml-1" />
                  </Button>
                </div>
              )}

              {step === 'details' && (
                <div className="space-y-5">
                  <div className="flex items-center gap-2 mb-2">
                    <button onClick={() => setStep('select')} className="text-sm text-gray-500 hover:text-gray-700">Back</button>
                    <span className="text-gray-300">|</span>
                    <span className="text-sm text-gray-900 font-medium">{form.date} at {form.time} for {form.partySize}</span>
                  </div>
                  <h2 className="text-xl font-bold text-gray-900">Your Details</h2>
                  <div className="space-y-3">
                    <div>
                      <label className="text-xs font-medium text-gray-500 mb-1 block">Full Name *</label>
                      <Input data-testid="portal-name" value={form.guestName} onChange={e => setForm(f => ({ ...f, guestName: e.target.value }))}
                        placeholder="John Smith" />
                    </div>
                    <div className="grid grid-cols-2 gap-3">
                      <div>
                        <label className="text-xs font-medium text-gray-500 mb-1 block">Phone</label>
                        <Input data-testid="portal-phone" value={form.guestPhone} onChange={e => setForm(f => ({ ...f, guestPhone: e.target.value }))}
                          placeholder="+61 400 000 000" />
                      </div>
                      <div>
                        <label className="text-xs font-medium text-gray-500 mb-1 block">Email</label>
                        <Input data-testid="portal-email" type="email" value={form.guestEmail}
                          onChange={e => setForm(f => ({ ...f, guestEmail: e.target.value }))} placeholder="email@example.com" />
                      </div>
                    </div>
                    <div>
                      <label className="text-xs font-medium text-gray-500 mb-1 block">Special Requests</label>
                      <Input data-testid="portal-requests" value={form.specialRequests}
                        onChange={e => setForm(f => ({ ...f, specialRequests: e.target.value }))}
                        placeholder="Birthday, high chair, dietary needs..." />
                    </div>
                  </div>
                  <Button className="w-full h-12 bg-gray-900 hover:bg-gray-800 text-white"
                    onClick={handleBook} data-testid="portal-confirm-btn">
                    Confirm Reservation
                  </Button>
                </div>
              )}
            </CardContent>
          </Card>
        )}

        {/* WAITLIST */}
        {tab === 'waitlist' && step !== 'confirmed' && (
          <Card className="border-0 shadow-2xl bg-white/95 backdrop-blur">
            <CardContent className="p-8 space-y-5">
              <h2 className="text-xl font-bold text-gray-900">Join the Waitlist</h2>
              <p className="text-sm text-gray-500">No tables available right now? Join our waitlist and we'll seat you as soon as possible.</p>
              <div className="space-y-3">
                <div>
                  <label className="text-xs font-medium text-gray-500 mb-1 block">Your Name *</label>
                  <Input data-testid="wl-portal-name" value={waitlistForm.guestName}
                    onChange={e => setWaitlistForm(f => ({ ...f, guestName: e.target.value }))} placeholder="Your name" />
                </div>
                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <label className="text-xs font-medium text-gray-500 mb-1 block">Phone</label>
                    <Input value={waitlistForm.guestPhone} onChange={e => setWaitlistForm(f => ({ ...f, guestPhone: e.target.value }))}
                      placeholder="+61 400 000 000" />
                  </div>
                  <div>
                    <label className="text-xs font-medium text-gray-500 mb-1 block">Party Size</label>
                    <Select value={String(waitlistForm.partySize)} onValueChange={v => setWaitlistForm(f => ({ ...f, partySize: parseInt(v) }))}>
                      <SelectTrigger><SelectValue /></SelectTrigger>
                      <SelectContent>
                        {[1, 2, 3, 4, 5, 6, 8, 10].map(n => <SelectItem key={n} value={String(n)}>{n} guests</SelectItem>)}
                      </SelectContent>
                    </Select>
                  </div>
                </div>
                <div>
                  <label className="text-xs font-medium text-gray-500 mb-1 block">Seating Preference</label>
                  <Select value={waitlistForm.preferences || 'any'} onValueChange={v => setWaitlistForm(f => ({ ...f, preferences: v === 'any' ? '' : v }))}>
                    <SelectTrigger><SelectValue placeholder="Any" /></SelectTrigger>
                    <SelectContent>
                      <SelectItem value="any">Any</SelectItem>
                      <SelectItem value="indoor">Indoor</SelectItem>
                      <SelectItem value="outdoor">Outdoor</SelectItem>
                      <SelectItem value="bar">Bar</SelectItem>
                      <SelectItem value="window">Window</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
              </div>
              <Button className="w-full h-12 bg-gray-900 hover:bg-gray-800 text-white"
                onClick={handleJoinWaitlist} data-testid="portal-join-waitlist-btn">
                Join Waitlist
              </Button>
            </CardContent>
          </Card>
        )}

        {/* CONFIRMATION */}
        {step === 'confirmed' && confirmData && (
          <Card className="border-0 shadow-2xl bg-white/95 backdrop-blur">
            <CardContent className="p-8 text-center">
              <div className="w-16 h-16 rounded-full bg-green-100 flex items-center justify-center mx-auto mb-4">
                <Check size={32} className="text-green-600" />
              </div>
              <h2 className="text-2xl font-bold text-gray-900 mb-2">
                {tab === 'reserve' ? 'Reservation Confirmed!' : 'Added to Waitlist!'}
              </h2>
              {tab === 'reserve' && (
                <div className="space-y-2 mt-4 text-sm text-gray-600">
                  <p>Booking Reference: <span className="font-mono font-bold text-gray-900">{confirmData.reservationId}</span></p>
                  <p>{form.date} at {form.time} for {form.partySize} guests</p>
                </div>
              )}
              {tab === 'waitlist' && (
                <div className="space-y-2 mt-4 text-sm text-gray-600">
                  <p>Your position: <span className="text-2xl font-bold text-gray-900">#{confirmData.position}</span></p>
                  <p>Estimated wait: ~{confirmData.estimatedWait} minutes</p>
                </div>
              )}
              <Button className="mt-6 bg-gray-900 hover:bg-gray-800 text-white" onClick={reset} data-testid="portal-new-booking-btn">
                Make Another Booking
              </Button>
            </CardContent>
          </Card>
        )}

        {/* EVENTS */}
        {tab === 'events' && (
          <div className="space-y-4">
            {events.length === 0 ? (
              <Card className="border-0 shadow-2xl bg-white/95"><CardContent className="p-8 text-center text-gray-400">No upcoming events</CardContent></Card>
            ) : events.map(evt => {
              const Icon = EVENT_ICONS[evt.eventType] || Ticket;
              const remaining = evt.capacity - (evt.ticketsBooked || 0);
              return (
                <Card key={evt.id} className="border-0 shadow-xl bg-white/95 backdrop-blur overflow-hidden" data-testid={`portal-event-${evt.id}`}>
                  <CardContent className="p-6">
                    <div className="flex items-start justify-between">
                      <div>
                        <Badge className="bg-gray-900 text-white text-[10px] mb-2 capitalize">{evt.eventType?.replace('_', ' ')}</Badge>
                        <h3 className="text-lg font-bold text-gray-900">{evt.name}</h3>
                        {evt.description && <p className="text-sm text-gray-500 mt-1">{evt.description}</p>}
                      </div>
                      {evt.ticketPrice > 0 && <div className="text-right">
                        <p className="text-2xl font-bold text-gray-900">${evt.ticketPrice}</p>
                        <p className="text-[10px] text-gray-500">per ticket</p>
                      </div>}
                    </div>
                    <div className="flex items-center gap-4 mt-4 text-sm text-gray-600">
                      <span className="flex items-center gap-1"><CalendarDays size={14} />{evt.date}</span>
                      <span className="flex items-center gap-1"><Clock size={14} />{evt.time}</span>
                      <span className="flex items-center gap-1"><Users size={14} />{remaining} spots left</span>
                    </div>
                  </CardContent>
                </Card>
              );
            })}
          </div>
        )}

        {/* MENU */}
        {tab === 'menu' && (
          <div className="space-y-6">
            {menu.map((cat, i) => (
              <Card key={i} className="border-0 shadow-xl bg-white/95 backdrop-blur">
                <CardContent className="p-6">
                  <h3 className="text-lg font-bold text-gray-900 mb-3">{cat.name}</h3>
                  <div className="space-y-3">
                    {cat.items.map((item, j) => (
                      <div key={j} className="flex items-center justify-between py-2 border-b border-gray-100 last:border-0">
                        <div>
                          <p className="font-medium text-gray-900">{item.name}</p>
                          {item.description && <p className="text-xs text-gray-500">{item.description}</p>}
                        </div>
                        <span className="font-bold text-gray-900">${item.price.toFixed(2)}</span>
                      </div>
                    ))}
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
