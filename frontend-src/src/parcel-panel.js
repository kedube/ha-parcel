// The Packages sidebar panel for the Parcel integration.
import { LitElement, html, nothing, svg } from 'lit';
import { daysBetween, makeFormat, shiftDay, toDate } from './format.js';
import { ICON, ICON_LABELS, itemIconPath } from './icons.js';
import { styles } from './styles.js';

const DELETE_HELP_URL = 'https://github.com/kedube/ha-parcel#let-home-assistant-delete-packages';

const uiIcon = (path, cls = '') =>
  html`<svg class="ic ${cls}" viewBox="0 0 24 24" aria-hidden="true" focusable="false"><path d=${path}></path></svg>`;
const itemIcon = (name, cls = '') => uiIcon(itemIconPath(name), cls);

// Parcel's status codes, in friendlier words.
const STATUS = {
  0: { key: 'delivered', label: 'Delivered', icon: ICON.delivered, color: '--st-delivered', stage: 3 },
  1: { key: 'stalled', label: 'No recent updates', icon: ICON.stalled, color: '--st-muted', stage: 1, attn: true },
  2: { key: 'transit', label: 'On the way', icon: ICON.inTransit, color: '--st-transit', stage: 1 },
  3: { key: 'pickup', label: 'Ready for pickup', icon: ICON.pickup, color: '--st-pickup', stage: 2 },
  4: { key: 'out', label: 'Out for delivery', icon: ICON.outForDelivery, color: '--st-out', stage: 2 },
  5: { key: 'notfound', label: 'Not found yet', icon: ICON.notFound, color: '--st-muted', stage: 0 },
  6: { key: 'failed', label: 'Missed delivery', icon: ICON.missed, color: '--st-failed', stage: 2, attn: true },
  7: { key: 'exception', label: 'Delivery problem', icon: ICON.alert, color: '--st-attention', stage: 1, attn: true },
  8: { key: 'pre', label: 'Label created', icon: ICON.labelCreated, color: '--st-pre', stage: 0 },
};
const PENDING = { key: 'pending', label: 'Waiting for first update', icon: ICON.waiting, color: '--st-muted', stage: -1 };
const STAGES = [
  { label: 'Label created', icon: ICON.labelCreated },
  { label: 'On the way', icon: ICON.inTransit },
  { label: 'Out for delivery', icon: ICON.outForDelivery },
  { label: 'Delivered', icon: ICON.home },
];
const PICKUP_STAGES = [STAGES[0], STAGES[1], { label: 'Ready for pickup', icon: ICON.pickup }, { label: 'Picked up', icon: ICON.delivered }];

const GROUPS = {
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
const ORDER = ['new', 'pickup', 'today', 'late', 'tomorrow', 'week', 'later', 'nodate', 'delivered'];
const LATER_GROUPS = ['new', 'late', 'tomorrow', 'week', 'later', 'nodate'];

// What some carriers need besides the number, keyed by "extra" in Parcel's carrier list.
const EXTRA = {
  1: { label: 'Postcode', type: 'text', placeholder: 'Destination postcode', autocomplete: 'postal-code' },
  2: { label: 'Email used for the order', type: 'email', placeholder: 'you@example.com', autocomplete: 'email', number: 'Order number' },
  3: { label: 'PIN', type: 'text', placeholder: 'PIN from the shipping notice', autocomplete: 'off' },
  4: { label: 'Phone number', type: 'tel', placeholder: 'Phone number on the order', autocomplete: 'tel' },
  5: { label: 'Country code and postcode', type: 'text', placeholder: 'US12345', autocomplete: 'off' },
};

const cap = (s) => (s ? s.charAt(0).toUpperCase() + s.slice(1) : s);
const plural = (n, word) => `${n} ${word}${n === 1 ? '' : 's'}`;
const cleanNumber = (s) => s.replace(/[\s-]/g, '').toUpperCase();

function ensureFonts(base) {
  if (document.getElementById('parcel-panel-fonts')) return;
  const style = document.createElement('style');
  style.id = 'parcel-panel-fonts';
  style.textContent = [400, 500, 600]
    .map(
      (w) =>
        `@font-face{font-family:"Parcel Outfit";font-style:normal;font-weight:${w};font-display:swap;` +
        `src:url("${base}/fonts/outfit-latin-${w}-normal.woff2") format("woff2");}`,
    )
    .join('');
  document.head.appendChild(style);
}

class ParcelPackagesPanel extends LitElement {
  static properties = {
    hass: { attribute: false },
    narrow: { type: Boolean },
    route: { attribute: false },
    panel: { attribute: false },
    _payload: { state: true },
    _subError: { state: true },
    _query: { state: true },
    _searchOpen: { state: true },
    _selectedUid: { state: true },
    _showAllEvents: { state: true },
    _iconsOpen: { state: true },
    _menuFor: { state: true },
    _confirmFor: { state: true },
    _deleting: { state: true },
    _addOpen: { state: true },
    _form: { state: true },
    _carriers: { state: true },
    _toast: { state: true },
    _refreshing: { state: true },
    _tick: { state: true },
  };

  static styles = styles;

  constructor() {
    super();
    this._payload = null;
    this._subError = '';
    this._query = '';
    this._searchOpen = false;
    this._selectedUid = null;
    this._showAllEvents = false;
    this._iconsOpen = false;
    this._menuFor = null;
    this._confirmFor = null;
    this._deleting = false;
    this._addOpen = false;
    this._form = this._blankForm();
    this._carriers = null;
    this._toast = null;
    this._refreshing = false;
    this._tick = 0;
    this._items = [];
    this._iconRules = [];
    this._onKey = this._onKey.bind(this);
    this._onDocClick = () => {
      if (this._menuFor) this._menuFor = null;
    };
  }

  // ---------------------------------------------------------------- lifecycle

  connectedCallback() {
    super.connectedCallback();
    ensureFonts(this.panel?.config?.static_url || '/parcel_static');
    window.addEventListener('keydown', this._onKey);
    window.addEventListener('click', this._onDocClick);
    this._timer = setInterval(() => {
      this._tick += 1;
    }, 30000);
    if (this.hass) this._subscribe();
  }

  disconnectedCallback() {
    super.disconnectedCallback();
    window.removeEventListener('keydown', this._onKey);
    window.removeEventListener('click', this._onDocClick);
    clearInterval(this._timer);
    this._unsubscribe();
  }

  shouldUpdate(changed) {
    // Home Assistant sends a new hass object on every state change; only a few parts matter here.
    if (changed.size === 1 && changed.has('hass')) {
      const old = changed.get('hass');
      if (!old || !this.hass) return true;
      return (
        old.themes?.darkMode !== this.hass.themes?.darkMode ||
        old.locale !== this.hass.locale ||
        old.language !== this.hass.language ||
        old.dockedSidebar !== this.hass.dockedSidebar
      );
    }
    return true;
  }

  willUpdate(changed) {
    if (!this._fmt || changed.has('hass')) this._fmt = makeFormat(this.hass);
    if (changed.has('_payload')) {
      this._items = this._normalize(this._payload);
      this._iconRules = (this._payload?.icon_rules || []).flatMap((rule) => {
        try {
          return [{ re: new RegExp(rule.pattern, 'i'), icon: rule.icon }];
        } catch {
          return [];
        }
      });
    }
  }

  updated(changed) {
    if (changed.has('hass')) {
      this.toggleAttribute('dark', Boolean(this.hass?.themes?.darkMode));
      if (this.hass && !this._unsub && this.isConnected) this._subscribe();
    }
  }

  _subscribe() {
    if (this._unsub) return;
    this._unsub = this.hass.connection
      .subscribeMessage((payload) => {
        this._subError = '';
        this._payload = payload;
      }, { type: 'parcel/subscribe' })
      .catch((err) => {
        this._subError = err?.message || 'Couldn’t load packages';
        this._unsub = undefined;
      });
  }

  _unsubscribe() {
    if (!this._unsub) return;
    this._unsub.then((unsub) => unsub?.()).catch(() => {});
    this._unsub = undefined;
  }

  // ---------------------------------------------------------------- data

  _normalize(payload) {
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
          statusCode: d.status_code,
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
          statusCode: null,
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

  get _entries() {
    return this._payload?.entries || [];
  }

  _statusOf(d) {
    return d.pending ? PENDING : STATUS[d.statusCode] || STATUS[2];
  }

  _dayKey(d) {
    if (d.etaDate) return d.etaDate;
    const when = d.etaStart || d.etaEnd;
    return when ? this._fmt.ymd(when) : null;
  }

  _sortTime(d) {
    if (d.etaStart || d.etaEnd) return (d.etaStart || d.etaEnd).getTime();
    if (d.etaDate) return Date.parse(`${d.etaDate}T00:00:00`);
    return Infinity;
  }

  _dayName(ymd, today, long = true) {
    if (ymd === today) return 'today';
    if (ymd === shiftDay(today, 1)) return 'tomorrow';
    if (ymd === shiftDay(today, -1)) return 'yesterday';
    if (Math.abs(daysBetween(today, ymd)) < 6) return this._fmt.weekday(ymd, long ? 'long' : 'short');
    return this._fmt.shortDate(ymd);
  }

  _when(date, today) {
    return `${cap(this._dayName(this._fmt.ymd(date), today, false))}, ${this._fmt.time(date)}`;
  }

  _ago(date, now) {
    const m = Math.round((now - date) / 60000);
    if (m < 1) return 'just now';
    if (m < 60) return `${m} min ago`;
    const h = Math.round(m / 60);
    if (h < 24) return `${h} hr ago`;
    const days = Math.round(h / 24);
    return days === 1 ? 'yesterday' : `${days} days ago`;
  }

  _countdown(target, now) {
    const m = Math.round((target - now) / 60000);
    if (m <= 0) return '';
    if (m < 50) return `In about ${Math.max(5, Math.round(m / 5) * 5)} minutes`;
    const h = Math.round(m / 60);
    return h === 1 ? 'In about an hour' : `In about ${h} hours`;
  }

  _groupOf(d, today) {
    if (d.pending) return 'new';
    const st = this._statusOf(d);
    if (st.key === 'delivered') return 'delivered';
    if (st.attn) return 'attention';
    if (st.key === 'pickup') return 'pickup';
    const day = this._dayKey(d);
    if (st.key === 'out' || day === today) return 'today';
    if (!day) return 'nodate';
    const diff = daysBetween(today, day);
    if (diff < 0) return 'late';
    if (diff === 1) return 'tomorrow';
    if (diff < 6) return 'week';
    return 'later';
  }

  _grouped(list, today) {
    const g = { attention: [] };
    for (const key of ORDER) g[key] = [];
    for (const d of list) g[this._groupOf(d, today)].push(d);
    for (const key of ORDER) {
      if (key === 'delivered') g[key].sort((a, b) => (b.deliveredAt?.getTime() || 0) - (a.deliveredAt?.getTime() || 0));
      else g[key].sort((a, b) => this._sortTime(a) - this._sortTime(b));
    }
    g.attention.sort((a, b) => this._sortTime(a) - this._sortTime(b));
    return g;
  }

  _guessIcon(text) {
    for (const rule of this._iconRules) if (rule.re.test(text || '')) return rule.icon;
    return 'mdi:package-variant-closed';
  }

  _matches(d) {
    const q = this._query.trim().toLowerCase();
    if (!q) return true;
    return (
      d.description.toLowerCase().includes(q) ||
      d.trackingNumber.toLowerCase().includes(q.replace(/[\s-]/g, '')) ||
      (d.carrierName || '').toLowerCase().includes(q)
    );
  }

  // ---------------------------------------------------------------- actions

  _onKey(e) {
    if (e.key !== 'Escape') return;
    if (this._confirmFor) {
      if (!this._deleting) this._confirmFor = null;
    } else if (this._addOpen && this._form.carrierOpen) this._setForm({ carrierOpen: false });
    else if (this._addOpen) this._closeAdd();
    else if (this._selectedUid) this._closeDetails();
    else if (this._menuFor) this._menuFor = null;
    else if (this._searchOpen) {
      this._query = '';
      this._searchOpen = false;
    }
  }

  _toggleSidebar() {
    this.dispatchEvent(new Event('hass-toggle-menu', { bubbles: true, composed: true }));
  }

  _showToast(message, error = false) {
    this._toast = { message, error };
    clearTimeout(this._toastTimer);
    this._toastTimer = setTimeout(() => {
      this._toast = null;
    }, error ? 6000 : 4000);
  }

  async _copy(text) {
    try {
      await navigator.clipboard.writeText(text);
      this._showToast('Tracking number copied');
    } catch {
      this._showToast(`Couldn't copy automatically. The number is ${text}`);
    }
  }

  async _refresh() {
    if (this._refreshing) return;
    this._refreshing = true;
    try {
      await this.hass.callWS({ type: 'parcel/refresh' });
      this._showToast('Up to date with Parcel');
    } catch (err) {
      this._showToast(err?.message || 'Couldn’t check Parcel', true);
    } finally {
      this._refreshing = false;
    }
  }

  _openSearch() {
    this._searchOpen = true;
    this.updateComplete.then(() => this.renderRoot.querySelector('#q')?.focus());
  }

  _openDetails(d, opts = {}) {
    this._lastFocus = this.renderRoot.activeElement || document.activeElement;
    this._menuFor = null;
    this._selectedUid = d.uid;
    this._showAllEvents = false;
    this._iconsOpen = Boolean(opts.icons);
    this.updateComplete.then(() => this.renderRoot.querySelector('.sheet .icon-btn')?.focus());
  }

  _closeDetails() {
    this._selectedUid = null;
    this._lastFocus?.focus?.();
  }

  _askDelete(d) {
    this._menuFor = null;
    this._confirmFor = d;
  }

  async _doDelete(d) {
    this._deleting = true;
    try {
      await this.hass.callWS({ type: 'parcel/delete', entry_id: d.entryId, key: d.key });
      if (this._selectedUid === d.uid) this._selectedUid = null;
      this._showToast(`Deleted “${d.description}”`);
    } catch (err) {
      this._showToast(err?.message || 'Couldn’t delete the package', true);
    } finally {
      this._deleting = false;
      this._confirmFor = null;
    }
  }

  async _setIcon(d, icon) {
    try {
      await this.hass.callWS({ type: 'parcel/set_icon', entry_id: d.entryId, key: d.key, icon });
    } catch (err) {
      this._showToast(err?.message || 'Couldn’t change the icon', true);
    }
  }

  _scrollTo(id) {
    const reduce = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    this.renderRoot.querySelector(`#${id}`)?.scrollIntoView({ behavior: reduce ? 'auto' : 'smooth', block: 'start' });
  }

  _blankForm() {
    return {
      entryId: '', number: '', carrier: '', carrierEditing: false, carrierQuery: '', carrierOpen: false, active: 0,
      description: '', icon: '', extra: '', push: true, submitting: false, error: '',
    };
  }

  _setForm(patch) {
    this._form = { ...this._form, ...patch };
  }

  async _loadCarriers() {
    try {
      const result = await this.hass.callWS({ type: 'parcel/carriers' });
      this._carriers = {
        list: result.carriers || {},
        suggested: result.suggested || [],
        detect: (result.detect || []).flatMap((rule) => {
          try {
            return [{ re: new RegExp(rule.pattern), code: rule.code }];
          } catch {
            return [];
          }
        }),
      };
    } catch (err) {
      this._carriers = { list: {}, suggested: [], detect: [], error: err?.message || 'Couldn’t load carriers' };
    }
  }

  _openAdd() {
    this._lastFocus = this.renderRoot.activeElement || document.activeElement;
    this._menuFor = null;
    this._form = { ...this._blankForm(), entryId: this._entries[0]?.entry_id || '' };
    this._addOpen = true;
    if (!this._carriers || this._carriers.error) this._loadCarriers();
    this.updateComplete.then(() => this.renderRoot.querySelector('#f-number')?.focus());
  }

  _closeAdd() {
    this._addOpen = false;
    this._lastFocus?.focus?.();
  }

  _detect(number) {
    if (!this._carriers) return [];
    const list = this._carriers.list;
    return [...new Set(this._carriers.detect.filter((r) => r.re.test(number)).map((r) => r.code))].filter((c) => list[c]);
  }

  _carrierName(code) {
    return this._carriers?.list?.[code]?.name || code.toUpperCase();
  }

  _carrierOptions(query, detected) {
    const list = this._carriers?.list || {};
    const q = query.trim().toLowerCase();
    const all = Object.entries(list).map(([code, c]) => ({ code, name: c.name }));
    if (!q) {
      const topCodes = [...detected, ...(this._carriers?.suggested || []).filter((c) => !detected.includes(c))].filter((c) => list[c]);
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

  _pickCarrier(code) {
    this._setForm({ carrier: code, carrierEditing: false, carrierOpen: false, carrierQuery: '', extra: '' });
    this.updateComplete.then(() => this.renderRoot.querySelector('#f-desc')?.focus());
  }

  _onComboKey(e, options) {
    const n = options.items.length;
    if (!n) return;
    if (e.key === 'ArrowDown') {
      e.preventDefault();
      this._setForm({ active: (this._form.active + 1) % n, carrierOpen: true });
      this.updateComplete.then(() => this.renderRoot.querySelector('.opt[aria-selected="true"]')?.scrollIntoView({ block: 'nearest' }));
    } else if (e.key === 'ArrowUp') {
      e.preventDefault();
      this._setForm({ active: (this._form.active - 1 + n) % n });
      this.updateComplete.then(() => this.renderRoot.querySelector('.opt[aria-selected="true"]')?.scrollIntoView({ block: 'nearest' }));
    } else if (e.key === 'Enter' && this._form.carrierOpen) {
      e.preventDefault();
      this._pickCarrier(options.items[this._form.active].code);
    }
  }

  async _submitAdd(e, ctx) {
    e.preventDefault();
    if (!ctx.valid || this._form.submitting) return;
    const name = this._form.description.trim();
    this._setForm({ submitting: true, error: '' });
    try {
      await this.hass.callWS({
        type: 'parcel/add',
        entry_id: ctx.entryId || undefined,
        tracking_number: ctx.number,
        description: name,
        carrier_code: ctx.carrier,
        extra: this._form.extra.trim() || null,
        send_push_confirmation: this._form.push,
        icon: this._form.icon || null,
      });
      this._addOpen = false;
      this._query = '';
      this._showToast(`Now tracking “${name}”. The first update usually takes a few minutes.`);
      this.updateComplete.then(() => this._scrollTo('sec-new'));
    } catch (err) {
      this._setForm({ submitting: false, error: err?.message || 'Couldn’t add the package' });
    }
  }

  // ---------------------------------------------------------------- render

  render() {
    if (!this._fmt) this._fmt = makeFormat(this.hass);
    const now = new Date();
    const today = this._fmt.ymd(now);
    const view = { fmt: this._fmt, today, now };
    const showMenu = this.narrow || this.hass?.dockedSidebar === 'always_hidden';
    const entries = this._entries;
    const updatedAt = entries.map((e) => toDate(e.updated_at)).filter(Boolean).sort((a, b) => b - a)[0];
    const searching = this._query.trim().length > 0;
    const g = this._grouped(this._items, today);
    const selected = this._selectedUid ? this._items.find((d) => d.uid === this._selectedUid) : null;

    let body;
    if (this._subError) body = html`<div class="banner">${uiIcon(ICON.warn)}<span>${this._subError}</span></div>`;
    else if (!this._payload) body = html`<p class="loading">Loading packages…</p>`;
    else if (!entries.length) body = html`<p class="loading">Parcel isn’t set up. Add it in Settings › Devices &amp; services.</p>`;
    else if (!this._items.length) body = this._renderEmpty();
    else if (searching) body = this._renderResults(view);
    else {
      body = html`${this._renderHero(g, view)}${this._renderAttention(g.attention, view)}${ORDER.map((key) =>
        this._renderGroup(key, g[key], view),
      )}`;
    }
    const errors = entries.filter((e) => e.last_error);
    const paused = entries.filter((e) => {
      const until = toDate(e.paused_until);
      return until && until > now;
    });

    return html`
      <header class="appbar ${this._searchOpen ? 'searching' : ''}">
        <div class="appbar-inner">
          ${showMenu ? html`<button class="icon-btn" aria-label="Show sidebar" @click=${this._toggleSidebar}>${uiIcon(ICON.menu)}</button>` : nothing}
          <h1>Packages</h1>
          <div class="spacer"></div>
          ${this._searchOpen
            ? html`<label class="search">${uiIcon(ICON.search, 'sm')}
                <input id="q" type="search" placeholder="Search by name, number or carrier" aria-label="Search packages"
                  .value=${this._query} @input=${(e) => { this._query = e.target.value; }}>
                <button class="icon-btn tiny" aria-label="Close search" @click=${() => { this._query = ''; this._searchOpen = false; }}>${uiIcon(ICON.close, 'xs')}</button>
              </label>`
            : html`<button class="icon-btn" aria-label="Search packages" title="Search packages" @click=${this._openSearch}>${uiIcon(ICON.search)}</button>`}
          ${updatedAt ? html`<span class="updated" title="Home Assistant checks Parcel every few minutes. Parcel allows 20 checks an hour.">
            ${this._refreshing ? 'Checking…' : `Updated ${this._ago(updatedAt, now)}`}</span>` : nothing}
          <button class="icon-btn ${this._refreshing ? 'spin' : ''}" aria-label="Check Parcel for updates" title="Check Parcel for updates" @click=${this._refresh}>${uiIcon(ICON.refresh)}</button>
        </div>
      </header>
      <main class="main">
        ${errors.map((e) => html`<div class="banner" role="status">${uiIcon(ICON.warn)}<span>${entries.length > 1 ? `${e.title}: ` : ''}${e.last_error}</span></div>`)}
        ${paused.map((e) => html`<div class="banner info" role="status">${uiIcon(ICON.info)}<span>${entries.length > 1 ? `${e.title}: ` : ''}Parcel asked Home Assistant to slow down. This is the last update it has; it will check again around ${this._fmt.time(toDate(e.paused_until))}.</span></div>`)}
        ${body}
      </main>
      ${entries.length ? html`<button class="fab" @click=${this._openAdd}>${uiIcon(ICON.plus)}<span>Add package</span></button>` : nothing}
      ${selected ? this._renderSheet(selected, view) : nothing}
      ${this._addOpen ? this._renderAdd() : nothing}
      ${this._confirmFor ? this._renderConfirm() : nothing}
      ${this._toast
        ? html`<div class="toast ${this._toast.error ? 'error' : ''}" role="status" aria-live="polite">
            ${uiIcon(this._toast.error ? ICON.warn : ICON.checkCircle, 'sm')}<span>${this._toast.message}</span></div>`
        : nothing}
    `;
  }

  _greeting(now) {
    const h = this._fmt.hours(now);
    return h < 12 ? 'Good morning' : h < 17 ? 'Good afternoon' : 'Good evening';
  }

  _renderHero(g, view) {
    const { fmt, today, now } = view;
    const todays = g.today;
    const deliveredToday = g.delivered.filter((d) => d.deliveredAt && fmt.ymd(d.deliveredAt) === today);
    const comingLater = LATER_GROUPS.reduce((n, key) => n + g[key].length, 0);

    let headline;
    let sub;
    let color = '--st-out';
    if (todays.length) {
      const noun = todays.length === 1 ? 'package' : 'packages';
      const verb = todays.length === 1 ? 'arrives' : 'arrive';
      headline = html`<span class="n">${todays.length} ${noun}</span> ${verb} today`;
      const starts = todays.filter((d) => d.etaStart).map((d) => d.etaStart.getTime());
      const ends = todays.filter((d) => d.etaEnd || d.etaStart).map((d) => (d.etaEnd || d.etaStart).getTime());
      if (starts.length && ends.length) sub = `Expected ${fmt.between(new Date(Math.min(...starts)), new Date(Math.max(...ends)))}.`;
      else if (ends.length) sub = `Expected by ${fmt.time(new Date(Math.max(...ends)))}.`;
      else sub = 'The carriers haven’t shared delivery times yet.';
      if (deliveredToday.length) sub += ` ${deliveredToday.length} already delivered today.`;
    } else if (deliveredToday.length) {
      color = '--st-delivered';
      headline = html`<span class="n">Today’s deliveries</span> are in`;
      sub = `${plural(deliveredToday.length, 'package')} delivered today.`;
    } else {
      color = '--st-transit';
      headline = html`Nothing arriving today`;
      const next = [...g.tomorrow, ...g.week, ...g.later][0];
      sub = next ? `Next up: ${next.description}, ${this._dayName(this._dayKey(next), today)}.` : 'Your packages are on their way.';
    }

    const stats = [];
    if (g.attention.length) stats.push({ n: g.attention.length, label: g.attention.length === 1 ? 'needs a look' : 'need a look', color: '--st-attention', target: 'sec-attention' });
    if (g.pickup.length) stats.push({ n: g.pickup.length, label: 'to pick up', color: '--st-pickup', target: 'sec-pickup' });
    if (comingLater) stats.push({ n: comingLater, label: 'coming later', color: '--st-transit', target: `sec-${LATER_GROUPS.find((k) => g[k].length)}` });
    if (deliveredToday.length) stats.push({ n: deliveredToday.length, label: 'delivered today', color: '--st-delivered', target: 'sec-delivered' });

    return html`<section class="hero" aria-labelledby="hero-h" style="--c: var(${color})">
      <div class="hero-top">
        <div>
          <div class="greet">${this._greeting(now)}</div>
          <h2 class="hero-h" id="hero-h">${headline}</h2>
          <p class="hero-sub">${sub}</p>
        </div>
        <div class="cal" aria-hidden="true">
          <span class="dow">${fmt.weekday(today, 'short')}</span>
          <span class="dom">${fmt.dayNumber(today)}</span>
          <span class="mon">${fmt.monthShort(today)}</span>
        </div>
      </div>
      ${this._renderRoad(todays, deliveredToday, view)}
      ${stats.length
        ? html`<div class="hero-stats">${stats.map((s) => html`
            <button class="stat" style="--c: var(${s.color})" @click=${() => this._scrollTo(s.target)}><span class="sn">${s.n}</span>${s.label}</button>`)}</div>`
        : nothing}
    </section>`;
  }

  _renderRoad(todays, deliveredToday, view) {
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
      const st = this._statusOf(d);
      if (!d.etaStart && !d.etaEnd) {
        anytime.push(d);
        continue;
      }
      const end = d.etaEnd ? clampH(d.etaEnd) : Math.min(24, clampH(d.etaStart) + 2);
      let start = d.etaStart ? clampH(d.etaStart) : Math.min(nowH, end - 0.5);
      if (start > end - 0.25) start = Math.max(0, end - 0.5);
      const label = d.etaStart && d.etaEnd ? fmt.window(d.etaStart, d.etaEnd) : d.etaEnd ? `by ${fmt.time(d.etaEnd)}` : `from ${fmt.time(d.etaStart)}`;
      pins.push({ d, st, start, end, at: (start + end) / 2, label });
    }
    for (const d of deliveredToday) {
      const h = fmt.hours(d.deliveredAt);
      pins.push({ d, st: this._statusOf(d), start: h, end: h, at: h, label: `delivered ${fmt.time(d.deliveredAt)}`, done: true });
    }
    if (!pins.length && !anytime.length) return nothing;

    let a = 8;
    let b = 20;
    for (const p of pins) {
      a = Math.min(a, Math.floor(p.start));
      b = Math.max(b, Math.ceil(p.end));
    }
    a = Math.max(0, Math.min(a, Math.floor(nowH)));
    b = Math.min(24, Math.max(b, Math.ceil(nowH)));
    if ((b - a) % 2) {
      if (b < 24) b += 1;
      else a -= 1;
    }
    const pct = (h) => Math.min(100, Math.max(0, ((h - a) / (b - a)) * 100));

    // Stack nearby stops into up to three lanes so their icons don't collide.
    pins.sort((x, y) => x.at - y.at);
    const laneEnds = [];
    const gap = (b - a) * 0.075;
    for (const p of pins) {
      let lane = laneEnds.findIndex((last) => p.at - last >= gap);
      if (lane === -1) lane = laneEnds.length < 3 ? laneEnds.length : laneEnds.indexOf(Math.min(...laneEnds));
      laneEnds[lane] = p.at;
      p.lane = lane;
    }
    const ticks = [];
    for (let h = a; h <= b; h += 2) ticks.push(h);

    return html`<div class="road-wrap" style="--lanes: ${Math.max(1, laneEnds.length)}">
      ${pins.length
        ? html`
          <div class="pins">
            ${pins.map((p) => {
              const x = pct(p.at);
              return html`<button class="pin ${x < 14 ? 'edge-l' : x > 86 ? 'edge-r' : ''} ${p.done ? 'done' : ''}"
                  style="left: ${x}%; --lane: ${p.lane}; --c: var(${p.st.color})" aria-label="${p.d.description}, ${p.label}"
                  @click=${() => this._openDetails(p.d)}>
                <span class="tip">${p.d.description} · ${p.label}</span>
                <span class="pin-av">${itemIcon(p.d.icon)}${p.done ? html`<span class="pin-check">${uiIcon(ICON.check, 'xxs')}</span>` : nothing}</span>
                <span class="stem"></span>
              </button>`;
            })}
          </div>
          <div class="road" aria-hidden="true">
            ${pins.filter((p) => !p.done).map((p) => html`<span class="band" style="left: ${pct(p.start)}%; width: ${Math.max(pct(p.end) - pct(p.start), 1.5)}%; --c: var(${p.st.color})"></span>`)}
            <span class="now-truck" style="left: ${pct(nowH)}%" title="Now, ${fmt.time(now)}">${uiIcon(ICON.truckNow, 'xs')}</span>
          </div>
          <div class="hours" aria-hidden="true">
            ${ticks.map((h) => (Math.abs(h - nowH) < (b - a) * 0.07 ? nothing : html`<span class="tick" style="left: ${pct(h)}%">${fmt.hourLabel(h)}</span>`))}
            <span class="now-lab" style="left: ${pct(nowH)}%">Now</span>
          </div>`
        : nothing}
      ${anytime.length
        ? html`<div class="anytime"><span class="any-label">Any time today:</span>
            ${anytime.map((d) => html`<button class="any-chip" style="--c: var(${this._statusOf(d).color})" @click=${() => this._openDetails(d)}>
              <span class="any-av">${itemIcon(d.icon, 'xs')}</span><span class="any-name">${d.description}</span></button>`)}</div>`
        : nothing}
    </div>`;
  }

  _reasonOf(d, st, view) {
    const last = d.events[0];
    const carrier = d.carrierShort || d.carrierName;
    if (st.key === 'failed') {
      const nextDay = this._dayKey(d);
      const retry = nextDay
        ? `${carrier} will try again ${this._dayName(nextDay, view.today)}${d.etaStart && d.etaEnd ? `, ${view.fmt.window(d.etaStart, d.etaEnd)}` : ''}.`
        : `Check with ${carrier} about the next attempt.`;
      const why = last?.additional ? `${last.additional.split('. ')[0].replace(/\.$/, '')}. ` : '';
      return { title: 'Missed delivery', hint: `${why}${retry}` };
    }
    if (st.key === 'exception') return { title: last?.text || 'Delivery problem', hint: last?.additional || `Check with ${carrier} for details.` };
    if (st.key === 'stalled') return { title: 'No updates for a while', hint: last?.when ? `Last update ${this._ago(last.when, view.now)}.` : `Check with ${carrier} if it seems late.` };
    return { title: st.label, hint: '' };
  }

  _renderAttention(list, view) {
    if (!list.length) return nothing;
    return html`<section class="attention" id="sec-attention" aria-labelledby="att-h">
      <div class="att-head">
        <span class="att-ic">${uiIcon(ICON.alert)}</span>
        <div><h3 id="att-h">${list.length === 1 ? '1 package needs a look' : `${list.length} packages need a look`}</h3>
          <p>Something changed that you may want to act on.</p></div>
      </div>
      ${list.map((d) => {
        const st = this._statusOf(d);
        const r = this._reasonOf(d, st, view);
        return html`<button class="att-row" style="--c: var(${st.color})" @click=${() => this._openDetails(d)}>
          <span class="att-av">${itemIcon(d.icon)}</span>
          <span class="att-text"><span class="att-name">${d.description}</span><span class="att-reason">${r.title}</span>${r.hint ? html`<span class="att-hint">${r.hint}</span>` : nothing}</span>
          ${uiIcon(ICON.chevronRight, 'sm chev')}
        </button>`;
      })}
    </section>`;
  }

  _renderGroup(key, list, view) {
    if (!list.length) return nothing;
    const meta = GROUPS[key];
    return html`<section class="group" id="sec-${key}" aria-labelledby="h-${key}">
      <div class="group-h"><h3 id="h-${key}">${meta.title}</h3>${meta.sub ? html`<span class="gsub">${meta.sub(view)}</span>` : nothing}<span class="gcount">${list.length}</span></div>
      <div class="cards">${list.map((d) => this._renderCard(d, view))}</div>
    </section>`;
  }

  _renderResults(view) {
    const list = this._items.filter((d) => this._matches(d));
    if (!list.length) {
      return html`<div class="no-match">${uiIcon(ICON.search)}<p>No packages match “${this._query}”.</p>
        <button class="btn text" @click=${() => { this._query = ''; }}>Clear search</button></div>`;
    }
    return html`<section class="group" aria-labelledby="h-results">
      <div class="group-h"><h3 id="h-results">Results</h3><span class="gcount">${list.length}</span></div>
      <div class="cards">${list.map((d) => this._renderCard(d, view))}</div>
    </section>`;
  }

  _renderRing(d, st, size = '') {
    const filled = st.key === 'pending' || st.key === 'notfound' ? 0 : st.stage + 1;
    const r = 25;
    const C = 2 * Math.PI * r;
    const gap = 9;
    const seg = C / 4 - gap;
    return html`<span class="ring ${size} ${st.key === 'pending' ? 'pending' : ''}">
      <svg viewBox="0 0 56 56" aria-hidden="true">${[0, 1, 2, 3].map(
        (i) => svg`<circle class="seg ${i < filled ? 'on' : ''}" cx="28" cy="28" r="${r}" stroke-dasharray="${seg} ${C - seg}" stroke-dashoffset="${-(i * C) / 4 - gap / 2}"></circle>`,
      )}</svg>
      <span class="av">${itemIcon(d.icon)}</span>
      ${st.key === 'delivered' ? html`<span class="done-badge">${uiIcon(ICON.check, 'xxs')}</span>` : nothing}
    </span>`;
  }

  _badgeOf(d, st, view) {
    const { fmt, today } = view;
    if (d.pending) return { main: 'New', sub: 'just added' };
    if (st.key === 'delivered') {
      if (!d.deliveredAt) return { main: 'Delivered', sub: '' };
      const day = fmt.ymd(d.deliveredAt);
      return day === today
        ? { main: fmt.time(d.deliveredAt), sub: 'today' }
        : { main: cap(this._dayName(day, today, false)), sub: fmt.time(d.deliveredAt) };
    }
    if (st.key === 'pickup') return { main: 'Pick up', sub: 'ready now' };
    const day = this._dayKey(d);
    if (!day) return { main: '—', sub: 'no date yet' };
    const timeText = d.etaStart && d.etaEnd ? fmt.window(d.etaStart, d.etaEnd) : d.etaEnd ? `by ${fmt.time(d.etaEnd)}` : '';
    const diff = daysBetween(today, day);
    if (diff === 0) return { main: timeText || 'Today', sub: timeText ? 'today' : 'any time' };
    if (diff < 0) return { main: 'Late', sub: `was due ${fmt.monthDay(day)}` };
    if (diff === 1) return { main: 'Tomorrow', sub: timeText };
    if (diff < 6) return { main: fmt.weekday(day, 'short'), sub: fmt.monthDay(day) };
    return { main: fmt.monthDay(day), sub: fmt.weekday(day, 'short') };
  }

  _metaOf(d, view) {
    const last = d.events[0];
    const parts = [d.carrierShort || d.carrierName];
    if (d.pending) parts.push('Parcel will check in a few minutes');
    else if (last?.location) parts.push(last.location);
    else if (last?.text && last.text.toLowerCase() !== this._statusOf(d).label.toLowerCase()) parts.push(last.text);
    if (!d.pending && last?.when) parts.push(this._ago(last.when, view.now));
    return parts.filter(Boolean).join(' · ');
  }

  _renderCard(d, view) {
    const st = this._statusOf(d);
    const b = this._badgeOf(d, st, view);
    const menuOpen = this._menuFor === d.uid;
    const open = () => this._openDetails(d);
    return html`<article class="pkg ${st.key} ${menuOpen ? 'menu-open' : ''}" style="--c: var(${st.color})" tabindex="0" role="button"
        aria-label="${d.description}: ${st.label}. ${b.main} ${b.sub}. Show details"
        @click=${open} @keydown=${(e) => { if (e.target === e.currentTarget && (e.key === 'Enter' || e.key === ' ')) { e.preventDefault(); open(); } }}>
      ${this._renderRing(d, st)}
      <div class="pkg-main">
        <span class="pkg-name">${d.description}</span>
        <span class="pkg-status">${uiIcon(st.icon, 'xs')}${st.label}</span>
        <span class="pkg-meta">${this._metaOf(d, view)}</span>
      </div>
      <div class="when"><span class="when-main">${b.main}</span>${b.sub ? html`<span class="when-sub">${b.sub}</span>` : nothing}</div>
      <button class="icon-btn kebab" aria-label="More for ${d.description}" aria-haspopup="menu" aria-expanded=${String(menuOpen)}
        @click=${(e) => { e.stopPropagation(); this._menuFor = menuOpen ? null : d.uid; }}>${uiIcon(ICON.more, 'sm')}</button>
      ${menuOpen
        ? html`<div class="menu" role="menu" @click=${(e) => e.stopPropagation()}>
            <button role="menuitem" @click=${() => { this._menuFor = null; this._copy(d.trackingNumber); }}>${uiIcon(ICON.copy, 'sm')}Copy tracking number</button>
            <button role="menuitem" @click=${() => this._openDetails(d, { icons: true })}>${uiIcon(ICON.shape, 'sm')}Change icon</button>
            <button role="menuitem" class="danger" @click=${() => this._askDelete(d)}>${uiIcon(ICON.delete, 'sm')}Delete…</button>
          </div>`
        : nothing}
    </article>`;
  }

  _etaFor(d, st, view) {
    const { fmt, today, now } = view;
    if (d.pending) return { main: 'Waiting for the first update', sub: 'Parcel will check with the carrier in a few minutes.' };
    if (st.key === 'delivered') {
      if (!d.deliveredAt) return { main: 'Delivered', sub: d.events[0]?.location || '' };
      const loc = d.events[0]?.location;
      return {
        main: `Delivered ${this._dayName(fmt.ymd(d.deliveredAt), today)}`,
        sub: `At ${fmt.time(d.deliveredAt)}${loc ? ` · ${loc}` : ''}`,
        note: d.events[0]?.additional || '',
      };
    }
    if (st.key === 'pickup') return { main: 'Ready for pickup', sub: d.events[0]?.location || '', note: d.events[0]?.additional || '' };
    if (st.attn) {
      const r = this._reasonOf(d, st, view);
      return { main: r.title, sub: r.hint };
    }
    const day = this._dayKey(d);
    if (!day) return { main: 'No delivery date yet', sub: 'The carrier hasn’t shared an estimate.' };
    let sub = '';
    if (d.etaStart && d.etaEnd) sub = cap(fmt.between(d.etaStart, d.etaEnd));
    else if (d.etaEnd) sub = `By ${fmt.time(d.etaEnd)}`;
    else if (st.key === 'pre') sub = 'The carrier doesn’t have the package yet.';
    else if (day === today) sub = 'No time window from the carrier.';
    let note = '';
    if (d.etaStart && fmt.ymd(d.etaStart) === today) {
      note = d.etaStart <= now && (!d.etaEnd || now <= d.etaEnd) ? 'Could arrive any minute' : this._countdown(d.etaStart, now);
    }
    const late = daysBetween(today, day) < 0;
    return { main: late ? `Expected ${this._dayName(day, today)}` : `Arriving ${this._dayName(day, today)}`, sub: late ? 'Running late. The carrier hasn’t updated the date.' : sub, note };
  }

  _renderSheet(d, view) {
    const st = this._statusOf(d);
    const eta = this._etaFor(d, st, view);
    const stages = st.key === 'pickup' ? PICKUP_STAGES : STAGES;
    const cur = st.stage;
    const events = this._showAllEvents ? d.events : d.events.slice(0, 3);
    const multiple = this._entries.length > 1;
    const choices = this._payload?.icon_choices || [];
    return html`
      <div class="scrim" @click=${this._closeDetails}></div>
      <aside class="sheet" role="dialog" aria-modal="true" aria-labelledby="sheet-title" style="--c: var(${st.color})">
        <div class="sheet-bar"><span class="grab" aria-hidden="true"></span>
          <button class="icon-btn" aria-label="Close" @click=${this._closeDetails}>${uiIcon(ICON.close)}</button></div>
        <div class="sheet-body">
          <div class="sheet-hero">
            ${this._renderRing(d, st, 'lg')}
            <h2 id="sheet-title">${d.description}</h2>
            <span class="pill">${uiIcon(st.icon, 'xs')}${st.label}</span>
          </div>
          <div class="eta-card">
            <span class="em">${eta.main}</span>
            ${eta.sub ? html`<span class="es">${eta.sub}</span>` : nothing}
            ${eta.note ? html`<span class="ec">${eta.note}</span>` : nothing}
          </div>
          <ol class="journey" aria-label="Delivery progress">${stages.map(
            (s, i) => html`<li class="j ${i < cur || st.key === 'delivered' ? 'done' : ''} ${i === cur && st.key !== 'delivered' ? 'cur' : ''}">
              <span class="ji">${uiIcon(s.icon, 'sm')}</span><span>${s.label}</span></li>`,
          )}</ol>
          <section>
            <h3 class="sec-h">Updates</h3>
            ${d.events.length
              ? html`<ol class="timeline">${events.map((e) => {
                  const meta = [e.location, e.when ? this._when(e.when, view.today) : e.whenText].filter(Boolean).join(' · ');
                  return html`<li class="ev"><span class="b"></span><div>
                    <div class="e">${e.text}</div>
                    ${meta ? html`<div class="m">${meta}</div>` : nothing}
                    ${e.additional ? html`<div class="a">${e.additional}</div>` : nothing}</div></li>`;
                })}</ol>
                ${d.events.length > 3
                  ? html`<button class="btn text sm" @click=${() => { this._showAllEvents = !this._showAllEvents; }}>${this._showAllEvents ? 'Show fewer' : `Show all ${d.events.length} updates`}</button>`
                  : nothing}`
              : html`<p class="muted">No updates yet. The first one usually shows up within a few hours of the carrier scanning the package.</p>`}
          </section>
          <section>
            <h3 class="sec-h">Details</h3>
            <div class="facts">
              <div class="fact"><span class="fk">Carrier</span><span class="fv">${d.carrierName}</span></div>
              <div class="fact"><span class="fk">Tracking number</span><span class="fv mono">${d.trackingNumber}
                <button class="icon-btn tiny" aria-label="Copy tracking number" title="Copy tracking number" @click=${() => this._copy(d.trackingNumber)}>${uiIcon(ICON.copy, 'xs')}</button></span></div>
              ${multiple ? html`<div class="fact"><span class="fk">Parcel account</span><span class="fv">${d.entryTitle}</span></div>` : nothing}
              <div class="fact"><span class="fk">Icon · ${d.iconSource === 'user' ? 'your choice' : 'matched to the name'}</span><span class="fv">
                <button class="btn text sm" @click=${() => { this._iconsOpen = !this._iconsOpen; }}>${itemIcon(d.icon, 'sm')}${this._iconsOpen ? 'Done' : 'Change'}</button></span></div>
            </div>
            ${this._iconsOpen
              ? html`<div class="icon-row" role="group" aria-label="Choose an icon" style="margin-top: 12px">
                  ${choices.map((name) => html`<button class="ic-choice" aria-pressed=${String(name === d.icon)} aria-label=${ICON_LABELS[name] || name} title=${ICON_LABELS[name] || name}
                    @click=${() => this._setIcon(d, name)}>${itemIcon(name, 'sm')}</button>`)}
                  ${d.iconSource === 'user' ? html`<button class="btn text sm" @click=${() => this._setIcon(d, null)}>Match the name again</button>` : nothing}
                </div>`
              : nothing}
          </section>
        </div>
        <div class="sheet-foot">
          <button class="btn tonal" @click=${() => this._copy(d.trackingNumber)}>${uiIcon(ICON.copy, 'sm')}Copy number</button>
          <button class="btn danger-text" @click=${() => this._askDelete(d)}>${uiIcon(ICON.delete, 'sm')}Delete</button>
        </div>
      </aside>`;
  }

  _renderConfirm() {
    const d = this._confirmFor;
    const close = () => {
      if (!this._deleting) this._confirmFor = null;
    };
    if (!d.canDelete) {
      return html`<div class="scrim top" @click=${close}></div>
        <div class="dialog small" role="alertdialog" aria-modal="true" aria-labelledby="cf-title">
          <span class="cf-ic info">${uiIcon(ICON.info)}</span>
          <h2 id="cf-title">Connect your Parcel sign-in</h2>
          <p>Parcel’s API can’t delete packages, so Home Assistant uses your Parcel web sign-in for this. Add it once under Settings › Devices &amp; services › Parcel › Configure.
            <a href=${DELETE_HELP_URL} target="_blank" rel="noreferrer">How to find it</a></p>
          <div class="actions"><button class="btn filled" @click=${close}>Got it</button></div>
        </div>`;
    }
    return html`<div class="scrim top" @click=${close}></div>
      <div class="dialog small" role="alertdialog" aria-modal="true" aria-labelledby="cf-title">
        <span class="cf-ic">${uiIcon(ICON.delete)}</span>
        <h2 id="cf-title">Delete “${d.description}”?</h2>
        <p>It will be removed from Parcel on all your devices. This can’t be undone.</p>
        <div class="actions">
          <button class="btn text" ?disabled=${this._deleting} @click=${close}>Cancel</button>
          <button class="btn danger" ?disabled=${this._deleting} @click=${() => this._doDelete(d)}>${this._deleting ? 'Deleting…' : 'Delete'}</button>
        </div>
      </div>`;
  }

  _renderEmpty() {
    return html`<section class="empty">
      <div class="empty-art" aria-hidden="true"><span class="halo"></span><span class="halo two"></span><span class="box">${uiIcon(ICON.empty)}</span></div>
      <h2>No packages on the way</h2>
      <p>Paste a tracking number to start following a delivery. Packages you add in the Parcel app show up here too.</p>
      <button class="btn filled lg" @click=${this._openAdd}>${uiIcon(ICON.plus, 'sm')}Add a package</button>
    </section>`;
  }

  _renderCarrierCombo(f, detected, info) {
    const options = this._carrierOptions(f.carrierQuery, detected);
    const total = Object.keys(this._carriers?.list || {}).length;
    return html`<div class="field">
      <label for="f-carrier">Carrier</label>
      <div class="combo-wrap">
        <input id="f-carrier" class="input" role="combobox" aria-expanded=${String(f.carrierOpen)} aria-controls="carrier-list" aria-autocomplete="list" autocomplete="off"
          placeholder=${total ? `Search ${total} carriers` : 'Loading carriers…'}
          .value=${f.carrierOpen ? f.carrierQuery : info?.name ?? ''}
          @focus=${() => this._setForm({ carrierOpen: true, carrierQuery: '', active: 0 })}
          @blur=${() => this._setForm({ carrierOpen: false })}
          @input=${(e) => this._setForm({ carrierQuery: e.target.value, carrierOpen: true, active: 0 })}
          @keydown=${(e) => this._onComboKey(e, options)}>
        ${uiIcon(ICON.chevronDown, 'sm caret')}
      </div>
      ${f.carrierOpen
        ? html`<div class="combo-list" id="carrier-list" role="listbox" @mousedown=${(e) => e.preventDefault()}>
            ${options.items.length
              ? options.items.map(
                  (o, i) => html`${o.heading ? html`<div class="opt-head">${o.heading}</div>` : nothing}
                    <div class="opt" role="option" aria-selected=${String(i === f.active)} @click=${() => this._pickCarrier(o.code)}><span>${o.name}</span><span class="code">${o.code}</span></div>`,
                )
              : html`<div class="opt-empty">${total ? `No carrier matches “${f.carrierQuery}”.` : this._carriers?.error || 'Loading carriers…'}</div>`}
            ${options.more ? html`<div class="opt-empty">Type to search ${options.more} more.</div>` : nothing}
          </div>`
        : nothing}
    </div>`;
  }

  _renderAdd() {
    const f = this._form;
    const entries = this._entries;
    const number = cleanNumber(f.number);
    const detected = number.length >= 6 ? this._detect(number) : [];
    const carrier = f.carrier || detected[0] || '';
    const list = this._carriers?.list || {};
    const info = list[carrier];
    const extra = info?.extra ? EXTRA[info.extra] || EXTRA[1] : null;
    const mismatch = Boolean(f.carrier && detected.length && !detected.includes(f.carrier));
    const guessed = this._guessIcon(f.description);
    const chosenIcon = f.icon || guessed;
    const choices = [guessed, ...(this._payload?.icon_choices || []).filter((c) => c !== guessed)].slice(0, 9);
    if (f.icon && !choices.includes(f.icon)) choices[choices.length - 1] = f.icon;
    const entry = entries.find((e) => e.entry_id === f.entryId) || entries[0];
    const addsLeft = entry?.adds_left ?? 20;
    const ok = number.length >= 5 && Boolean(carrier) && f.description.trim().length > 0 && (!extra || f.extra.trim().length > 0) && addsLeft > 0;
    const ctx = { number: f.number.replace(/\s+/g, ''), carrier, valid: ok, entryId: entry?.entry_id };
    const showChip = carrier && !f.carrierEditing;

    return html`
      <div class="scrim top" @click=${this._closeAdd}></div>
      <form class="dialog" role="dialog" aria-modal="true" aria-labelledby="add-title" novalidate @submit=${(e) => this._submitAdd(e, ctx)}>
        <header>
          <div><h2 id="add-title">Add a package</h2><p class="dsub">Paste a tracking number and give it a name.</p></div>
          <button type="button" class="icon-btn" aria-label="Close" @click=${this._closeAdd}>${uiIcon(ICON.close)}</button>
        </header>
        <div class="form">
          ${f.error ? html`<div class="form-error" role="alert">${uiIcon(ICON.warn, 'sm')}<span>${f.error}</span></div>` : nothing}
          ${entries.length > 1
            ? html`<div class="field"><label for="f-entry">Parcel account</label>
                <select id="f-entry" class="input" .value=${entry?.entry_id || ''} @change=${(e) => this._setForm({ entryId: e.target.value })}>
                  ${entries.map((e) => html`<option value=${e.entry_id}>${e.title}</option>`)}
                </select></div>`
            : nothing}
          <div class="field">
            <label for="f-number">${extra?.number || 'Tracking number'}</label>
            <input id="f-number" class="input xl mono" autocomplete="off" autocapitalize="characters" spellcheck="false"
              placeholder="1Z 999 AA1 01 2345 6784" .value=${f.number}
              @input=${(e) => this._setForm({ number: e.target.value, carrier: '', carrierEditing: false, extra: '', error: '' })}>
          </div>
          ${number.length < 6
            ? html`<p class="help">The carrier is recognized from the number. Parcel supports ${Object.keys(list).length || 'hundreds of'} carriers.</p>`
            : showChip
              ? html`<div class="carrier-row ${mismatch ? 'warn' : ''}">
                  ${uiIcon(mismatch ? ICON.warn : ICON.checkCircle, 'sm')}
                  <span class="cr-text"><span>${f.carrier ? 'Carrier: ' : 'Looks like '}<b>${this._carrierName(carrier)}</b></span>
                    ${mismatch ? html`<span class="cr-warn">This number doesn’t match the usual format. Rejected tries still count toward today’s limit.</span>` : nothing}</span>
                  <button type="button" class="btn text sm" @click=${() => { this._setForm({ carrierEditing: true }); this.updateComplete.then(() => this.renderRoot.querySelector('#f-carrier')?.focus()); }}>Change</button>
                </div>`
              : this._renderCarrierCombo(f, detected, info)}
          ${extra
            ? html`<div class="field">
                <label for="f-extra">${extra.label}</label>
                <input id="f-extra" class="input" type=${extra.type} autocomplete=${extra.autocomplete} placeholder=${extra.placeholder}
                  .value=${f.extra} @input=${(e) => this._setForm({ extra: e.target.value })}>
                <p class="help">${this._carrierName(carrier)} needs this to look up the package.</p>
              </div>`
            : nothing}
          <div class="field">
            <label for="f-desc">Name</label>
            <div class="desc-row">
              <span class="desc-av" aria-hidden="true">${itemIcon(chosenIcon)}</span>
              <input id="f-desc" class="input" maxlength="80" placeholder="e.g. Coffee grinder"
                .value=${f.description} @input=${(e) => this._setForm({ description: e.target.value })}>
            </div>
            <div class="icon-row" role="group" aria-label="Icon">${choices.map(
              (name) => html`<button type="button" class="ic-choice" aria-pressed=${String(name === chosenIcon)} aria-label=${ICON_LABELS[name] || name} title=${ICON_LABELS[name] || name}
                @click=${() => this._setForm({ icon: name })}>${itemIcon(name, 'sm')}</button>`,
            )}</div>
            <p class="help">Shown here and in the Parcel app. The icon is matched to words in the name; pick another if it doesn’t fit.</p>
          </div>
          <label class="toggle-row" for="f-push">
            <span><span class="toggle-title">Confirm on my phone</span>
              <span class="help">Parcel sends a notification to your devices when the package is added.</span></span>
            <input id="f-push" type="checkbox" class="switch" .checked=${f.push} @change=${(e) => this._setForm({ push: e.target.checked })}>
          </label>
        </div>
        <footer>
          <span class="quota" title="Parcel allows 20 new packages a day through its API, rejected tries included.">${addsLeft} of ${entry?.adds_limit ?? 20} adds left today</span>
          <button type="button" class="btn text" @click=${this._closeAdd}>Cancel</button>
          <button type="submit" class="btn filled" ?disabled=${!ok || f.submitting}>${f.submitting ? 'Adding…' : 'Start tracking'}</button>
        </footer>
      </form>`;
  }
}

if (!customElements.get('parcel-packages-panel')) {
  customElements.define('parcel-packages-panel', ParcelPackagesPanel);
}
