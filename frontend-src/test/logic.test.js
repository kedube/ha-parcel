// What the panel works out from the data: sections, wording, the day's timeline, the add form.
import assert from 'node:assert/strict';
import { test } from 'node:test';

import { makeFormat } from '../src/format.js';
import {
  DEFAULT_ICON,
  ORDER,
  STATUS,
  ago,
  badgeOf,
  carrierOptions,
  cleanNumber,
  compileRules,
  countdown,
  dayName,
  detectCarriers,
  etaFor,
  groupOf,
  grouped,
  guessIcon,
  heroModel,
  matches,
  metaOf,
  normalizePayload,
  reasonOf,
  roadLayout,
  statusOf,
  trapFocus,
} from '../src/logic.js';

const fmt = makeFormat({
  locale: { language: 'en', time_format: '12', time_zone: 'server' },
  config: { time_zone: 'America/New_York' },
});
// Monday 16 November 2026, 9 in the morning in New York.
const now = new Date('2026-11-16T14:00:00Z');
const today = '2026-11-16';
const view = { fmt, today, now };
const at = (iso) => new Date(iso);

let serial = 0;
/** A package as the panel holds it, with only what a test cares about filled in. */
function pkg(overrides = {}) {
  serial += 1;
  return {
    uid: `e|k${serial}`,
    key: `k${serial}`,
    pending: false,
    description: `Package ${serial}`,
    trackingNumber: `1Z999AA1012345${String(serial).padStart(4, '0')}`,
    carrierCode: 'ups',
    carrierName: 'UPS',
    carrierShort: 'UPS',
    status: 'in_transit',
    etaStart: null,
    etaEnd: null,
    etaDate: null,
    deliveredAt: null,
    events: [],
    icon: DEFAULT_ICON,
    iconSource: 'name',
    ...overrides,
  };
}

test('every status has words, and one the panel does not know reads as not found yet', () => {
  assert.equal(statusOf(pkg({ status: 'out_for_delivery' })).label, 'Out for delivery');
  assert.equal(statusOf(pkg({ status: 'something_new' })), STATUS.not_found);
  assert.equal(statusOf(pkg({ status: null })), STATUS.not_found);
  assert.equal(statusOf(pkg({ pending: true, status: null })).key, 'pending');
  for (const entry of Object.values(STATUS)) assert.ok(entry.label && entry.icon && entry.color.startsWith('--st-'));
});

test('accounts are flattened into one list', () => {
  const items = normalizePayload({
    entries: [
      {
        entry_id: 'home',
        title: 'Home',
        can_delete: true,
        deliveries: [
          {
            key: 'ups:1',
            description: 'Lamp',
            tracking_number: '1',
            carrier_code: 'ups',
            status: 'in_transit',
            eta_start: '2026-11-16T13:00:00-05:00',
            eta_date: null,
            delivered_at: null,
            events: [{ event: 'Departed', date: '2026-11-15T08:00:00-05:00', location: 'Portland' }],
            icon: 'mdi:desk-lamp',
            icon_source: 'name',
          },
        ],
        pending: [{ key: 'ups:2', description: 'Shoes', tracking_number: '2', carrier_code: 'ups', added_at: '2026-11-16T08:00:00-05:00', icon: 'mdi:shoe-sneaker' }],
      },
      { entry_id: 'work', title: 'Work', can_delete: false, deliveries: [], pending: [] },
    ],
  });
  assert.deepEqual(items.map((d) => [d.uid, d.pending, d.entryTitle, d.canDelete]), [
    ['home|ups:1', false, 'Home', true],
    ['home|ups:2', true, 'Home', true],
  ]);
  assert.equal(items[0].etaStart.toISOString(), '2026-11-16T18:00:00.000Z');
  assert.equal(items[0].events[0].text, 'Departed');
  assert.equal(items[1].status, null);
  assert.deepEqual(normalizePayload(null), []);
});

test('each package lands in the right section', () => {
  const cases = [
    [pkg({ pending: true, status: null }), 'new'],
    [pkg({ status: 'delivered' }), 'delivered'],
    [pkg({ status: 'failed_attempt', etaDate: today }), 'attention'],
    [pkg({ status: 'exception' }), 'attention'],
    [pkg({ status: 'stalled' }), 'attention'],
    [pkg({ status: 'ready_for_pickup' }), 'pickup'],
    [pkg({ status: 'out_for_delivery' }), 'today'],
    [pkg({ etaDate: today }), 'today'],
    [pkg({ etaStart: at('2026-11-16T18:00:00Z') }), 'today'],
    [pkg({ etaDate: '2026-11-15' }), 'late'],
    [pkg({ etaDate: '2026-11-17' }), 'tomorrow'],
    [pkg({ etaDate: '2026-11-20' }), 'week'],
    [pkg({ etaDate: '2026-11-30' }), 'later'],
    [pkg({ status: 'label_created' }), 'nodate'],
    // 11 PM in New York on the 16th is already the 17th in UTC; it is still today here.
    [pkg({ etaStart: at('2026-11-17T04:00:00Z') }), 'today'],
  ];
  for (const [item, group] of cases) assert.equal(groupOf(item, today, fmt), group, item.description);
});

test('sections are sorted by arrival, delivered ones newest first', () => {
  const late = pkg({ description: 'Late window', etaStart: at('2026-11-16T22:00:00Z') });
  const early = pkg({ description: 'Early window', etaStart: at('2026-11-16T15:00:00Z') });
  const anyTime = pkg({ description: 'Any time', etaDate: today });
  const older = pkg({ description: 'Older', status: 'delivered', deliveredAt: at('2026-11-14T15:00:00Z') });
  const newer = pkg({ description: 'Newer', status: 'delivered', deliveredAt: at('2026-11-16T12:00:00Z') });
  const g = grouped([late, older, anyTime, newer, early], today, fmt);
  assert.deepEqual(g.today.map((d) => d.description), ['Any time', 'Early window', 'Late window']);
  assert.deepEqual(g.delivered.map((d) => d.description), ['Newer', 'Older']);
  assert.deepEqual(Object.keys(g).sort(), ['attention', ...ORDER].sort());
});

test('search looks at the name, the number and the carrier', () => {
  const lamp = pkg({ description: 'Desk lamp', trackingNumber: '1Z999AA10123456784', carrierName: 'UPS' });
  assert.ok(matches(lamp, ''));
  assert.ok(matches(lamp, '  LAMP '));
  assert.ok(matches(lamp, '1z 999-aa1'));
  assert.ok(matches(lamp, 'ups'));
  assert.ok(!matches(lamp, 'fedex'));
  // Punctuation alone is not a tracking number.
  assert.ok(!matches(lamp, '-'));
  assert.ok(!matches(lamp, ' - - '));
});

test('the card says when in a few words', () => {
  const st = (d) => statusOf(d);
  const say = (d) => badgeOf(d, st(d), view);
  assert.deepEqual(say(pkg({ pending: true })), { main: 'New', sub: 'just added' });
  assert.deepEqual(say(pkg({ etaStart: at('2026-11-16T18:00:00Z'), etaEnd: at('2026-11-16T21:00:00Z') })), { main: '1–4 PM', sub: 'today' });
  assert.deepEqual(say(pkg({ etaDate: today })), { main: 'Today', sub: 'any time' });
  assert.deepEqual(say(pkg({ etaDate: '2026-11-17' })), { main: 'Tomorrow', sub: '' });
  assert.deepEqual(say(pkg({ etaEnd: at('2026-11-18T01:00:00Z') })), { main: 'Tomorrow', sub: 'by 8 PM' });
  assert.deepEqual(say(pkg({ etaDate: '2026-11-19' })), { main: 'Thu', sub: 'Nov 19' });
  assert.deepEqual(say(pkg({ etaDate: '2026-11-30' })), { main: 'Nov 30', sub: 'Mon' });
  assert.deepEqual(say(pkg({ etaDate: '2026-11-13' })), { main: 'Late', sub: 'was due Nov 13' });
  assert.deepEqual(say(pkg({})), { main: '—', sub: 'no date yet' });
  assert.deepEqual(say(pkg({ status: 'ready_for_pickup' })), { main: 'Pick up', sub: 'ready now' });
  assert.deepEqual(say(pkg({ status: 'delivered', deliveredAt: at('2026-11-16T13:02:00Z') })), { main: '8:02 AM', sub: 'today' });
  assert.deepEqual(say(pkg({ status: 'delivered', deliveredAt: at('2026-11-15T20:30:00Z') })), { main: 'Yesterday', sub: '3:30 PM' });
  assert.deepEqual(say(pkg({ status: 'delivered' })), { main: 'Delivered', sub: '' });
});

test('the small line under a card name', () => {
  const scanned = pkg({ events: [{ text: 'Arrived at facility', when: at('2026-11-16T12:00:00Z'), location: 'Portland, OR' }] });
  assert.equal(metaOf(scanned, view), 'UPS · Portland, OR · 2 hr ago');
  const noPlace = pkg({ events: [{ text: 'Label printed', when: null }] });
  assert.equal(metaOf(noPlace, view), 'UPS · Label printed');
  // The carrier's text isn't repeated when it only says what the status already does.
  assert.equal(metaOf(pkg({ events: [{ text: 'on the way', when: null }] }), view), 'UPS');
  assert.equal(metaOf(pkg({ pending: true, carrierShort: '', carrierName: 'UPS' }), view), 'UPS · Parcel will check in a few minutes');
});

test('what needs a look, and what to do about it', () => {
  const missed = pkg({
    status: 'failed_attempt',
    etaDate: '2026-11-17',
    events: [{ text: 'Delivery attempted', additional: 'Nobody was home. A notice was left.' }],
  });
  assert.deepEqual(reasonOf(missed, statusOf(missed), view), { title: 'Missed delivery', hint: 'Nobody was home. UPS will try again tomorrow.' });
  const noRetry = pkg({ status: 'failed_attempt' });
  assert.equal(reasonOf(noRetry, statusOf(noRetry), view).hint, 'Check with UPS about the next attempt.');
  const damaged = pkg({ status: 'exception', events: [{ text: 'Package damaged' }] });
  assert.deepEqual(reasonOf(damaged, statusOf(damaged), view), { title: 'Package damaged', hint: 'Check with UPS for details.' });
  const quiet = pkg({ status: 'stalled', events: [{ text: 'Departed', when: at('2026-11-12T14:00:00Z') }] });
  assert.deepEqual(reasonOf(quiet, statusOf(quiet), view), { title: 'No updates for a while', hint: 'Last update 4 days ago.' });
});

test('the arrival card in the details', () => {
  const say = (d) => etaFor(d, statusOf(d), view);
  assert.equal(say(pkg({ pending: true })).main, 'Waiting for the first update');
  assert.deepEqual(say(pkg({ etaStart: at('2026-11-16T18:00:00Z'), etaEnd: at('2026-11-16T21:00:00Z') })), {
    main: 'Arriving today',
    sub: 'Between 1 and 4 PM',
    note: 'In about 4 hours',
  });
  assert.equal(say(pkg({ etaStart: at('2026-11-16T13:00:00Z'), etaEnd: at('2026-11-16T16:00:00Z') })).note, 'Could arrive any minute');
  assert.deepEqual(say(pkg({ etaDate: today })), { main: 'Arriving today', sub: 'No time window from the carrier.', note: '' });
  assert.deepEqual(say(pkg({ etaDate: '2026-11-13' })), {
    main: 'Expected Friday',
    sub: 'Running late. The carrier hasn’t updated the date.',
    note: '',
  });
  assert.equal(say(pkg({})).main, 'No delivery date yet');
  assert.equal(say(pkg({ status: 'label_created', etaDate: '2026-11-18' })).sub, 'The carrier doesn’t have the package yet.');
  const delivered = pkg({ status: 'delivered', deliveredAt: at('2026-11-16T13:02:00Z'), events: [{ text: 'Delivered', location: 'Front door' }] });
  assert.deepEqual(say(delivered), { main: 'Delivered today', sub: 'At 8:02 AM · Front door', note: '' });
  assert.equal(say(pkg({ status: 'failed_attempt' })).main, 'Missed delivery');
});

test('the top card sums up today', () => {
  const timed = pkg({ etaStart: at('2026-11-16T18:00:00Z'), etaEnd: at('2026-11-16T21:00:00Z') });
  const anyTime = pkg({ etaDate: today });
  const done = pkg({ status: 'delivered', deliveredAt: at('2026-11-16T13:00:00Z') });
  const tomorrow = pkg({ description: 'Shoes', etaDate: '2026-11-17' });
  const missed = pkg({ status: 'failed_attempt' });

  const busy = heroModel(grouped([timed, anyTime, done, tomorrow, missed], today, fmt), view);
  assert.equal(busy.kind, 'today');
  assert.equal(busy.count, 2);
  assert.equal(busy.sub, 'Expected between 1 and 4 PM. 1 already delivered today.');
  assert.deepEqual(busy.stats.map((s) => [s.n, s.label, s.target]), [
    [1, 'needs a look', 'sec-attention'],
    [1, 'coming later', 'sec-tomorrow'],
    [1, 'delivered today', 'sec-delivered'],
  ]);

  const allIn = heroModel(grouped([done], today, fmt), view);
  assert.deepEqual([allIn.kind, allIn.sub, allIn.color], ['delivered', '1 package delivered today.', '--st-delivered']);

  const quiet = heroModel(grouped([tomorrow], today, fmt), view);
  assert.deepEqual([quiet.kind, quiet.sub], ['none', 'Next up: Shoes, tomorrow.']);
  assert.equal(heroModel(grouped([pkg({})], today, fmt), view).sub, 'Your packages are on their way.');
  assert.equal(heroModel(grouped([anyTime], today, fmt), view).sub, 'The carriers haven’t shared delivery times yet.');
});

test('the day is drawn to scale, and close stops get lanes of their own', () => {
  assert.equal(roadLayout([], [], view), null);

  const first = pkg({ etaStart: at('2026-11-16T18:00:00Z'), etaEnd: at('2026-11-16T21:00:00Z') }); // 1 to 4 PM
  const second = pkg({ etaStart: at('2026-11-16T18:30:00Z'), etaEnd: at('2026-11-16T21:30:00Z') }); // 1:30 to 4:30
  const anyTime = pkg({ etaDate: today });
  const done = pkg({ status: 'delivered', deliveredAt: at('2026-11-16T13:30:00Z') }); // 8:30 AM
  const road = roadLayout([first, second, anyTime], [done], view);

  assert.deepEqual([road.from, road.to], [8, 20]);
  assert.deepEqual(road.anytime, [anyTime]);
  assert.deepEqual(road.pins.map((p) => [p.d, p.done, p.lane]), [[done, true, 0], [first, false, 0], [second, false, 1]]);
  assert.equal(road.lanes, 2);
  // 2:30 PM is 6.5 of the 12 hours shown; 9 AM is 1 of 12.
  assert.ok(Math.abs(road.pins[1].x - (6.5 / 12) * 100) < 0.001);
  assert.ok(Math.abs(road.nowLeft - (1 / 12) * 100) < 0.001);
  assert.equal(road.pins[1].label, '1–4 PM');
  assert.equal(road.pins[0].label, 'delivered 8:30 AM');
  assert.equal(road.bands.length, 2);
  assert.ok(Math.abs(road.bands[0].width - 25) < 0.001);
  assert.deepEqual(road.ticks.map((t) => t.hour), [8, 10, 12, 14, 16, 18, 20]);
  // An hour mark gives way to the "Now" label only when the two would collide.
  assert.deepEqual(road.ticks.filter((t) => t.hidden).map((t) => t.hour), []);
  const tenPastEight = { fmt, today, now: new Date('2026-11-16T13:10:00Z') };
  assert.deepEqual(roadLayout([first], [], tenPastEight).ticks.filter((t) => t.hidden).map((t) => t.hour), [8]);
  assert.equal(road.ticks[2].label, '12 PM');
  for (const pin of road.pins) assert.ok(pin.x >= 0 && pin.x <= 100);
});

test('hour labels thin out on a narrow timeline and keep clear of "Now"', () => {
  const noonToThree = pkg({ etaStart: at('2026-11-16T17:00:00Z'), etaEnd: at('2026-11-16T20:00:00Z') });
  const shown = (roadWidth, nowIso) =>
    roadLayout([noonToThree], [], { fmt, today, now: new Date(nowIso), roadWidth })
      .ticks.filter((t) => !t.hidden)
      .map((t) => t.hour);
  // A phone draws 8 AM to 8 PM in under 300 px: a label every four hours.
  assert.deepEqual(shown(288, '2026-11-16T15:00:00Z'), [8, 12, 16, 20]); // 10 AM
  // At 11:15 "Now" would cover noon, so only that label goes; the rest stay four-hourly.
  assert.deepEqual(shown(288, '2026-11-16T16:15:00Z'), [8, 16, 20]);
  // Over a whole day, the narrowest phones get one every eight hours.
  const allDay = pkg({ etaStart: at('2026-11-16T05:30:00Z'), etaEnd: at('2026-11-17T04:00:00Z') });
  const day = roadLayout([allDay], [], { fmt, today, now: new Date('2026-11-16T17:00:00Z'), roadWidth: 218 });
  assert.deepEqual([day.from, day.to], [0, 24]);
  assert.deepEqual(day.ticks.filter((t) => !t.hidden).map((t) => t.hour), [0, 8, 16, 24]);
  // A desktop has room for every two hours, even 45 minutes from "Now".
  assert.deepEqual(shown(750, '2026-11-16T16:15:00Z'), [8, 10, 12, 14, 16, 18, 20]);
});

test('the day stretches for an early or late stop, in whole two-hour steps', () => {
  const early = pkg({ etaStart: at('2026-11-16T11:00:00Z'), etaEnd: at('2026-11-16T12:30:00Z') }); // 6 to 7:30 AM
  const late = pkg({ etaEnd: at('2026-11-17T03:00:00Z') }); // by 10 PM
  const road = roadLayout([early, late], [], view);
  assert.deepEqual([road.from, road.to], [6, 22]);
  assert.equal((road.to - road.from) % 2, 0);
  assert.equal(road.pins[1].label, 'by 10 PM');
  // A window that ends tomorrow is drawn to the end of today.
  const overnight = pkg({ etaStart: at('2026-11-17T01:00:00Z'), etaEnd: at('2026-11-17T07:00:00Z') });
  assert.equal(roadLayout([overnight], [], view).to, 24);
  // Only "any time" packages: no timeline, just the list.
  assert.deepEqual(roadLayout([pkg({ etaDate: today })], [], view).pins, []);
});

test('carriers are suggested from the number and found by typing', () => {
  const carriers = {
    list: { ups: { name: 'UPS' }, usps: { name: 'USPS' }, fedex: { name: 'FedEx' }, dhl: { name: 'DHL Express' } },
    suggested: ['usps', 'ups'],
    detect: compileRules([
      { pattern: '^1Z[0-9A-Z]{16}$', code: 'ups' },
      { pattern: '^[0-9]{12}$', code: 'fedex' },
      { pattern: '^[0-9]{12}$', code: 'unlisted' },
      { pattern: '([', code: 'broken' },
    ], ''),
  };
  assert.equal(carriers.detect.length, 3);
  assert.deepEqual(detectCarriers(carriers, cleanNumber('1z 999-aa1 0123456784')), ['ups']);
  assert.deepEqual(detectCarriers(carriers, '123456789012'), ['fedex']);
  assert.deepEqual(detectCarriers(null, '123456789012'), []);

  const blank = carrierOptions(carriers, '', ['fedex']);
  assert.deepEqual(blank.items.map((o) => [o.code, o.heading]), [
    ['fedex', 'Suggested'],
    ['usps', ''],
    ['ups', ''],
    ['dhl', 'All carriers'],
  ]);
  assert.equal(carrierOptions(carriers, '', []).items[0].heading, 'Common');
  assert.deepEqual(carrierOptions(carriers, 'us', []).items.map((o) => o.code), ['usps']);
  assert.deepEqual(carrierOptions(carriers, 'ps', []).items.map((o) => o.code), ['ups', 'usps']);
  assert.deepEqual(carrierOptions(carriers, 'dhl ', []).items.map((o) => o.code), ['dhl']);
  assert.deepEqual(carrierOptions(null, 'x', []), { items: [], more: 0 });
});

test('an icon is guessed from the name', () => {
  const rules = compileRules([{ pattern: 'coffee|grinder', icon: 'mdi:coffee' }, { pattern: '(', icon: 'mdi:broken' }, { pattern: '\\bdog\\b', icon: 'mdi:paw' }]);
  assert.equal(rules.length, 2);
  assert.equal(guessIcon(rules, 'Coffee Grinder'), 'mdi:coffee');
  assert.equal(guessIcon(rules, 'Dog food'), 'mdi:paw');
  assert.equal(guessIcon(rules, 'Hot dogs'), DEFAULT_ICON);
  assert.equal(guessIcon(rules, undefined), DEFAULT_ICON);
  assert.deepEqual(compileRules(undefined), []);
});

test('Tab stays inside an open dialog', () => {
  const [close, name, save] = ['close', 'name', 'save'];
  const inside = [close, name, save];
  assert.equal(trapFocus(inside, save, false), close); // forwards off the end wraps to the start
  assert.equal(trapFocus(inside, close, true), save); // backwards off the start wraps to the end
  assert.equal(trapFocus(inside, name, false), null); // the browser's own step stays inside
  assert.equal(trapFocus(inside, name, true), null);
  assert.equal(trapFocus(inside, 'something behind the dialog', false), close);
  assert.equal(trapFocus(inside, null, true), save);
  assert.equal(trapFocus([], null, false), null);
});

test('small words', () => {
  assert.equal(cleanNumber(' 1z 999-aa1 '), '1Z999AA1');
  assert.equal(ago(at('2026-11-16T13:59:40Z'), now), 'just now');
  assert.equal(ago(at('2026-11-16T13:15:00Z'), now), '45 min ago');
  assert.equal(ago(at('2026-11-16T09:00:00Z'), now), '5 hr ago');
  assert.equal(ago(at('2026-11-15T12:00:00Z'), now), 'yesterday');
  assert.equal(ago(at('2026-11-13T14:00:00Z'), now), '3 days ago');
  assert.equal(countdown(at('2026-11-16T13:00:00Z'), now), '');
  assert.equal(countdown(at('2026-11-16T14:02:00Z'), now), 'In about 5 minutes');
  assert.equal(countdown(at('2026-11-16T14:32:00Z'), now), 'In about 30 minutes');
  assert.equal(countdown(at('2026-11-16T15:05:00Z'), now), 'In about an hour');
  assert.equal(countdown(at('2026-11-16T18:00:00Z'), now), 'In about 4 hours');
  assert.equal(dayName(fmt, today, today), 'today');
  assert.equal(dayName(fmt, '2026-11-17', today), 'tomorrow');
  assert.equal(dayName(fmt, '2026-11-15', today), 'yesterday');
  assert.equal(dayName(fmt, '2026-11-19', today), 'Thursday');
  assert.equal(dayName(fmt, '2026-11-19', today, false), 'Thu');
  assert.equal(dayName(fmt, '2026-11-30', today), 'Mon, Nov 30');
});
