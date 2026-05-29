import React, { useEffect, useRef, useState } from 'react';
import { Card, CardContent } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Textarea } from '../components/ui/textarea';
import { Badge } from '../components/ui/badge';
import { aiWave2API } from '../services/api';
import { useToast } from '../hooks/use-toast';
import { useTheme } from '../contexts/ThemeContext';
import { Mic, Square, BookOpen, Wand2, Clock, Utensils } from 'lucide-react';

export default function VoiceRecipe() {
  const { theme } = useTheme();
  const { toast } = useToast();
  const [text, setText] = useState('');
  const [recipes, setRecipes] = useState([]);
  const [generating, setGenerating] = useState(false);
  const [recording, setRecording] = useState(false);
  const mediaRef = useRef(null);
  const chunksRef = useRef([]);

  const load = async () => {
    try { const r = await aiWave2API.listRecipes(); setRecipes(r.data || []); } catch {}
  };
  useEffect(() => { load(); }, []);

  const generate = async () => {
    if (!text.trim()) return;
    setGenerating(true);
    try {
      await aiWave2API.voiceRecipe(text, null, null);
      toast({ title: 'Recipe generated' });
      setText('');
      await load();
    } catch (e) {
      toast({ title: 'Error', description: e?.response?.data?.detail || 'Failed to generate', variant: 'destructive' });
    } finally { setGenerating(false); }
  };

  const startRec = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const rec = new MediaRecorder(stream, { mimeType: 'audio/webm' });
      chunksRef.current = [];
      rec.ondataavailable = e => { if (e.data.size > 0) chunksRef.current.push(e.data); };
      rec.onstop = async () => {
        stream.getTracks().forEach(t => t.stop());
        const blob = new Blob(chunksRef.current, { type: 'audio/webm' });
        const reader = new FileReader();
        reader.onloadend = async () => {
          const b64 = reader.result.split(',')[1];
          setGenerating(true);
          try {
            await aiWave2API.voiceRecipe('', b64, 'audio/webm');
            toast({ title: 'Recipe generated from voice' });
            await load();
          } catch (e) {
            toast({ title: 'Error', description: e?.response?.data?.detail || 'Voice failed', variant: 'destructive' });
          } finally { setGenerating(false); }
        };
        reader.readAsDataURL(blob);
      };
      mediaRef.current = rec;
      rec.start();
      setRecording(true);
    } catch (e) { toast({ title: 'Mic error', description: String(e), variant: 'destructive' }); }
  };
  const stopRec = () => { mediaRef.current?.stop(); setRecording(false); };

  return (
    <div className="space-y-6" data-testid="voice-recipe-page">
      <div>
        <h1 className="text-3xl font-bold flex items-center gap-2" style={{ color: theme.text }}>
          <BookOpen className="text-rose-600" /> Voice-to-Recipe
        </h1>
        <p className="text-sm text-gray-500 mt-1">Describe a dish · AI structures it into a recipe spec</p>
      </div>

      <Card>
        <CardContent className="p-5 space-y-3">
          <Textarea
            value={text}
            onChange={e => setText(e.target.value)}
            rows={4}
            placeholder="e.g. Spicy lamb shank for 4 — sear lamb, braise 2 hrs with red wine, carrots, garlic, rosemary; serve on creamy polenta…"
            data-testid="recipe-text"
          />
          <div className="flex gap-2">
            <Button onClick={generate} disabled={!text.trim() || generating} style={{ background: theme.primary }} data-testid="recipe-generate">
              <Wand2 size={14} className="mr-1.5" /> {generating ? 'Generating…' : 'Generate from Text'}
            </Button>
            {!recording ? (
              <Button variant="outline" onClick={startRec} disabled={generating} data-testid="recipe-mic-start"><Mic size={14} className="mr-1.5" /> Record Voice</Button>
            ) : (
              <Button variant="destructive" onClick={stopRec} data-testid="recipe-mic-stop"><Square size={14} className="mr-1.5" /> Stop Recording</Button>
            )}
          </div>
        </CardContent>
      </Card>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4" data-testid="recipe-list">
        {recipes.length === 0 ? (
          <div className="col-span-full text-center py-12 text-gray-400">No recipes yet. Describe one above.</div>
        ) : recipes.map(r => (
          <Card key={r.id} className="hover:shadow-md transition-shadow" data-testid={`recipe-${r.id}`}>
            <CardContent className="p-5">
              <div className="flex items-start justify-between gap-2">
                <h3 className="font-bold text-lg">{r.name || 'Unnamed Recipe'}</h3>
                <Badge variant="outline" className="text-[10px]">{(r.tags || []).slice(0, 2).join(' · ')}</Badge>
              </div>
              <div className="flex gap-4 text-xs text-gray-500 mt-1">
                <span><Utensils size={10} className="inline mr-1" />{r.yield || '—'}</span>
                <span><Clock size={10} className="inline mr-1" />Prep {r.prepMin || '?'}m · Cook {r.cookMin || '?'}m</span>
              </div>
              {Array.isArray(r.ingredients) && r.ingredients.length > 0 && (
                <div className="mt-3">
                  <p className="text-[10px] uppercase tracking-widest text-gray-400 mb-1">Ingredients</p>
                  <ul className="text-xs space-y-0.5">
                    {r.ingredients.slice(0, 8).map((i, idx) => (<li key={idx}>· {i.quantity} {i.item}</li>))}
                    {r.ingredients.length > 8 && <li className="text-gray-400">+ {r.ingredients.length - 8} more</li>}
                  </ul>
                </div>
              )}
              {Array.isArray(r.steps) && r.steps.length > 0 && (
                <div className="mt-3">
                  <p className="text-[10px] uppercase tracking-widest text-gray-400 mb-1">Steps</p>
                  <ol className="text-xs space-y-0.5 list-decimal list-inside">
                    {r.steps.slice(0, 5).map((s, idx) => <li key={idx} className="line-clamp-1">{s}</li>)}
                    {r.steps.length > 5 && <li className="list-none text-gray-400">+ {r.steps.length - 5} more</li>}
                  </ol>
                </div>
              )}
              {Array.isArray(r.allergens) && r.allergens.length > 0 && (
                <div className="mt-2 flex gap-1 flex-wrap">
                  {r.allergens.map((a, i) => <Badge key={i} className="bg-red-50 text-red-700 hover:bg-red-50 text-[10px]">{a}</Badge>)}
                </div>
              )}
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  );
}
