import React, { useState, useRef } from 'react';
import { Mic, MicOff, Square, Loader2 } from 'lucide-react';
import { Button } from '../components/ui/button';
import { useTheme } from '../contexts/ThemeContext';
import { v15API } from '../services/api';
import { toast } from 'sonner';

export default function VoiceOrderButton({ onAddSuggestions }) {
  const { theme } = useTheme();
  const [recording, setRecording] = useState(false);
  const [processing, setProcessing] = useState(false);
  const mediaRef = useRef(null);
  const chunksRef = useRef([]);

  const start = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const mr = new MediaRecorder(stream);
      chunksRef.current = [];
      mr.ondataavailable = (e) => chunksRef.current.push(e.data);
      mr.onstop = async () => {
        const blob = new Blob(chunksRef.current, { type: 'audio/webm' });
        stream.getTracks().forEach(t => t.stop());
        setProcessing(true);
        try {
          const reader = new FileReader();
          reader.onloadend = async () => {
            try {
              const r = await v15API.voiceOrder(reader.result, 'audio/webm');
              const sugg = r.data?.suggestions || [];
              if (sugg.length > 0) {
                onAddSuggestions(sugg);
                toast.success(`Heard: "${r.data.transcript}" — added ${sugg.length} item(s)`);
              } else {
                toast(`Heard: "${r.data?.transcript || ''}" — no matching products`);
              }
            } catch (e) {
              toast.error('Voice processing failed');
            }
            setProcessing(false);
          };
          reader.readAsDataURL(blob);
        } catch { setProcessing(false); }
      };
      mr.start();
      mediaRef.current = mr;
      setRecording(true);
    } catch {
      toast.error('Microphone access denied');
    }
  };

  const stop = () => {
    if (mediaRef.current && mediaRef.current.state === 'recording') {
      mediaRef.current.stop();
      setRecording(false);
    }
  };

  return (
    <Button
      onClick={recording ? stop : start}
      disabled={processing}
      variant="outline"
      className={`h-9 px-3 ${recording ? 'bg-red-50 border-red-300 text-red-600 animate-pulse' : ''}`}
      data-testid="voice-order-btn"
      title="Voice order — say 'add two flat whites' etc"
    >
      {processing ? <Loader2 size={14} className="animate-spin" /> : recording ? <><Square size={12} className="mr-1" /> Stop</> : <><Mic size={14} className="mr-1" /> Voice</>}
    </Button>
  );
}
