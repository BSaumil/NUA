import React, { useState, useEffect, lazy, Suspense } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { Share2, Tag, Sparkles, Award, Mail, Star, Ticket, PartyPopper, Gift } from 'lucide-react';
import { useTheme } from '../contexts/ThemeContext';

/**
 * Marketing Hub — single umbrella that unifies every guest-facing growth
 * surface: Social Media, Promotions, Experiences, Club Members, Email
 * Marketing, Loyalty, Vouchers, Gift Cards and Events.
 *
 * Each sub-page is lazy-loaded so opening the hub only pays for the tab
 * you actually click. The tab argument is kept in the URL search-string
 * (`?tab=social`) so refresh + deep-link both work, and the old direct
 * routes (/social-media, /loyalty, ...) are redirected here by App.js.
 */
const TABS = [
  { key: 'social',      label: 'Social Media',   icon: Share2 },
  { key: 'promotions',  label: 'Promotions',     icon: Tag },
  { key: 'experiences', label: 'Experiences',    icon: PartyPopper },
  { key: 'club',        label: 'Club Members',   icon: Award },
  { key: 'email',       label: 'Email Marketing', icon: Mail },
  { key: 'loyalty',     label: 'Loyalty',        icon: Star },
  { key: 'vouchers',    label: 'Vouchers',       icon: Ticket },
  { key: 'gift-cards',  label: 'Gift Cards',     icon: Gift },
  { key: 'events',      label: 'Events',         icon: Sparkles },
];

// Lazy imports keep the initial bundle small.
const SocialMedia    = lazy(() => import('./SocialMedia'));
const Discounts      = lazy(() => import('./Discounts'));       // Discounts + Promos live here
const Experiences    = lazy(() => import('./BookingExperience'));
const Clubmember     = lazy(() => import('./Clubmember'));
const EmailMarketing = lazy(() => import('./EmailMarketing'));
const LoyaltyEvents  = lazy(() => import('./LoyaltyEvents'));
const Vouchers       = lazy(() => import('./v26/VoucherManager'));
const GiftCards      = lazy(() => import('./v25/GiftCards'));
const EventsManager  = lazy(() => import('./v26/EventsManager'));

export default function Marketing() {
  const { theme } = useTheme();
  const navigate = useNavigate();
  const location = useLocation();
  const params = new URLSearchParams(location.search);
  const initial = params.get('tab') || 'social';
  const [tab, setTab] = useState(TABS.some(t => t.key === initial) ? initial : 'social');

  useEffect(() => {
    // Keep URL in sync so refresh + share retains the selected tab.
    const p = new URLSearchParams(location.search);
    if (p.get('tab') !== tab) {
      p.set('tab', tab);
      navigate(`${location.pathname}?${p.toString()}`, { replace: true });
    }
  }, [tab]);

  const renderTab = () => {
    switch (tab) {
      case 'social':      return <SocialMedia />;
      case 'promotions':  return <Discounts />;
      case 'experiences': return <Experiences />;
      case 'club':        return <Clubmember />;
      case 'email':       return <EmailMarketing />;
      case 'loyalty':     return <LoyaltyEvents />;
      case 'vouchers':    return <Vouchers />;
      case 'gift-cards':  return <GiftCards />;
      case 'events':      return <EventsManager />;
      default:            return <SocialMedia />;
    }
  };

  return (
    <div className="space-y-6" data-testid="marketing-hub">
      <div>
        <h1 className="text-3xl font-bold flex items-center gap-2" style={{ color: theme.text }}>
          <Sparkles style={{ color: theme.primary }} /> Social Media &amp; Promotions
        </h1>
        <p className="text-sm text-gray-500 mt-1">
          One home for everything guest-facing: social posts, promotions, experiences, club, email, loyalty, vouchers, gift cards and events.
        </p>
      </div>

      {/* Tab strip */}
      <div className="border-b border-gray-200 overflow-x-auto" data-testid="marketing-tabs">
        <div className="flex gap-1 min-w-max">
          {TABS.map(t => {
            const Icon = t.icon;
            const active = tab === t.key;
            return (
              <button
                key={t.key}
                onClick={() => setTab(t.key)}
                data-testid={`marketing-tab-${t.key}`}
                className={`px-3 py-2 text-sm font-medium border-b-2 flex items-center gap-1.5 transition-colors whitespace-nowrap
                  ${active ? 'border-current' : 'border-transparent text-gray-500 hover:text-gray-900'}`}
                style={active ? { color: theme.primary } : {}}
              >
                <Icon size={14} /> {t.label}
              </button>
            );
          })}
        </div>
      </div>

      {/* Lazy-rendered sub-page */}
      <div data-testid={`marketing-panel-${tab}`}>
        <Suspense fallback={
          <div className="text-center py-12 text-gray-400 text-sm" data-testid="marketing-loading">
            Loading {TABS.find(t => t.key === tab)?.label}…
          </div>
        }>
          {renderTab()}
        </Suspense>
      </div>
    </div>
  );
}
