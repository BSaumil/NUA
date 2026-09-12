// Mirrors services/booking_rules_engine.match_tier() on the backend.
//
// Used on both the customer (BookingPortal.jsx) and staff (Reservations.jsx)
// booking forms to show a large-booking requirement proactively as the
// party size is chosen — never as the actual gate. The backend re-validates
// on every POST /public/book and POST /reservations and is what a caller
// genuinely cannot get past; if this ever disagrees with the server (rules
// changed mid-session, a stale fetch), the resulting 409 still catches it.
export function matchTier(tiers, partySize) {
  const ordered = [...(tiers || [])].sort((a, b) => (a.minGuests || 1) - (b.minGuests || 1));
  for (const t of ordered) {
    const lo = t.minGuests || 1;
    const hi = (t.maxGuests === null || t.maxGuests === undefined || t.maxGuests === '') ? null : t.maxGuests;
    if (partySize >= lo && (hi === null || partySize <= hi)) return t;
  }
  return null;
}
