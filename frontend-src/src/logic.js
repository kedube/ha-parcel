// What the Packages panel works out from the data, kept apart from how it is drawn
// so it can be tested on its own. Nothing here touches the page.
import { daysBetween, shiftDay, toDate } from './format.js';

// Parcel's statuses, by the names the integration sends ("status"), in friendlier words.
// `icon` names an entry in icons.js; `key` is the CSS class.
export const STATUS = {
  delivered: { key: 'delivered', label: 'Delivered', icon: 'delivered', color: '--st-delivered', stage: 3 },
  stalled: { key: 'stalled', label: 'No recent updates', icon: 'stalled', color: '--st-muted', stage: 1, attn: true },
  in_transit: { key: 'transit', label: 'On the way', icon: 'inTransit', color: '--st-transit', stage: 1 },
  ready_for_pickup: { key: 'pickup', label: 'Ready for pickup', icon: 'pickup', color: '--st-pickup', stage: 2 },
  out_for_delivery: { key: 'out', label: 'Out for delivery', icon: 'outForDelivery', color: '--st-out', stage: 2 },
  not_found: { key: 'notfound', label: 'Not found yet', icon: 'notFound', color: '--st-muted', stage: 0 },
  failed_attempt: { key: 'failed', label: 'Missed delivery', icon: 'missed', color: '--st-failed', stage: 2, attn: true },
  exception: { key: 'exception', label: 'Delivery problem', icon: 'alert', color: '--st-attention', stage: 1, attn: true },
  label_created: { key: 'pre', label: 'Label created', icon: 'labelCreated', color: '--st-pre', stage: 0 },
};
export const PENDING = { key: 'pending', label: 'Waiting for first update', icon: 'waiting', color: '--st-muted', stage: -1 };
export const STAGES = [
  { label: 'Label created', icon: 'labelCreated' },
  { label: 'On the way', icon: 'inTransit' },
  { label: 'Out for delivery', icon: 'outForDelivery' },
  { label: 'Delivered', icon: 'home' },
];
export const PICKUP_STAGES = [STAGES[0], STAGES[1], { label: 'Ready for pickup', icon: 'pickup' }, { label: 'Picked up', icon: 'delivered' }];

export const GROUPS = {
  new: { title: 'Just added' },
  pickup: { title: 'Ready for pickup', sub: () => 'Waiting for you' },
  today: { title: 'Today', sub: (v) => v.fmt.longDate(v.today) },
  late: { title: 'Running late', sub: () => 'Expected earlier' },
  tomorrow: { title: 'Tomorrow', sub: (v) => v.fmt.longDate(shiftDay(v.today, 1)) },
  week: { title: 'Later this week' },
  later: { title: 'Coming later' },
  nodate: { title: 'No delivery date yet' },
  delivered: { title: 'Delivered', sub: () => 'Recently' },
};
export const ORDER = ['new', 'pickup', 'today', 'late', 'tomorrow', 'week', 'later', 'nodate', 'delivered'];
export const LATER_GROUPS = ['new', 'late', 'tomorrow', 'week', 'later', 'nodate'];

// What some carriers need besides the number, keyed by "extra" in Parcel's carrier list.
export const EXTRA = {
  1: { label: 'Postcode', type: 'text', placeholder: 'Destination postcode', autocomplete: 'postal-code' },
  2: { label: 'Email used for the order', type: 'email', placeholder: 'you@example.com', autocomplete: 'email', number: 'Order number' },
  3: { label: 'PIN', type: 'text', placeholder: 'PIN from the shipping notice', autocomplete: 'off' },
  4: { label: 'Phone number', type: 'tel', placeholder: 'Phone number on the order', autocomplete: 'tel' },
  5: { label: 'Country code and postcode', type: 'text', placeholder: 'US12345', autocomplete: 'off' },
};

export const DEFAULT_ICON = 'mdi:package-variant-closed';

// The timeline's hour labels, in pixels: how wide the timeline is taken to be until it
// has been measured, the least room between two labels' centers, and between a label's
// center and the "Now" label's.
const ROAD_WIDTH = 700;
const TICK_SPACING = 56;
const NOW_CLEARANCE = 34;

export const cap = (s) => (s ? s.charAt(0).toUpperCase() + s.slice(1) : s);
export const plural = (n, word) => `${n} ${word}${n === 1 ? '' : 's'}`;
/** A tracking number without spaces or dashes, in capitals, for comparing. */
export const cleanNumber = (s) => s.replace(/[\s-]/g, '').toUpperCase();

// ------------------------------------------------------------------ the data

/** One flat list of packages from what the integration sends for all accounts. */
export function normalizePayload(payload) {
  const items = [];
  for (const entry of payload?.entries || []) {
    const common = { entryId: entry.entry_id, entryTitle: entry.title, canDelete: entry.can_delete };
    for (const d of entry.deliveries || []) {
      items.push({
        ...common,
        uid: `${entry.entry_id}|${d.key}`,
        key: d.key,
        pending: false,
        description: d.description,
        trackingNumber: d.tracking_number,
        carrierCode: d.carrier_code,
        carrierName: d.carrier_name,
        carrierShort: d.carrier_short,
        status: d.status,
        etaStart: toDate(d.eta_start),
        etaEnd: toDate(d.eta_end),
        etaDate: d.eta_date || null,
        deliveredAt: toDate(d.delivered_at),
        events: (d.events || []).map((e) => ({
          text: e.event,
          when: toDate(e.date),
          whenText: e.date_text,
          location: e.location,
          additional: e.additional,
        })),
        icon: d.icon,
        iconSource: d.icon_source,
      });
    }
    for (const p of entry.pending || []) {
      items.push({
        ...common,
        uid: `${entry.entry_id}|${p.key}`,
        key: p.key,
        pending: true,
        description: p.description,
        trackingNumber: p.tracking_number,
        carrierCode: p.carrier_code,
        carrierName: p.carrier_name,
        carrierShort: p.carrier_short,
        status: null,
        etaStart: null,
        etaEnd: null,
        etaDate: null,
        deliveredAt: null,
        events: [],
        icon: p.icon,
        iconSource: p.icon_source,
        addedAt: toDate(p.added_at),
      });
    }
  }
  return items;
}

/** How a package's status is shown. A status this panel doesn't know reads as "not found yet". */
export const statusOf = (d) => (d.pending ? PENDING : STATUS[d.status] || STATUS.not_found);

/** The local day a package is expected, as 'YYYY-MM-DD', or null. */
export function dayKey(d, fmt) {
  if (d.etaDate) return d.etaDate;
  const when = d.etaStart || d.etaEnd;
  return when ? fmt.ymd(when) : null;
}

export function sortTime(d) {
  if (d.etaStart || d.etaEnd) return (d.etaStart || d.etaEnd).getTime();
  if (d.etaDate) return Date.parse(`${d.etaDate}T00:00:00`);
  return Infinity;
}

/** Which section of the page a package belongs in. */
export function groupOf(d, today, fmt) {
  if (d.pending) return 'new';
  const st = statusOf(d);
  if (st.key === 'delivered') return 'delivered';
  if (st.attn) return 'attention';
  if (st.key === 'pickup') return 'pickup';
  const day = dayKey(d, fmt);
  if (st.key === 'out' || day === today) return 'today';
  if (!day) return 'nodate';
  const diff = daysBetween(today, day);
  if (diff < 0) return 'late';
  if (diff === 1) return 'tomorrow';
  if (diff < 6) return 'week';
  return 'later';
}

/** Every package in its section, each section in the order it should be read. */
export function grouped(list, today, fmt) {
  const g = { attention: [] };
  for (const key of ORDER) g[key] = [];
  for (const d of list) g[groupOf(d, today, fmt)].push(d);
  for (const key of ORDER) {
    if (key === 'delivered') g[key].sort((a, b) => (b.deliveredAt?.getTime() || 0) - (a.deliveredAt?.getTime() || 0));
    else g[key].sort((a, b) => sortTime(a) - sortTime(b));
  }
  g.attention.sort((a, b) => sortTime(a) - sortTime(b));
  return g;
}

/** Whether a package matches what was typed in the search box. */
export function matches(d, query) {
  const q = query.trim().toLowerCase();
  if (!q) return true;
  const number = q.replace(/[\s-]/g, '');
  return (
    d.description.toLowerCase().includes(q) ||
    (number.length > 0 && d.trackingNumber.toLowerCase().includes(number)) ||
    (d.carrierName || '').toLowerCase().includes(q)
  );
}

/** The icon for a name, from the integration's rules ([{ re, icon }]). */
export function guessIcon(rules, text) {
  for (const rule of rules) if (rule.re.test(text || '')) return rule.icon;
  return DEFAULT_ICON;
}

/** The integration's icon rules as regular expressions; a rule that won't compile is skipped. */
export function compileRules(rules, flags = 'i') {
  return (rules || []).flatMap((rule) => {
    try {
      return [{ ...rule, re: new RegExp(rule.pattern, flags) }];
    } catch {
      return [];
    }
  });
}

// ------------------------------------------------------------------ words

export function dayName(fmt, ymd, today, long = true) {
  if (ymd === today) return 'today';
  if (ymd === shiftDay(today, 1)) return 'tomorrow';
  if (ymd === shiftDay(today, -1)) return 'yesterday';
  if (Math.abs(daysBetween(today, ymd)) < 6) return fmt.weekday(ymd, long ? 'long' : 'short');
  return fmt.shortDate(ymd);
}

export const whenText = (fmt, date, today) => `${cap(dayName(fmt, fmt.ymd(date), today, false))}, ${fmt.time(date)}`;

export function ago(date, now) {
  const m = Math.round((now - date) / 60000);
  if (m < 1) return 'just now';
  if (m < 60) return `${m} min ago`;
  const h = Math.round(m / 60);
  if (h < 24) return `${h} hr ago`;
  const days = Math.round(h / 24);
  return days === 1 ? 'yesterday' : `${days} days ago`;
}

export function countdown(target, now) {
  const m = Math.round((target - now) / 60000);
  if (m <= 0) return '';
  if (m < 50) return `In about ${Math.max(5, Math.round(m / 5) * 5)} minutes`;
  const h = Math.round(m / 60);
  return h === 1 ? 'In about an hour' : `In about ${h} hours`;
}

/** Why a package needs a look, and what to do about it. */
export function reasonOf(d, st, view) {
  const last = d.events[0];
  const carrier = d.carrierShort || d.carrierName;
  if (st.key === 'failed') {
    const nextDay = dayKey(d, view.fmt);
    const retry = nextDay
      ? `${carrier} will try again ${dayName(view.fmt, nextDay, view.today)}${d.etaStart && d.etaEnd ? `, ${view.fmt.window(d.etaStart, d.etaEnd)}` : ''}.`
      : `Check with ${carrier} about the next attempt.`;
    const why = last?.additional ? `${last.additional.split('. ')[0].replace(/\.$/, '')}. ` : '';
    return { title: 'Missed delivery', hint: `${why}${retry}` };
  }
  if (st.key === 'exception') return { title: last?.text || 'Delivery problem', hint: last?.additional || `Check with ${carrier} for details.` };
  if (st.key === 'stalled') return { title: 'No updates for a while', hint: last?.when ? `Last update ${ago(last.when, view.now)}.` : `Check with ${carrier} if it seems late.` };
  return { title: st.label, hint: '' };
}

/** The two short lines at the right of a card: when it arrives. */
export function badgeOf(d, st, view) {
  const { fmt, today } = view;
  if (d.pending) return { main: 'New', sub: 'just added' };
  if (st.key === 'delivered') {
    if (!d.deliveredAt) return { main: 'Delivered', sub: '' };
    const day = fmt.ymd(d.deliveredAt);
    return day === today
      ? { main: fmt.time(d.deliveredAt), sub: 'today' }
      : { main: cap(dayName(fmt, day, today, false)), sub: fmt.time(d.deliveredAt) };
  }
  if (st.key === 'pickup') return { main: 'Pick up', sub: 'ready now' };
  const day = dayKey(d, fmt);
  if (!day) return { main: '—', sub: 'no date yet' };
  const timeText = d.etaStart && d.etaEnd ? fmt.window(d.etaStart, d.etaEnd) : d.etaEnd ? `by ${fmt.time(d.etaEnd)}` : '';
  const diff = daysBetween(today, day);
  if (diff === 0) return { main: timeText || 'Today', sub: timeText ? 'today' : 'any time' };
  if (diff < 0) return { main: 'Late', sub: `was due ${fmt.monthDay(day)}` };
  if (diff === 1) return { main: 'Tomorrow', sub: timeText };
  if (diff < 6) return { main: fmt.weekday(day, 'short'), sub: fmt.monthDay(day) };
  return { main: fmt.monthDay(day), sub: fmt.weekday(day, 'short') };
}

/** The small grey line on a card: carrier, where it is, how long ago. */
export function metaOf(d, view) {
  const last = d.events[0];
  const parts = [d.carrierShort || d.carrierName];
  if (d.pending) parts.push('Parcel will check in a few minutes');
  else if (last?.location) parts.push(last.location);
  else if (last?.text && last.text.toLowerCase() !== statusOf(d).label.toLowerCase()) parts.push(last.text);
  if (!d.pending && last?.when) parts.push(ago(last.when, view.now));
  return parts.filter(Boolean).join(' · ');
}

/** The arrival card in the details sheet. */
export function etaFor(d, st, view) {
  const { fmt, today, now } = view;
  if (d.pending) return { main: 'Waiting for the first update', sub: 'Parcel will check with the carrier in a few minutes.' };
  if (st.key === 'delivered') {
    if (!d.deliveredAt) return { main: 'Delivered', sub: d.events[0]?.location || '' };
    const loc = d.events[0]?.location;
    return {
      main: `Delivered ${dayName(fmt, fmt.ymd(d.deliveredAt), today)}`,
      sub: `At ${fmt.time(d.deliveredAt)}${loc ? ` · ${loc}` : ''}`,
      note: d.events[0]?.additional || '',
    };
  }
  if (st.key === 'pickup') return { main: 'Ready for pickup', sub: d.events[0]?.location || '', note: d.events[0]?.additional || '' };
  if (st.attn) {
    const r = reasonOf(d, st, view);
    return { main: r.title, sub: r.hint };
  }
  const day = dayKey(d, fmt);
  if (!day) return { main: 'No delivery date yet', sub: 'The carrier hasn’t shared an estimate.' };
  let sub = '';
  if (d.etaStart && d.etaEnd) sub = cap(fmt.between(d.etaStart, d.etaEnd));
  else if (d.etaEnd) sub = `By ${fmt.time(d.etaEnd)}`;
  else if (st.key === 'pre') sub = 'The carrier doesn’t have the package yet.';
  else if (day === today) sub = 'No time window from the carrier.';
  let note = '';
  if (d.etaStart && fmt.ymd(d.etaStart) === today) {
    note = d.etaStart <= now && (!d.etaEnd || now <= d.etaEnd) ? 'Could arrive any minute' : countdown(d.etaStart, now);
  }
  const late = daysBetween(today, day) < 0;
  return {
    main: late ? `Expected ${dayName(fmt, day, today)}` : `Arriving ${dayName(fmt, day, today)}`,
    sub: late ? 'Running late. The carrier hasn’t updated the date.' : sub,
    note,
  };
}

// ------------------------------------------------------------------ today

/** What the card at the top says about today. */
export function heroModel(g, view) {
  const { fmt, today } = view;
  const todays = g.today;
  const deliveredToday = g.delivered.filter((d) => d.deliveredAt && fmt.ymd(d.deliveredAt) === today);
  const comingLater = LATER_GROUPS.reduce((n, key) => n + g[key].length, 0);

  let kind;
  let sub;
  let color = '--st-out';
  if (todays.length) {
    kind = 'today';
    const starts = todays.filter((d) => d.etaStart).map((d) => d.etaStart.getTime());
    const ends = todays.filter((d) => d.etaEnd || d.etaStart).map((d) => (d.etaEnd || d.etaStart).getTime());
    if (starts.length && ends.length) sub = `Expected ${fmt.between(new Date(Math.min(...starts)), new Date(Math.max(...ends)))}.`;
    else if (ends.length) sub = `Expected by ${fmt.time(new Date(Math.max(...ends)))}.`;
    else sub = 'The carriers haven’t shared delivery times yet.';
    if (deliveredToday.length) sub += ` ${deliveredToday.length} already delivered today.`;
  } else if (deliveredToday.length) {
    kind = 'delivered';
    color = '--st-delivered';
    sub = `${plural(deliveredToday.length, 'package')} delivered today.`;
  } else {
    kind = 'none';
    color = '--st-transit';
    const next = [...g.tomorrow, ...g.week, ...g.later][0];
    sub = next ? `Next up: ${next.description}, ${dayName(fmt, dayKey(next, fmt), today)}.` : 'Your packages are on their way.';
  }

  const stats = [];
  if (g.attention.length) stats.push({ n: g.attention.length, label: g.attention.length === 1 ? 'needs a look' : 'need a look', color: '--st-attention', target: 'sec-attention' });
  if (g.pickup.length) stats.push({ n: g.pickup.length, label: 'to pick up', color: '--st-pickup', target: 'sec-pickup' });
  if (comingLater) stats.push({ n: comingLater, label: 'coming later', color: '--st-transit', target: `sec-${LATER_GROUPS.find((k) => g[k].length)}` });
  if (deliveredToday.length) stats.push({ n: deliveredToday.length, label: 'delivered today', color: '--st-delivered', target: 'sec-delivered' });

  return { kind, count: todays.length, sub, color, stats, todays, deliveredToday };
}

/**
 * Today's deliveries as stops along a to-scale day: where each pin and time band sits
 * (in percent), which of up to three lanes keeps pins from colliding, and the hour marks.
 * view.roadWidth is the timeline's width in pixels, once measured. Returns null when
 * there is nothing to show.
 */
export function roadLayout(todays, deliveredToday, view) {
  const { fmt, today, now } = view;
  const nowH = fmt.hours(now);
  const clampH = (date) => {
    const key = fmt.ymd(date);
    if (key < today) return 0;
    if (key > today) return 24;
    return fmt.hours(date);
  };
  const pins = [];
  const anytime = [];
  for (const d of todays) {
    if (!d.etaStart && !d.etaEnd) {
      anytime.push(d);
      continue;
    }
    const end = d.etaEnd ? clampH(d.etaEnd) : Math.min(24, clampH(d.etaStart) + 2);
    let start = d.etaStart ? clampH(d.etaStart) : Math.min(nowH, end - 0.5);
    if (start > end - 0.25) start = Math.max(0, end - 0.5);
    const label = d.etaStart && d.etaEnd ? fmt.window(d.etaStart, d.etaEnd) : d.etaEnd ? `by ${fmt.time(d.etaEnd)}` : `from ${fmt.time(d.etaStart)}`;
    pins.push({ d, st: statusOf(d), start, end, at: (start + end) / 2, label, done: false });
  }
  for (const d of deliveredToday) {
    const h = fmt.hours(d.deliveredAt);
    pins.push({ d, st: statusOf(d), start: h, end: h, at: h, label: `delivered ${fmt.time(d.deliveredAt)}`, done: true });
  }
  if (!pins.length && !anytime.length) return null;

  // The day shown runs 8 to 8 unless a stop or the current time falls outside it.
  let from = 8;
  let to = 20;
  for (const p of pins) {
    from = Math.min(from, Math.floor(p.start));
    to = Math.max(to, Math.ceil(p.end));
  }
  from = Math.max(0, Math.min(from, Math.floor(nowH)));
  to = Math.min(24, Math.max(to, Math.ceil(nowH)));
  if ((to - from) % 2) {
    if (to < 24) to += 1;
    else from -= 1;
  }
  const pct = (h) => Math.min(100, Math.max(0, ((h - from) / (to - from)) * 100));

  pins.sort((x, y) => x.at - y.at);
  const laneEnds = [];
  const gap = (to - from) * 0.075;
  for (const p of pins) {
    let lane = laneEnds.findIndex((last) => p.at - last >= gap);
    if (lane === -1) lane = laneEnds.length < 3 ? laneEnds.length : laneEnds.indexOf(Math.min(...laneEnds));
    laneEnds[lane] = p.at;
    p.lane = lane;
    p.x = pct(p.at);
  }
  // A label every two hours, or fewer where the timeline is too narrow for that; any
  // label "Now" would overlap gives way to it.
  const hourPx = (view.roadWidth || ROAD_WIDTH) / (to - from);
  const step = [2, 4, 6, 8, 12].find((hours) => hours * hourPx >= TICK_SPACING) || 12;
  const ticks = [];
  for (let h = from; h <= to; h += 2) {
    const hidden = (h - from) % step !== 0 || Math.abs(h - nowH) * hourPx < NOW_CLEARANCE;
    ticks.push({ hour: h, left: pct(h), label: fmt.hourLabel(h), hidden });
  }
  return {
    pins,
    anytime,
    ticks,
    from,
    to,
    lanes: Math.max(1, laneEnds.length),
    nowLeft: pct(nowH),
    bands: pins.filter((p) => !p.done).map((p) => ({ left: pct(p.start), width: Math.max(pct(p.end) - pct(p.start), 1.5), color: p.st.color })),
  };
}

// ------------------------------------------------------------------ adding

/** Carrier codes whose number format matches, limited to carriers Parcel lists. */
export function detectCarriers(carriers, number) {
  if (!carriers) return [];
  const list = carriers.list;
  return [...new Set(carriers.detect.filter((r) => r.re.test(number)).map((r) => r.code))].filter((c) => list[c]);
}

/** What the carrier picker shows for what has been typed into it. */
export function carrierOptions(carriers, query, detected) {
  const list = carriers?.list || {};
  const q = query.trim().toLowerCase();
  const all = Object.entries(list).map(([code, c]) => ({ code, name: c.name }));
  if (!q) {
    const topCodes = [...detected, ...(carriers?.suggested || []).filter((c) => !detected.includes(c))].filter((c) => list[c]);
    const top = topCodes.map((code, i) => ({ code, name: list[code].name, heading: i === 0 ? (detected.length ? 'Suggested' : 'Common') : '' }));
    const rest = all.filter((o) => !topCodes.includes(o.code)).sort((a, b) => a.name.localeCompare(b.name));
    const shown = rest.slice(0, 40).map((o, i) => ({ ...o, heading: i === 0 ? 'All carriers' : '' }));
    return { items: [...top, ...shown], more: Math.max(0, rest.length - 40) };
  }
  const starts = (o) => (o.name.toLowerCase().startsWith(q) ? 0 : 1);
  const hits = all
    .filter((o) => o.name.toLowerCase().includes(q) || o.code.includes(q))
    .sort((a, b) => starts(a) - starts(b) || a.name.localeCompare(b.name));
  return { items: hits.slice(0, 50), more: Math.max(0, hits.length - 50) };
}

/** The elements inside a dialog that Tab should move between. */
export const FOCUSABLE = 'button:not([disabled]), [href], input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])';

/**
 * Keeps Tab inside a dialog. Returns the element to move focus to when Tab would
 * otherwise leave (or when focus is already outside), and null when the browser's
 * own next step stays inside.
 */
export function trapFocus(focusables, active, backwards) {
  if (!focusables.length) return null;
  const first = focusables[0];
  const last = focusables[focusables.length - 1];
  if (!focusables.includes(active)) return backwards ? last : first;
  if (backwards && active === first) return last;
  if (!backwards && active === last) return first;
  return null;
}
