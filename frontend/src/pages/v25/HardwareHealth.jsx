import React, { useEffect, useState } from 'react';
import { Card, CardContent } from '../../components/ui/card';
import { Badge } from '../../components/ui/badge';
import { v25API } from '../../services/api';
import { useTheme } from '../../contexts/ThemeContext';
import { Cpu } from 'lucide-react';

export default function HardwareHealth() {
  const { theme } = useTheme();
  const [devices, setDevices] = useState([]);
  useEffect(() => { v25API.hardware().then(r => setDevices(r.data || [])); }, []);
  return (
    <div className="space-y-6" data-testid="hardware-page">
      <h1 className="text-3xl font-bold flex items-center gap-2" style={{ color: theme.text }}><Cpu className="text-gray-600" /> Hardware Health</h1>
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {devices.map(d => (
          <Card key={d.id} data-testid={`device-${d.id}`}>
            <CardContent className="p-5 flex items-center justify-between">
              <div>
                <p className="font-medium">{d.name}</p>
                <p className="text-xs text-gray-500">{d.kind} · {d.id}</p>
              </div>
              <Badge className={d.status === 'online' ? 'bg-emerald-100 text-emerald-700' : 'bg-red-100 text-red-700'}>{d.status}</Badge>
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  );
}
