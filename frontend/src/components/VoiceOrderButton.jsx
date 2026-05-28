import React, { useState, useRef } from 'react';
import { Mic, MicOff, Square, Loader2 } from 'lucide-react';
import { Button } from '../components/ui/button';
import { useTheme } from '../contexts/ThemeContext';
import { v15API, phaseEFAPI } from '../services/api';
import { toast } from 'sonner';

export default function VoiceOrderButton({ onAddSuggestions, onExtendedAction }) {
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
              const transcript = r.data?.transcript || '';
              if (sugg.length > 0) {
                onAddSuggestions(sugg);
                toast.success(`Heard: "${transcript}" — added ${sugg.length} item(s)`);
              } else if (transcript) {
                // Try extended commands (void last, price change, 86)
                try {
                  const ext = await phaseEFAPI.voiceExtended(transcript);
                  if (ext.data?.intent === 'void_last_item' && onExtendedAction) {
                    onExtendedAction({ action: 'void_last_item' });
                    toast.success('Voided last item');
                  } else if (ext.data?.intent === 'price_change') {
                    toast.success(`Price of ${ext.data.productName}: $${ext.data.oldPrice} → $${ext.data.newPrice}`);
                  } else if (ext.data?.intent === 'eighty_six') {
                    toast.success(`${ext.data.productName} 86'd (out of stock)`);
                  } else {
                    toast(`Heard: "${transcript}" — no matching action`);
                  }
                } catch {
                  toast(`Heard: "${transcript}" — no matching products`);
                }
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
