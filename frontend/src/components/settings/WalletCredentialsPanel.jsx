import React, { useEffect, useState } from 'react';
import { Card, CardContent } from '../ui/card';
import { Button } from '../ui/button';
import { Input } from '../ui/input';
import { Badge } from '../ui/badge';
import { Textarea } from '../ui/textarea';
import { finalizeAPI } from '../../services/api';
import { toast } from 'sonner';
import { Smartphone, ExternalLink, ShieldCheck, ShieldAlert, KeyRound, Eye, EyeOff } from 'lucide-react';

/** Owner-only panel to paste Apple / Google Wallet credentials.
 *  Never displays existing secrets — only shows "configured" state. */
export default function WalletCredentialsPanel({ theme }) {
  const [status, setStatus] = useState(null);
  const [apple, setApple] = useState({ passTypeIdentifier: '', teamId: '', passTypeCertPem: '', passTypeKeyPem: '', appleWwdrCertPem: '' });
  const [google, setGoogle] = useState({ issuerId: '', classId: '', issuerEmail: '', serviceAccountKey: '' });
  const [showApple, setShowApple] = useState(false);
  const [showGoogle, setShowGoogle] = useState(false);
  const [saving, setSaving] = useState(false);

  const load = async () => {
    try {
      const r = await finalizeAPI.walletCredentialsStatus();
      setStatus(r.data);
      setApple(a => ({ ...a,
        passTypeIdentifier: r.data.apple?.passTypeId || '',
        teamId: r.data.apple?.teamId || '',
      }));
      setGoogle(g => ({ ...g,
        issuerId: r.data.google?.issuerId || '',
        classId: r.data.google?.classId || '',
      }));
    } catch { /* silent */ }
  };
  useEffect(() => { load(); }, []);

  const save = async () => {
    // Only send fields the user actually filled — never wipe secrets with blanks.
    const applePayload = Object.fromEntries(Object.entries(apple).filter(([, v]) => v && v.trim()));
    const googlePayload = Object.fromEntries(Object.entries(google).filter(([, v]) => v && v.trim()));
    if (!Object.keys(applePayload).length && !Object.keys(googlePayload).length) {
      toast.error('Nothing to save — paste at least one credential');
      return;
    }
    setSaving(true);
    try {
      await finalizeAPI.walletCredentialsSave({ apple: applePayload, google: googlePayload });
      toast.success('Wallet credentials saved & applied');
      setApple(a => ({ ...a, passTypeCertPem: '', passTypeKeyPem: '', appleWwdrCertPem: '' }));
      setGoogle(g => ({ ...g, serviceAccountKey: '' }));
      load();
    } catch (e) { toast.error(e?.response?.data?.detail || 'Save failed'); }
    finally { setSaving(false); }
  };

  const StatusBadge = ({ ready }) => ready ? (
    <Badge className="bg-emerald-100 text-emerald-700 border-0">
      <ShieldCheck size={11} className="mr-1" /> Production ready
    </Badge>
  ) : (
    <Badge className="bg-amber-100 text-amber-700 border-0">
      <ShieldAlert size={11} className="mr-1" /> Preview mode
    </Badge>
  );

  return (
    <Card className="border-0 shadow-sm" data-testid="wallet-credentials-panel">
      <CardContent className="p-5 space-y-5">
        <div>
          <h3 className="font-semibold flex items-center gap-2">
            <KeyRound size={16} style={{ color: theme?.primary || '#f97316' }} />
            Wallet Credentials
          </h3>
          <p className="text-xs text-gray-500 mt-1">
            Paste Apple Pass Type ID certs + Google Wallet service account here to switch loyalty
            passes from preview to production-signed. Secrets are stored encrypted, never re-displayed.
          </p>
        </div>

        {/* Apple */}
        <div className="border rounded-lg p-4 space-y-2.5" data-testid="apple-wallet-section">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Smartphone size={14} className="text-gray-700" />
              <p className="font-medium">Apple Wallet</p>
            </div>
            <StatusBadge ready={status?.apple?.envReady} />
          </div>
          <div className="grid grid-cols-2 gap-2">
            <Input placeholder="Pass Type ID (e.g. pass.com.nua.loyalty)"
              value={apple.passTypeIdentifier}
              onChange={e => setApple({ ...apple, passTypeIdentifier: e.target.value })}
              data-testid="apple-pass-type-id" />
            <Input placeholder="Apple Team ID"
              value={apple.teamId}
              onChange={e => setApple({ ...apple, teamId: e.target.value })}
              data-testid="apple-team-id" />
          </div>
          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <span className="text-xs text-gray-500">Pass Type Certificate (PEM)</span>
              <Button size="sm" variant="ghost" onClick={() => setShowApple(!showApple)} data-testid="apple-toggle-visibility">
                {showApple ? <EyeOff size={12} /> : <Eye size={12} />}
              </Button>
            </div>
            <Textarea rows={showApple ? 4 : 2} className="font-mono text-[10px]"
              placeholder="-----BEGIN CERTIFICATE-----&#10;...&#10;-----END CERTIFICATE-----"
              value={apple.passTypeCertPem}
              onChange={e => setApple({ ...apple, passTypeCertPem: e.target.value })}
              data-testid="apple-cert-pem" />
            <Textarea rows={showApple ? 4 : 2} className="font-mono text-[10px]"
              placeholder="-----BEGIN RSA PRIVATE KEY-----&#10;...&#10;-----END RSA PRIVATE KEY-----"
              value={apple.passTypeKeyPem}
              onChange={e => setApple({ ...apple, passTypeKeyPem: e.target.value })}
              data-testid="apple-key-pem" />
            <Textarea rows={showApple ? 4 : 2} className="font-mono text-[10px]"
              placeholder="Apple WWDR Intermediate Certificate (PEM)"
              value={apple.appleWwdrCertPem}
              onChange={e => setApple({ ...apple, appleWwdrCertPem: e.target.value })}
              data-testid="apple-wwdr-pem" />
          </div>
          <p className="text-[10px] text-gray-500 flex items-center gap-1">
            <ExternalLink size={10} /> Get certs at
            <a href="https://developer.apple.com/account/resources/identifiers/list/passTypeId" target="_blank" rel="noreferrer" className="text-blue-600 hover:underline">
              developer.apple.com → Pass Type IDs
            </a>
          </p>
        </div>

        {/* Google */}
        <div className="border rounded-lg p-4 space-y-2.5" data-testid="google-wallet-section">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <ExternalLink size={14} style={{ color: '#4285F4' }} />
              <p className="font-medium">Google Wallet</p>
            </div>
            <StatusBadge ready={status?.google?.envReady} />
          </div>
          <div className="grid grid-cols-2 gap-2">
            <Input placeholder="Issuer ID (numeric)"
              value={google.issuerId}
              onChange={e => setGoogle({ ...google, issuerId: e.target.value })}
              data-testid="google-issuer-id" />
            <Input placeholder="Loyalty Class ID (issuer.class)"
              value={google.classId}
              onChange={e => setGoogle({ ...google, classId: e.target.value })}
              data-testid="google-class-id" />
          </div>
          <Input placeholder="Service account email"
            value={google.issuerEmail}
            onChange={e => setGoogle({ ...google, issuerEmail: e.target.value })}
            data-testid="google-issuer-email" />
          <div className="flex items-center justify-between">
            <span className="text-xs text-gray-500">Service Account JSON (raw or base64)</span>
            <Button size="sm" variant="ghost" onClick={() => setShowGoogle(!showGoogle)} data-testid="google-toggle-visibility">
              {showGoogle ? <EyeOff size={12} /> : <Eye size={12} />}
            </Button>
          </div>
          <Textarea rows={showGoogle ? 6 : 3} className="font-mono text-[10px]"
            placeholder='{"type":"service_account","project_id":"...","private_key":"..."}'
            value={google.serviceAccountKey}
            onChange={e => setGoogle({ ...google, serviceAccountKey: e.target.value })}
            data-testid="google-sa-key" />
          <p className="text-[10px] text-gray-500 flex items-center gap-1">
            <ExternalLink size={10} /> Get keys at
            <a href="https://pay.google.com/business/console" target="_blank" rel="noreferrer" className="text-blue-600 hover:underline">
              pay.google.com/business/console
            </a>
          </p>
        </div>

        <Button onClick={save} disabled={saving} className="w-full text-white"
          style={{ background: theme?.primary || '#f97316' }} data-testid="save-wallet-creds-btn">
          {saving ? 'Saving…' : 'Save & apply credentials'}
        </Button>
      </CardContent>
    </Card>
  );
}
