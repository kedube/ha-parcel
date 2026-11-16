// The Packages sidebar panel for the Parcel integration: how everything is drawn.
// What is shown is worked out in logic.js.
import { LitElement, html, nothing, svg } from 'lit';
import { copyText } from './clipboard.js';
import { makeFormat, toDate } from './format.js';
import { ICON, ICON_LABELS, itemIconPath } from './icons.js';
import {
  EXTRA,
  FOCUSABLE,
  GROUPS,
  ORDER,
  PICKUP_STAGES,
  STAGES,
  ago,
  badgeOf,
  carrierOptions,
  cleanNumber,
  compileRules,
  detectCarriers,
  etaFor,
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
  whenText,
} from './logic.js';
import { styles } from './styles.js';

const DELETE_HELP_URL = 'https://github.com/kedube/ha-parcel#let-home-assistant-delete-packages';

const uiIcon = (path, cls = '') =>
  html`<svg class="ic ${cls}" viewBox="0 0 24 24" aria-hidden="true" focusable="false"><path d=${path}></path></svg>`;
const itemIcon = (name, cls = '') => uiIcon(itemIconPath(name), cls);

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
    this._onReconnect = this._onReconnect.bind(this);
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
      // Keeps "updated 3 min ago" and the timeline current, and tries the
      // connection again if subscribing failed (for example while Parcel was loading).
      this._tick += 1;
      this._subscribe();
    }, 30000);
    this._subscribe();
  }

  disconnectedCallback() {
    super.disconnectedCallback();
    window.removeEventListener('keydown', this._onKey);
    window.removeEventListener('click', this._onDocClick);
    clearInterval(this._timer);
    clearTimeout(this._toastTimer);
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
    if (changed.has('panel')) this._iconRules = compileRules(this.panel?.config?.icon_rules);
    if (changed.has('_payload')) {
      this._items = normalizePayload(this._payload);
      // A package that has gone (deleted elsewhere, or delivered long ago) closes what was open for it.
      const uids = new Set(this._items.map((d) => d.uid));
      if (this._selectedUid && !uids.has(this._selectedUid)) this._selectedUid = null;
      if (this._menuFor && !uids.has(this._menuFor)) this._menuFor = null;
    }
  }

  updated(changed) {
    if (changed.has('hass')) {
      this.toggleAttribute('dark', Boolean(this.hass?.themes?.darkMode));
      this._subscribe();
    }
  }

  _subscribe() {
    if (this._unsub || !this.hass || !this.isConnected) return;
    const connection = this.hass.connection;
    if (this._connection !== connection) {
      this._connection?.removeEventListener('ready', this._onReconnect);
      connection.addEventListener('ready', this._onReconnect);
      this._connection = connection;
    }
    // Not resubscribe: after Home Assistant restarts, the browser reconnects before
    // this integration has loaded, and a repeat the library makes then fails without
    // telling anyone. _onReconnect subscribes afresh instead, and a failure is retried
    // on the 30-second tick.
    this._unsub = connection
      .subscribeMessage(
        (payload) => {
          this._subError = '';
          this._payload = payload;
        },
        { type: 'parcel/subscribe' },
        { resubscribe: false },
      )
      .catch((err) => {
        this._subError = err?.message || 'Couldn’t load packages';
        this._unsub = undefined;
      });
  }

  /** The connection came back: the old subscription ended with the old connection. */
  _onReconnect() {
    // Its unsubscribe would now name another subscription on the new connection,
    // so it is dropped rather than called.
    this._unsub = undefined;
    this._subscribe();
  }

  _unsubscribe() {
    this._connection?.removeEventListener('ready', this._onReconnect);
    this._connection = undefined;
    if (!this._unsub) return;
    this._unsub.then((unsub) => unsub?.()).catch(() => {});
    this._unsub = undefined;
  }

  get _entries() {
    return this._payload?.entries || [];
  }

  get _iconChoices() {
    return this.panel?.config?.icon_choices || [];
  }

  // ---------------------------------------------------------------- keyboard

  /** The dialog on top, if one is open: Tab stays inside it. */
  _modal() {
    if (this._confirmFor) return this.renderRoot.querySelector('.dialog.small');
    if (this._addOpen) return this.renderRoot.querySelector('form.dialog');
    if (this._selectedUid) return this.renderRoot.querySelector('.sheet');
    return null;
  }

  _onKey(e) {
    if (e.key === 'Tab') {
      const modal = this._modal();
      if (!modal) return;
      const focusables = [...modal.querySelectorAll(FOCUSABLE)].filter((el) => el.getClientRects().length > 0);
      const next = trapFocus(focusables, this.renderRoot.activeElement, e.shiftKey);
      if (next || !focusables.length) {
        e.preventDefault();
        next?.focus();
      }
      return;
    }
    if (e.key !== 'Escape') return;
    if (this._confirmFor) this._closeConfirm();
    else if (this._addOpen && this._form.carrierOpen) this._setForm({ carrierOpen: false });
    else if (this._addOpen) this._closeAdd();
    else if (this._selectedUid) this._closeDetails();
    else if (this._menuFor) this._menuFor = null;
    else if (this._searchOpen) {
      this._query = '';
      this._searchOpen = false;
    }
  }

  /** Put focus back where it was once the page behind a dialog can take it again. */
  _restoreFocus(target) {
    this.updateComplete.then(() => target?.focus?.());
  }

  // ---------------------------------------------------------------- actions

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
    const focused = this.renderRoot.activeElement;
    const copied = await copyText(text);
    focused?.focus?.();
    this._showToast(copied ? 'Tracking number copied' : `Couldn’t copy automatically. The number is ${text}`);
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
    this._restoreFocus(this._lastFocus);
  }

  _askDelete(d) {
    this._confirmFocus = this.renderRoot.activeElement || document.activeElement;
    this._menuFor = null;
    this._confirmFor = d;
    // Start on the safe choice.
    this.updateComplete.then(() => this.renderRoot.querySelector('.dialog.small .btn')?.focus());
  }

  _closeConfirm() {
    if (this._deleting) return;
    this._confirmFor = null;
    this._restoreFocus(this._confirmFocus);
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
        detect: compileRules(result.detect, ''),
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
    this._restoreFocus(this._lastFocus);
  }

  _carrierName(code) {
    return this._carriers?.list?.[code]?.name || code.toUpperCase();
  }

  _pickCarrier(code) {
    this._setForm({ carrier: code, carrierEditing: false, carrierOpen: false, carrierQuery: '', extra: '' });
    this.updateComplete.then(() => this.renderRoot.querySelector('#f-desc')?.focus());
  }

  _onComboKey(e, options) {
    const n = options.items.length;
    if (!n) return;
    const showActive = () =>
      this.updateComplete.then(() => this.renderRoot.querySelector('.opt[aria-selected="true"]')?.scrollIntoView({ block: 'nearest' }));
    if (e.key === 'ArrowDown') {
      e.preventDefault();
      this._setForm({ active: (this._form.active + 1) % n, carrierOpen: true });
      showActive();
    } else if (e.key === 'ArrowUp') {
      e.preventDefault();
      this._setForm({ active: (this._form.active - 1 + n) % n });
      showActive();
    } else if (e.key === 'Enter' && this._form.carrierOpen) {
      e.preventDefault();
      this._pickCarrier(options.items[Math.min(this._form.active, n - 1)].code);
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
    const g = grouped(this._items, today, this._fmt);
    const selected = this._selectedUid ? this._items.find((d) => d.uid === this._selectedUid) : null;
    // While a dialog is open, the page behind it can't be reached with the keyboard.
    const behind = Boolean(selected || this._addOpen || this._confirmFor);

    let body;
    if (this._subError && !this._payload) body = html`<div class="banner">${uiIcon(ICON.warn)}<span>${this._subError}</span></div>`;
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
      <header class="appbar ${this._searchOpen ? 'searching' : ''}" ?inert=${behind}>
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
            ${this._refreshing ? 'Checking…' : `Updated ${ago(updatedAt, now)}`}</span>` : nothing}
          <button class="icon-btn ${this._refreshing ? 'spin' : ''}" aria-label="Check Parcel for updates" title="Check Parcel for updates" @click=${this._refresh}>${uiIcon(ICON.refresh)}</button>
        </div>
      </header>
      <main class="main" ?inert=${behind}>
        ${this._subError && this._payload
          ? html`<div class="banner" role="status">${uiIcon(ICON.warn)}<span>Lost touch with Home Assistant, so this may be out of date. Trying again…</span></div>`
          : nothing}
        ${errors.map((e) => html`<div class="banner" role="status">${uiIcon(ICON.warn)}<span>${entries.length > 1 ? `${e.title}: ` : ''}${e.last_error}</span></div>`)}
        ${paused.map((e) => html`<div class="banner info" role="status">${uiIcon(ICON.info)}<span>${entries.length > 1 ? `${e.title}: ` : ''}Parcel asked Home Assistant to slow down. This is the last update it has; it will check again around ${this._fmt.time(toDate(e.paused_until))}.</span></div>`)}
        ${body}
      </main>
      ${entries.length ? html`<button class="fab" ?inert=${behind} @click=${this._openAdd}>${uiIcon(ICON.plus)}<span>Add package</span></button>` : nothing}
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
    const hero = heroModel(g, view);
    let headline;
    if (hero.kind === 'today') {
      const one = hero.count === 1;
      headline = html`<span class="n">${hero.count} ${one ? 'package' : 'packages'}</span> ${one ? 'arrives' : 'arrive'} today`;
    } else if (hero.kind === 'delivered') headline = html`<span class="n">Today’s deliveries</span> are in`;
    else headline = html`Nothing arriving today`;

    return html`<section class="hero" aria-labelledby="hero-h" style="--c: var(${hero.color})">
      <div class="hero-top">
        <div>
          <div class="greet">${this._greeting(now)}</div>
          <h2 class="hero-h" id="hero-h">${headline}</h2>
          <p class="hero-sub">${hero.sub}</p>
        </div>
        <div class="cal" aria-hidden="true">
          <span class="dow">${fmt.weekday(today, 'short')}</span>
          <span class="dom">${fmt.dayNumber(today)}</span>
          <span class="mon">${fmt.monthShort(today)}</span>
        </div>
      </div>
      ${this._renderRoad(hero.todays, hero.deliveredToday, view)}
      ${hero.stats.length
        ? html`<div class="hero-stats">${hero.stats.map((s) => html`
            <button class="stat" style="--c: var(${s.color})" @click=${() => this._scrollTo(s.target)}><span class="sn">${s.n}</span>${s.label}</button>`)}</div>`
        : nothing}
    </section>`;
  }

  _renderRoad(todays, deliveredToday, view) {
    const road = roadLayout(todays, deliveredToday, view);
    if (!road) return nothing;
    const { pins, anytime } = road;
    return html`<div class="road-wrap" style="--lanes: ${road.lanes}">
      ${pins.length
        ? html`
          <div class="pins">
            ${pins.map((p) => html`<button class="pin ${p.x < 14 ? 'edge-l' : p.x > 86 ? 'edge-r' : ''} ${p.done ? 'done' : ''}"
                style="left: ${p.x}%; --lane: ${p.lane}; --c: var(${p.st.color})" aria-label="${p.d.description}, ${p.label}"
                @click=${() => this._openDetails(p.d)}>
              <span class="tip">${p.d.description} · ${p.label}</span>
              <span class="pin-av">${itemIcon(p.d.icon)}${p.done ? html`<span class="pin-check">${uiIcon(ICON.check, 'xxs')}</span>` : nothing}</span>
              <span class="stem"></span>
            </button>`)}
          </div>
          <div class="road" aria-hidden="true">
            ${road.bands.map((b) => html`<span class="band" style="left: ${b.left}%; width: ${b.width}%; --c: var(${b.color})"></span>`)}
            <span class="now-truck" style="left: ${road.nowLeft}%" title="Now, ${view.fmt.time(view.now)}">${uiIcon(ICON.truckNow, 'xs')}</span>
          </div>
          <div class="hours" aria-hidden="true">
            ${road.ticks.map((t) => (t.hidden ? nothing : html`<span class="tick" style="left: ${t.left}%">${t.label}</span>`))}
            <span class="now-lab" style="left: ${road.nowLeft}%">Now</span>
          </div>`
        : nothing}
      ${anytime.length
        ? html`<div class="anytime"><span class="any-label">Any time today:</span>
            ${anytime.map((d) => html`<button class="any-chip" style="--c: var(${statusOf(d).color})" @click=${() => this._openDetails(d)}>
              <span class="any-av">${itemIcon(d.icon, 'xs')}</span><span class="any-name">${d.description}</span></button>`)}</div>`
        : nothing}
    </div>`;
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
        const st = statusOf(d);
        const r = reasonOf(d, st, view);
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
    const list = this._items.filter((d) => matches(d, this._query));
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

  _renderCard(d, view) {
    const st = statusOf(d);
    const b = badgeOf(d, st, view);
    const menuOpen = this._menuFor === d.uid;
    // The card holds two controls side by side: one opens the details, one opens the menu.
    return html`<article class="pkg ${st.key} ${menuOpen ? 'menu-open' : ''}" style="--c: var(${st.color})">
      <button class="pkg-open" aria-label="${d.description}: ${st.label}. ${b.main} ${b.sub}. Show details" @click=${() => this._openDetails(d)}>
        ${this._renderRing(d, st)}
        <span class="pkg-main">
          <span class="pkg-name">${d.description}</span>
          <span class="pkg-status">${uiIcon(ICON[st.icon], 'xs')}${st.label}</span>
          <span class="pkg-meta">${metaOf(d, view)}</span>
        </span>
        <span class="when"><span class="when-main">${b.main}</span>${b.sub ? html`<span class="when-sub">${b.sub}</span>` : nothing}</span>
      </button>
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

  _renderSheet(d, view) {
    const st = statusOf(d);
    const eta = etaFor(d, st, view);
    const stages = st.key === 'pickup' ? PICKUP_STAGES : STAGES;
    const cur = st.stage;
    const events = this._showAllEvents ? d.events : d.events.slice(0, 3);
    const multiple = this._entries.length > 1;
    return html`
      <div class="scrim" @click=${this._closeDetails}></div>
      <aside class="sheet" role="dialog" aria-modal="true" aria-labelledby="sheet-title" style="--c: var(${st.color})" ?inert=${Boolean(this._confirmFor)}>
        <div class="sheet-bar"><span class="grab" aria-hidden="true"></span>
          <button class="icon-btn" aria-label="Close" @click=${this._closeDetails}>${uiIcon(ICON.close)}</button></div>
        <div class="sheet-body">
          <div class="sheet-hero">
            ${this._renderRing(d, st, 'lg')}
            <h2 id="sheet-title">${d.description}</h2>
            <span class="pill">${uiIcon(ICON[st.icon], 'xs')}${st.label}</span>
          </div>
          <div class="eta-card">
            <span class="em">${eta.main}</span>
            ${eta.sub ? html`<span class="es">${eta.sub}</span>` : nothing}
            ${eta.note ? html`<span class="ec">${eta.note}</span>` : nothing}
          </div>
          <ol class="journey" aria-label="Delivery progress">${stages.map(
            (s, i) => html`<li class="j ${i < cur || st.key === 'delivered' ? 'done' : ''} ${i === cur && st.key !== 'delivered' ? 'cur' : ''}">
              <span class="ji">${uiIcon(ICON[s.icon], 'sm')}</span><span>${s.label}</span></li>`,
          )}</ol>
          <section>
            <h3 class="sec-h">Updates</h3>
            ${d.events.length
              ? html`<ol class="timeline">${events.map((e) => {
                  const meta = [e.location, e.when ? whenText(view.fmt, e.when, view.today) : e.whenText].filter(Boolean).join(' · ');
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
                  ${this._iconChoices.map((name) => html`<button class="ic-choice" aria-pressed=${String(name === d.icon)} aria-label=${ICON_LABELS[name] || name} title=${ICON_LABELS[name] || name}
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
    if (!d.canDelete) {
      return html`<div class="scrim top" @click=${this._closeConfirm}></div>
        <div class="dialog small" role="alertdialog" aria-modal="true" aria-labelledby="cf-title">
          <span class="cf-ic info">${uiIcon(ICON.info)}</span>
          <h2 id="cf-title">Connect your Parcel sign-in</h2>
          <p>Parcel’s API can’t delete packages, so Home Assistant uses your Parcel web sign-in for this. Add it once under Settings › Devices &amp; services › Parcel › Configure.
            <a href=${DELETE_HELP_URL} target="_blank" rel="noreferrer">How to find it</a></p>
          <div class="actions"><button class="btn filled" @click=${this._closeConfirm}>Got it</button></div>
        </div>`;
    }
    return html`<div class="scrim top" @click=${this._closeConfirm}></div>
      <div class="dialog small" role="alertdialog" aria-modal="true" aria-labelledby="cf-title">
        <span class="cf-ic">${uiIcon(ICON.delete)}</span>
        <h2 id="cf-title">Delete “${d.description}”?</h2>
        <p>It will be removed from Parcel on all your devices. This can’t be undone.</p>
        <div class="actions">
          <button class="btn text" ?disabled=${this._deleting} @click=${this._closeConfirm}>Cancel</button>
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
    const options = carrierOptions(this._carriers, f.carrierQuery, detected);
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
    const detected = number.length >= 6 ? detectCarriers(this._carriers, number) : [];
    const carrier = f.carrier || detected[0] || '';
    const list = this._carriers?.list || {};
    const info = list[carrier];
    const extra = info?.extra ? EXTRA[info.extra] || EXTRA[1] : null;
    const mismatch = Boolean(f.carrier && detected.length && !detected.includes(f.carrier));
    const guessed = guessIcon(this._iconRules, f.description);
    const chosenIcon = f.icon || guessed;
    const choices = [guessed, ...this._iconChoices.filter((c) => c !== guessed)].slice(0, 9);
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
                  ${entries.map((e) => html`<option value=${e.entry_id} ?selected=${e.entry_id === entry?.entry_id}>${e.title}</option>`)}
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
