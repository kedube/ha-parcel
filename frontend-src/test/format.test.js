// Dates and times as the panel shows them.
import assert from 'node:assert/strict';
import { test } from 'node:test';

import { daysBetween, makeFormat, shiftDay, toDate } from '../src/format.js';

const hass = (overrides = {}) => ({
  locale: { language: 'en', time_format: '12', time_zone: 'server', ...overrides },
  config: { time_zone: 'America/New_York' },
});

test('days are shifted and counted without regard to time zones or daylight saving', () => {
  assert.equal(shiftDay('2026-11-16', 1), '2026-11-17');
  assert.equal(shiftDay('2026-03-01', -1), '2026-02-28');
  assert.equal(shiftDay('2026-12-31', 1), '2027-01-01');
  assert.equal(daysBetween('2026-11-16', '2026-11-16'), 0);
  assert.equal(daysBetween('2026-11-16', '2026-11-21'), 5);
  assert.equal(daysBetween('2026-11-16', '2026-11-14'), -2);
  // Across the US clock changes a day is still a day.
  assert.equal(daysBetween('2026-03-07', '2026-03-09'), 2);
  assert.equal(daysBetween('2026-10-31', '2026-11-02'), 2);
});

test('toDate accepts what the integration sends and rejects the rest', () => {
  assert.equal(toDate(null), null);
  assert.equal(toDate(''), null);
  assert.equal(toDate('not a date'), null);
  assert.equal(toDate('2026-11-16T13:00:00-05:00').toISOString(), '2026-11-16T18:00:00.000Z');
});

test('the day and hour follow the Home Assistant time zone, not the browser', () => {
  const fmt = makeFormat(hass());
  const lateEvening = new Date('2026-11-17T03:30:00Z'); // 10:30 PM on the 16th in New York
  assert.equal(fmt.ymd(lateEvening), '2026-11-16');
  assert.equal(fmt.hours(lateEvening), 22.5);
  assert.equal(fmt.ymd(new Date('2026-11-16T05:00:00Z')), '2026-11-16'); // midnight
  assert.equal(fmt.hours(new Date('2026-11-16T05:00:00Z')), 0);
});

test('times are short on a 12-hour clock and plain on a 24-hour one', () => {
  const twelve = makeFormat(hass());
  const one = new Date('2026-11-16T18:00:00Z');
  const half = new Date('2026-11-16T18:30:00Z');
  const four = new Date('2026-11-16T21:00:00Z');
  const eleven = new Date('2026-11-16T16:00:00Z');
  assert.equal(twelve.time(one), '1 PM');
  assert.equal(twelve.time(half), '1:30 PM');
  assert.equal(twelve.window(one, four), '1–4 PM');
  assert.equal(twelve.window(eleven, four), '11 AM–4 PM');
  assert.equal(twelve.between(one, four), 'between 1 and 4 PM');
  assert.equal(twelve.between(eleven, one), 'between 11 AM and 1 PM');

  const twentyFour = makeFormat(hass({ time_format: '24' }));
  assert.equal(twentyFour.time(one), '13:00');
  assert.equal(twentyFour.window(one, four), '13:00–16:00');
  assert.equal(twentyFour.hourLabel(8), '08');
});

test('dates given as a day stay on that day', () => {
  const fmt = makeFormat(hass());
  assert.equal(fmt.weekday('2026-11-16'), 'Monday');
  assert.equal(fmt.weekday('2026-11-16', 'short'), 'Mon');
  assert.equal(fmt.monthDay('2026-11-16'), 'Nov 16');
  assert.equal(fmt.longDate('2026-11-16'), 'Monday, November 16');
  assert.equal(fmt.shortDate('2026-11-16'), 'Mon, Nov 16');
  assert.equal(fmt.monthShort('2026-11-16'), 'Nov');
  assert.equal(fmt.dayNumber('2026-11-06'), 6);
  assert.equal(fmt.hourLabel(8), '8 AM');
  assert.equal(fmt.hourLabel(24), '12 AM');
});

test('an unknown language falls back instead of failing', () => {
  const fmt = makeFormat({ locale: { language: 'not-a-language-tag!', time_zone: 'server' }, config: { time_zone: 'UTC' } });
  assert.equal(fmt.ymd(new Date('2026-11-16T12:00:00Z')), '2026-11-16');
  assert.equal(makeFormat(undefined).dayNumber('2026-11-16'), 16);
});
