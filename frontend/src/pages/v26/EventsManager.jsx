import React, { useEffect, useState } from 'react';
import { Card, CardContent } from '../../components/ui/card';
import { Button } from '../../components/ui/button';
import { Input } from '../../components/ui/input';
import { Textarea } from '../../components/ui/textarea';
import { Badge } from '../../components/ui/badge';
import { useToast } from '../../hooks/use-toast';
import { useTheme } from '../../contexts/ThemeContext';
import { v26API } from '../../services/api';
import { Calendar, CalendarDays, Plus, Edit2, Save, Sparkles } from 'lucide-react';

export default function EventsManager() {
  const { theme } = useTheme(); const { toast } = useToast();
  const [rows, setRows] = useState([]);
  const [editing, setEditing] = useState(null);
  const [aiPreview, setAiPreview] = useState(null);
  const [aiLoading, setAiLoading] = useState(false);

  const load = () => v26API.listEvents().then(r => setRows(r.data || []));
  useEffect(() => { load(); }, []);

  const blank = () => ({
    title: '', description: '', date: new Date().toISOString().slice(0, 10),
    startTime: '18:00', endTime: '21:00', capacity: 30, pricePerGuest: 0,
    category: 'experience', termsAndConditions: '',
  });

  const save = async () => {
    try {
      if (editing.id) await v26API.updateEvent(editing.id, editing);
      else await v26API.createEvent(editing);
      toast({ title: 'Saved' }); setEditing(null); load();
    } catch (e) { toast({ title: 'Failed', description: e?.response?.data?.detail, variant: 'destructive' }); }
  };

  const previewMarketing = async (date) => {
    setAiLoading(true);
    try { const r = await v26API.eventAiPreview(date); setAiPreview(r.data); }
    catch { toast({ title: 'AI preview unavailable', variant: 'destructive' }); }
    finally { setAiLoading(false); }
  };

  const book = async (eid) => {
    const name = prompt('Guest name?'); if (!name) return;
    const party = parseInt(prompt('Party size?') || '1');
    try { await v26API.bookEvent(eid, { guestName: name, partySize: party }); toast({ title: 'Booked' }); load(); }
    catch (e) { toast({ title: 'Could not book', description: e?.response?.data?.detail, variant: 'destructive' }); }
  };

  return (
    <div className="space-y-6" data-testid="events-page">
      <div className="flex justify-between items-center">
        <h1 className="text-3xl font-bold flex items-center gap-2" style={{ color: theme.text }}>
          <Calendar className="text-purple-600" /> Events & Experiences
        </h1>
        <Button onClick={() => setEditing(blank())} style={{ background: theme.primary }} data-testid="new-event-btn">
          <Plus size={14} className="mr-1.5" /> New Event
        </Button>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4" data-testid="events-grid">
        {rows.length === 0 ? <Card className="col-span-full"><CardContent className="p-8 text-center text-gray-400">No events yet</CardContent></Card> :
          rows.map(e => {
            const booked = (e.bookings || []).reduce((s, b) => s + (b.partySize || 0), 0);
            const remaining = e.capacity - booked;
            return (
              <Card key={e.id} className="hover:shadow-lg transition" data-testid={`event-${e.id}`}>
                <CardContent className="p-5 space-y-2">
                  <div className="flex justify-between items-start">
                    <h3 className="font-bold">{e.title}</h3>
                    <Badge variant="outline">{e.category}</Badge>
                  </div>
                  <p className="text-xs text-gray-500 flex items-center gap-1"><CalendarDays size={12} /> {e.date} · {e.startTime}–{e.endTime}</p>
                  <p className="text-sm text-gray-700 line-clamp-2">{e.description}</p>
                  <div className="flex items-center justify-between text-xs pt-2 border-t">
                    <span>${e.pricePerGuest}/guest</span>
                    <Badge className={remaining > 5 ? 'bg-emerald-100 text-emerald-700' : remaining > 0 ? 'bg-amber-100 text-amber-700' : 'bg-red-100 text-red-700'}>
                      {remaining > 0 ? `${remaining} left` : 'Sold out'}
                    </Badge>
                  </div>
                  <div className="flex gap-1 pt-1">
                    <Button size="sm" variant="outline" onClick={() => book(e.id)} disabled={remaining <= 0} data-testid={`book-${e.id}`}>Book</Button>
                    <Button size="sm" variant="outline" onClick={() => previewMarketing(e.date)} data-testid={`preview-${e.id}`}><Sparkles size={12} className="mr-1" /> AI</Button>
                    <Button size="sm" variant="ghost" onClick={() => setEditing(e)}><Edit2 size={12} /></Button>
                  </div>
                </CardContent>
              </Card>
            );
          })}
      </div>

      {aiPreview && (
        <Card className="border-purple-300 bg-purple-50"><CardContent className="p-5" data-testid="ai-preview">
          <div className="flex justify-between items-start mb-3">
            <h3 className="font-bold flex items-center gap-1.5"><Sparkles size={16} className="text-purple-600" /> AI Marketing Preview · {aiPreview.date}</h3>
            <button onClick={() => setAiPreview(null)} className="text-gray-400 hover:text-red-600">×</button>
          </div>
          {aiLoading ? <p className="text-sm text-gray-500">Generating…</p> : (
            <div className="space-y-2 text-sm">
              <p><strong>Subject:</strong> {aiPreview.preview?.subject}</p>
              <p className="whitespace-pre-wrap text-gray-700">{aiPreview.preview?.emailBody}</p>
              <p className="italic text-purple-700">SMS: {aiPreview.preview?.sms}</p>
              {aiPreview.preview?.highlights && (
                <ul className="text-xs">{(aiPreview.preview.highlights || []).map((h, i) => <li key={i}>· {h}</li>)}</ul>
              )}
            </div>
          )}
        </CardContent></Card>
      )}

      {editing && (
        <Card className="border-amber-300"><CardContent className="p-5 space-y-3" data-testid="event-editor">
          <h2 className="font-bold">{editing.id ? 'Edit' : 'New'} Event</h2>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
            <div className="md:col-span-2"><label className="text-xs uppercase text-gray-500">Title</label>
              <Input value={editing.title} onChange={e => setEditing({ ...editing, title: e.target.value })} /></div>
            <div><label className="text-xs uppercase text-gray-500">Category</label>
              <select className="w-full p-2 border rounded text-sm" value={editing.category} onChange={e => setEditing({ ...editing, category: e.target.value })}>
                <option>experience</option><option>tasting</option><option>live_music</option><option>workshop</option><option>private</option>
              </select></div>
            <div><label className="text-xs uppercase text-gray-500">Date</label>
              <Input type="date" value={editing.date} onChange={e => setEditing({ ...editing, date: e.target.value })} /></div>
            <div><label className="text-xs uppercase text-gray-500">Start</label>
              <Input type="time" value={editing.startTime} onChange={e => setEditing({ ...editing, startTime: e.target.value })} /></div>
            <div><label className="text-xs uppercase text-gray-500">End</label>
              <Input type="time" value={editing.endTime} onChange={e => setEditing({ ...editing, endTime: e.target.value })} /></div>
            <div><label className="text-xs uppercase text-gray-500">Capacity</label>
              <Input type="number" value={editing.capacity} onChange={e => setEditing({ ...editing, capacity: parseInt(e.target.value) || 0 })} /></div>
            <div><label className="text-xs uppercase text-gray-500">Price / Guest</label>
              <Input type="number" value={editing.pricePerGuest} onChange={e => setEditing({ ...editing, pricePerGuest: parseFloat(e.target.value) || 0 })} /></div>
          </div>
          <div><label className="text-xs uppercase text-gray-500">Description</label>
            <Textarea rows={3} value={editing.description} onChange={e => setEditing({ ...editing, description: e.target.value })} /></div>
          <div><label className="text-xs uppercase text-gray-500">Terms & Conditions</label>
            <Textarea rows={2} value={editing.termsAndConditions} onChange={e => setEditing({ ...editing, termsAndConditions: e.target.value })} /></div>
          <div className="flex gap-2">
            <Button onClick={save} style={{ background: theme.primary }} data-testid="save-event"><Save size={14} className="mr-1.5" /> Save</Button>
            <Button variant="outline" onClick={() => setEditing(null)}>Cancel</Button>
          </div>
        </CardContent></Card>
      )}
    </div>
  );
}
