import React, { useState } from 'react';
import { Users, Send, Copy, Check } from 'lucide-react';
import { Button } from '../ui/button';
import { Input } from '../ui/input';
import { Card, CardContent, CardHeader, CardTitle } from '../ui/card';
import { toast } from 'sonner';

export function GroupInvite({ splitId, groupId, isOrganizer, participants = [] }) {
  const [invitePhone, setInvitePhone] = useState('');
  const [inviteCode, setInviteCode] = useState('');
  const [loading, setLoading] = useState(false);
  const [copied, setCopied] = useState(false);

  const handleSendInvite = async () => {
    if (!invitePhone.trim()) {
      toast.error('Enter a phone number');
      return;
    }

    setLoading(true);
    try {
      const response = await fetch(`/api/table/split/${splitId}/group/invite`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ phone: invitePhone }),
      });

      const data = await response.json();
      if (response.ok) {
        setInviteCode(data.inviteToken);
        toast.success('Invite sent!');
      } else {
        toast.error(data.error || 'Failed to send invite');
      }
    } catch (e) {
      toast.error('Failed to send invite');
    } finally {
      setLoading(false);
    }
  };

  const copyInviteCode = async () => {
    try {
      await navigator.clipboard.writeText(inviteCode);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch (e) {
      toast.error('Failed to copy');
    }
  };

  if (!isOrganizer) {
    return (
      <Card>
        <CardContent className="pt-4">
          <div className="flex items-center gap-2 text-sm text-gray-600">
            <Users size={16} />
            <span>{participants.length} guest(s) in group</span>
          </div>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-sm flex items-center gap-2">
          <Users size={16} /> Group Split
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-3">
        <div>
          <label className="text-xs font-medium text-gray-700">
            Invite another guest
          </label>
          <div className="flex gap-2 mt-1">
            <Input
              type="tel"
              placeholder="Phone number"
              value={invitePhone}
              onChange={(e) => setInvitePhone(e.target.value)}
              disabled={loading}
              className="text-sm"
            />
            <Button
              size="sm"
              onClick={handleSendInvite}
              disabled={loading}
              className="gap-1"
            >
              <Send size={14} />
              Invite
            </Button>
          </div>
        </div>

        {inviteCode && (
          <div className="p-2 rounded bg-blue-50 border border-blue-200">
            <p className="text-xs font-medium text-blue-900 mb-1">
              Share this code:
            </p>
            <div className="flex items-center gap-2">
              <code className="text-xs font-mono bg-white px-2 py-1 rounded flex-1 border">
                {inviteCode}
              </code>
              <Button
                size="sm"
                variant="ghost"
                onClick={copyInviteCode}
                className="gap-1"
              >
                {copied ? <Check size={14} /> : <Copy size={14} />}
              </Button>
            </div>
          </div>
        )}

        <div className="text-xs text-gray-600">
          <p className="font-medium mb-1">Participants ({participants.length}):</p>
          <div className="space-y-0.5">
            {participants.map((phone, i) => (
              <div key={i} className="text-gray-700">
                • {phone}
              </div>
            ))}
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
