// Mirrors backend/utils/au_payroll.py's effective_hourly_rate() exactly —
// payRate is stored in whatever unit salaryType names, and every hours×rate
// preview on the client needs the same conversion the server payroll runs
// use, or a $75k/year salary would render as "$75,000/hr" in a shift-cost
// preview while the actual pay run correctly shows ~$38/hr.
export const STANDARD_WEEKLY_HOURS = 38;

export function effectiveHourlyRate(payRate, salaryType) {
  const rate = Number(payRate) || 0;
  const type = (salaryType || 'hourly').toLowerCase();
  if (type === 'weekly') return rate / STANDARD_WEEKLY_HOURS;
  if (type === 'annually' || type === 'annual' || type === 'yearly') return rate / 52 / STANDARD_WEEKLY_HOURS;
  if (type === 'daily') return rate / (STANDARD_WEEKLY_HOURS / 5); // legacy option
  return rate;
}

const SUFFIX = { hourly: '/hr', weekly: '/wk', annually: '/yr', annual: '/yr', yearly: '/yr', daily: '/day' };
export function salaryTypeSuffix(salaryType) {
  return SUFFIX[(salaryType || 'hourly').toLowerCase()] || '/hr';
}
