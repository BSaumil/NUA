import React, { useState, useEffect } from 'react';
import { Mic, Command } from 'lucide-react';
import { Dialog, DialogContent } from '../components/ui/dialog';
import { useTheme } from '../contexts/ThemeContext';
import { agentAPI } from '../services/api';

export default function VoiceCommandCatalog({ open, onClose }) {
  const { theme } = useTheme();
  const [catalog, setCatalog] = useState({});

  useEffect(() => { if (open) agentAPI.getCatalog().then(r => setCatalog(r.data || {})).catch(() => {}); }, [open]);

  return (
    <Dialog open={open} onOpenChange={onClose}>
      <DialogContent className="max-w-2xl max-h-[80vh] overflow-y-auto" data-testid="voice-catalog">
        <div className="flex items-center gap-3 mb-4">
          <div className="w-10 h-10 rounded-lg flex items-center justify-center" style={{ backgroundColor: `${theme.primary}15`, color: theme.primary }}><Mic size={20} /></div>
          <div><h2 className="font-bold">Voice Commands</h2><p className="text-xs text-gray-500">Hold the mic and say any of these. NUA will route to the right action.</p></div>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {Object.entries(catalog).map(([section, commands]) => (
            <div key={section} data-testid={`catalog-${section}`}>
              <p className="text-xs font-bold uppercase tracking-wider text-gray-400 mb-2">{section}</p>
              <ul className="space-y-1.5">
                {commands.map(c => (
                  <li key={c} className="text-sm bg-gray-50 px-3 py-2 rounded-lg flex items-center gap-2">
                    <Command size={12} className="text-gray-400" /> "{c}"
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </div>
      </DialogContent>
    </Dialog>
  );
}
