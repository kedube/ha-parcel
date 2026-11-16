// Dates and times in the person's Home Assistant language, clock and time zone.

const DAY_MS = 86400000;

/** 'YYYY-MM-DD' plus n days. */
export const shiftDay = (ymd, n) => {
  const d = new Date(`${ymd}T12:00:00Z`);
  d.setUTCDate(d.getUTCDate() + n);
  return d.toISOString().slice(0, 10);
};

/** Whole days from one 'YYYY-MM-DD' to another. */
export const daysBetween = (a, b) => Math.round((Date.parse(`${b}T12:00:00Z`) - Date.parse(`${a}T12:00:00Z`)) / DAY_MS);

export const toDate = (value) => {
  if (!value) return null;
  const d = new Date(value);
  return Number.isNaN(d.getTime()) ? null : d;
};

export function makeFormat(hass) {
  const language = hass?.locale?.language || hass?.language || navigator.language || 'en';
  const clock = hass?.locale?.time_format;
  const hour12 = clock === '12' ? true : clock === '24' ? false : undefined;
  const timeZone = hass?.locale?.time_zone === 'server' ? hass?.config?.time_zone : undefined;
  const cache = new Map();
  const formatter = (key, options, zone = timeZone) => {
    const id = `${key}|${zone || ''}`;
    if (!cache.has(id)) {
      try {
        cache.set(id, new Intl.DateTimeFormat(language, zone ? { ...options, timeZone: zone } : options));
      } catch {
        cache.set(id, new Intl.DateTimeFormat('en', zone ? { ...options, timeZone: zone } : options));
      }
    }
    return cache.get(id);
  };
  const parts = (date) => {
    const out = {};
    for (const part of formatter('parts', {
      year: 'numeric', month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit', hourCycle: 'h23',
    }).formatToParts(date)) out[part.type] = part.value;
    return out;
  };
  // Date-only values ('YYYY-MM-DD') are formatted at noon UTC so no zone can shift the day.
  const dayDate = (ymd) => new Date(`${ymd}T12:00:00Z`);

  const api = {
    /** Local calendar day of a moment, as 'YYYY-MM-DD'. */
    ymd(date) {
      const p = parts(date);
      return `${p.year}-${p.month}-${p.day}`;
    },
    /** Hours since local midnight, e.g. 13.5 for 1:30 PM. */
    hours(date) {
      const p = parts(date);
      return (Number(p.hour) % 24) + Number(p.minute) / 60;
    },
    /** "1 PM", "1:30 PM" or "13:00", following the person's clock setting. */
    time(date) {
      const p = parts(date);
      const whole = p.minute === '00';
      const usesDayPeriod = formatter('probe', { hour: 'numeric', hour12 })
        .formatToParts(date)
        .some((part) => part.type === 'dayPeriod');
      if (whole && usesDayPeriod) return formatter('hour', { hour: 'numeric', hour12 }).format(date);
      return formatter('time', { hour: 'numeric', minute: '2-digit', hour12 }).format(date);
    },
    /** "1–4 PM", "11 AM–2 PM" or "13:00–16:00". */
    window(start, end) {
      const a = api.time(start);
      const b = api.time(end);
      const suffix = (s) => (s.match(/\s?[^\d\s:.]+$/) || [''])[0];
      const sa = suffix(a);
      if (sa && sa === suffix(b)) return `${a.slice(0, -sa.length)}–${b}`;
      return `${a}–${b}`;
    },
    between(start, end) {
      const a = api.time(start);
      const b = api.time(end);
      const suffix = (s) => (s.match(/\s?[^\d\s:.]+$/) || [''])[0];
      const sa = suffix(a);
      if (sa && sa === suffix(b)) return `between ${a.slice(0, -sa.length)} and ${b}`;
      return `between ${a} and ${b}`;
    },
    weekday: (ymd, style = 'long') => formatter(`wd-${style}`, { weekday: style }, 'UTC').format(dayDate(ymd)),
    monthDay: (ymd) => formatter('md', { month: 'short', day: 'numeric' }, 'UTC').format(dayDate(ymd)),
    longDate: (ymd) => formatter('ld', { weekday: 'long', month: 'long', day: 'numeric' }, 'UTC').format(dayDate(ymd)),
    shortDate: (ymd) => formatter('sd', { weekday: 'short', month: 'short', day: 'numeric' }, 'UTC').format(dayDate(ymd)),
    monthShort: (ymd) => formatter('mon', { month: 'short' }, 'UTC').format(dayDate(ymd)),
    dayNumber: (ymd) => Number(ymd.slice(8, 10)),
    /** Axis label for an hour of the day: "8 AM", "Noon"-free and locale-aware. */
    hourLabel: (h) => formatter('hl', { hour: 'numeric', hour12 }, 'UTC').format(new Date(Date.UTC(2000, 0, 1, h % 24))),
  };
  return api;
}
