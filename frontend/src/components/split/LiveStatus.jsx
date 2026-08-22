import React from 'react';
import { Activity, AlertCircle, CheckCircle2, Clock } from 'lucide-react';
import { Badge } from '../ui/badge';

export function LiveStatus({ split, connected, claimedByOthers }) {
  if (!connected) {
    return (
      <div className="p-3 rounded-lg bg-amber-50 border border-amber-200 flex items-start gap-2">
        <AlertCircle size={16} className="mt-0.5 text-amber-600 flex-shrink-0" />
        <div className="text-xs text-amber-700">
          <p className="font-medium">Reconnecting...</p>
          <p>Updates may be delayed</p>
        </div>
      </div>
    );
  }

  // Count statuses
  const openCount = split?.lines?.filter(l => l.status === 'open').length || 0;
  const claimedCount = split?.lines?.filter(l => l.status === 'claimed').length || 0;
  const paidCount = split?.lines?.filter(l => l.status === 'paid').length || 0;

  const recentClaimsByOthers = claimedByOthers?.slice(-2) || [];

  return (
    <div className="space-y-2">
      <div className="flex items-center gap-2 text-xs text-green-700">
        <Activity size={14} className="animate-pulse" />
        <span className="font-medium">Live updates enabled</span>
      </div>

      {/* Item status summary */}
      <div className="grid grid-cols-3 gap-2">
        <div className="text-center p-2 rounded bg-blue-50 border border-blue-200">
          <div className="text-lg font-bold text-blue-900">{openCount}</div>
          <div className="text-xs text-blue-700">Available</div>
        </div>
        <div className="text-center p-2 rounded bg-yellow-50 border border-yellow-200">
          <div className="text-lg font-bold text-yellow-900">{claimedCount}</div>
          <div className="text-xs text-yellow-700">Claimed</div>
        </div>
        <div className="text-center p-2 rounded bg-green-50 border border-green-200">
          <div className="text-lg font-bold text-green-900">{paidCount}</div>
          <div className="text-xs text-green-700">Paid</div>
        </div>
      </div>

      {/* Recent actions by other guests */}
      {recentClaimsByOthers.length > 0 && (
        <div className="text-xs bg-gray-50 p-2 rounded border border-gray-200">
          <p className="font-medium text-gray-600 mb-1">Others just claimed:</p>
          <div className="space-y-1">
            {recentClaimsByOthers.map((claim, i) => (
              <div key={i} className="text-gray-600 flex items-center gap-1">
                <CheckCircle2 size={12} className="text-green-600" />
                {claim.productName}
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
