export const FMT = (n) => (n ?? 0).toLocaleString('en-AU', { style: 'currency', currency: 'AUD', minimumFractionDigits: 2 });
export const today = () => new Date().toISOString().slice(0, 10);
export const fyStart = () => {
  const t = new Date();
  const y = t.getMonth() >= 6 ? t.getFullYear() : t.getFullYear() - 1;
  return `${y}-07-01`;
};
