import { css } from 'lit';

// Layout: a friendly delivery-day planner. A hero card shows today's deliveries as stops on a to-scale
// "road", a callout lists anything that needs a look, then packages are grouped by when they arrive.
// Colors come from the person's Home Assistant theme; status colors are semantic and adapt to dark themes.
export const styles = css`
  :host {
    --pp-primary: var(--primary-color, #03a9f4);
    --pp-on-primary: var(--text-primary-color, #ffffff);
    --pp-bg: var(--primary-background-color, #fafafa);
    --pp-card: var(--card-background-color, var(--ha-card-background, #ffffff));
    --pp-text: var(--primary-text-color, #212121);
    --pp-text2: var(--secondary-text-color, #727272);
    --pp-text3: var(--disabled-text-color, #a0a0a0);
    --pp-line: var(--divider-color, rgba(0, 0, 0, 0.12));
    --pp-surface: var(--secondary-background-color, #e5e5e5);
    --pp-surface2: color-mix(in srgb, var(--pp-text) 4%, var(--pp-card));
    --pp-card-line: color-mix(in srgb, var(--pp-text) 9%, var(--pp-card));
    --pp-ring-off: color-mix(in srgb, var(--pp-text) 12%, var(--pp-card));
    --pp-road: color-mix(in srgb, var(--pp-text) 9%, var(--pp-card));
    --pp-road-dash: var(--pp-card);
    --pp-hover: color-mix(in srgb, var(--pp-text) 7%, transparent);
    --pp-selected: color-mix(in srgb, var(--pp-primary) 12%, var(--pp-card));
    --pp-disabled-bg: color-mix(in srgb, var(--pp-text) 10%, transparent);
    --pp-input-bg: color-mix(in srgb, var(--pp-text) 3%, var(--pp-card));
    --pp-input-line: color-mix(in srgb, var(--pp-text) 22%, var(--pp-card));
    --pp-switch-off: color-mix(in srgb, var(--pp-text) 25%, var(--pp-card));
    --pp-hero-top: color-mix(in srgb, var(--pp-primary) 10%, var(--pp-card));
    --pp-scrim: rgba(0, 0, 0, 0.42);
    --pp-toast-bg: var(--pp-text);
    --pp-toast-fg: var(--pp-card);
    --pp-danger: var(--error-color, #db4437);
    --pp-on-danger: #ffffff;
    --pp-shadow-1: 0 1px 2px rgba(21, 27, 34, 0.05), 0 4px 14px rgba(21, 27, 34, 0.06);
    --pp-shadow-2: 0 2px 6px rgba(21, 27, 34, 0.07), 0 14px 32px rgba(21, 27, 34, 0.11);
    --st-pre: #5f6d7b;
    --st-transit: #4855d4;
    --st-out: #0b7a6e;
    --st-pickup: #8546d6;
    --st-failed: #c2410c;
    --st-attention: #d42a2a;
    --st-delivered: #237a3b;
    --st-muted: #6f7a85;
    --font-body: var(--ha-font-family-body, Roboto, 'Noto Sans', 'Helvetica Neue', Arial, sans-serif);
    --font-display: 'Parcel Outfit', var(--font-body);
    --font-mono: var(--ha-font-family-code, 'Roboto Mono', ui-monospace, Menlo, Consolas, monospace);
    --r-lg: 24px;
    --r-md: 18px;
    display: block;
    min-height: 100%;
    background: var(--pp-bg);
    color: var(--pp-text);
    font-family: var(--font-body);
    font-size: 14px;
    line-height: 1.45;
    -webkit-font-smoothing: antialiased;
  }
  :host([dark]) {
    --pp-scrim: rgba(0, 0, 0, 0.58);
    --pp-shadow-1: 0 1px 2px rgba(0, 0, 0, 0.4), 0 4px 14px rgba(0, 0, 0, 0.25);
    --pp-shadow-2: 0 2px 6px rgba(0, 0, 0, 0.45), 0 14px 32px rgba(0, 0, 0, 0.4);
    --st-pre: #a3b3c2;
    --st-transit: #9aa6ff;
    --st-out: #52d6c4;
    --st-pickup: #c4a0ff;
    --st-failed: #ff9d5c;
    --st-attention: #ff7373;
    --st-delivered: #74d68e;
    --st-muted: #94a0ab;
  }
  * { box-sizing: border-box; }
  button, input, select { font: inherit; color: inherit; }
  button { cursor: pointer; }
  h1, h2, h3, p { margin: 0; }
  a { color: var(--pp-primary); }
  .ic { width: 24px; height: 24px; fill: currentColor; flex: none; }
  .ic.sm { width: 20px; height: 20px; }
  .ic.xs { width: 16px; height: 16px; }
  .ic.xxs { width: 12px; height: 12px; }
  :focus-visible { outline: 2px solid var(--pp-primary); outline-offset: 2px; }
  .muted { color: var(--pp-text2); }

  /* Top bar */
  .appbar {
    position: sticky; top: 0; z-index: 8;
    background: var(--app-header-background-color, var(--pp-bg));
    color: var(--app-header-text-color, var(--pp-text));
    border-bottom: var(--app-header-border-bottom, 1px solid var(--pp-line));
  }
  .appbar-inner { display: flex; align-items: center; gap: 4px; height: var(--header-height, 56px); padding: 0 12px 0 16px; }
  .appbar h1 { margin-left: 4px; font-size: 20px; font-weight: 400; white-space: nowrap; }
  .spacer { flex: 1; }
  .updated { margin-left: 6px; font-size: 12px; color: var(--pp-text2); white-space: nowrap; }
  .icon-btn {
    width: 40px; height: 40px; flex: none; display: inline-grid; place-items: center;
    border: 0; border-radius: 50%; background: none; color: inherit; opacity: 0.85;
  }
  .icon-btn:hover { background: var(--pp-hover); opacity: 1; }
  .icon-btn.tiny { width: 30px; height: 30px; color: var(--pp-text2); }
  .icon-btn.spin .ic { animation: spin 0.9s linear infinite; }
  @keyframes spin { to { transform: rotate(360deg); } }
  .search {
    display: flex; align-items: center; gap: 6px; height: 40px; width: min(340px, 100%);
    padding: 0 4px 0 12px; border-radius: 999px; color: var(--pp-text2);
    background: var(--pp-card); box-shadow: var(--pp-shadow-1);
  }
  .search input { flex: 1; min-width: 0; border: 0; background: none; outline: none; color: var(--pp-text); font-size: 14px; }
  .search input::-webkit-search-cancel-button { display: none; }
  @media (max-width: 600px) {
    .updated { display: none; }
    .appbar.searching h1, .appbar.searching .spacer { display: none; }
    .appbar.searching .search { flex: 1; width: auto; }
  }

  /* Page */
  .main {
    max-width: 880px; margin: 0 auto; display: flex; flex-direction: column; gap: 28px;
    padding: 24px 16px 132px; overflow-x: clip;
  }
  .banner {
    display: flex; align-items: flex-start; gap: 12px; padding: 14px 16px; border-radius: 14px;
    background: color-mix(in srgb, var(--st-failed) 9%, var(--pp-card)); color: var(--pp-text);
    border: 1px solid color-mix(in srgb, var(--st-failed) 25%, var(--pp-card-line));
  }
  .banner .ic { color: var(--st-failed); }
  .banner.info {
    background: color-mix(in srgb, var(--pp-primary) 8%, var(--pp-card));
    border-color: color-mix(in srgb, var(--pp-primary) 24%, var(--pp-card-line));
  }
  .banner.info .ic { color: var(--pp-primary); }
  .loading { padding: 64px 16px; text-align: center; color: var(--pp-text2); }

  /* Hero */
  .hero {
    position: relative; padding: 26px 26px 22px; border-radius: var(--r-lg);
    background: linear-gradient(180deg, var(--pp-hero-top), var(--pp-card) 72%);
    border: 1px solid var(--pp-card-line); box-shadow: var(--pp-shadow-1);
  }
  .hero-top { display: flex; align-items: flex-start; justify-content: space-between; gap: 20px; }
  .greet { font-size: 14px; font-weight: 500; color: var(--pp-text2); }
  .hero-h { margin-top: 6px; font: 600 clamp(28px, 5.2vw, 42px) / 1.06 var(--font-display); letter-spacing: -0.025em; text-wrap: balance; }
  .hero-h .n { color: var(--c, var(--pp-text)); }
  .hero-sub { margin-top: 10px; max-width: 46ch; font-size: 15px; color: var(--pp-text2); }
  .cal {
    flex: none; display: grid; justify-items: center; width: 74px; padding: 9px 0 10px; border-radius: 18px;
    background: var(--pp-card); border: 1px solid var(--pp-card-line); box-shadow: var(--pp-shadow-1);
  }
  .cal .dow { font-size: 11px; font-weight: 600; letter-spacing: 0.1em; text-transform: uppercase; color: var(--pp-primary); }
  .cal .dom { margin-top: 4px; font: 600 32px / 1.05 var(--font-display); font-variant-numeric: tabular-nums; }
  .cal .mon { font-size: 11px; letter-spacing: 0.08em; text-transform: uppercase; color: var(--pp-text2); }
  @media (max-width: 560px) {
    .hero { padding: 20px 16px 18px; }
    .cal { display: none; }
  }
  .road-wrap { position: relative; margin-top: 22px; padding: 0 18px; }
  .pins { position: relative; height: calc(46px + (var(--lanes) - 1) * 40px); }
  .pin { position: absolute; bottom: 0; transform: translateX(-50%); display: flex; flex-direction: column; align-items: center; padding: 0; border: 0; background: none; }
  .pin-av {
    position: relative; width: 38px; height: 38px; border-radius: 50%; display: grid; place-items: center;
    background: color-mix(in srgb, var(--c) 16%, var(--pp-card)); color: var(--c);
    box-shadow: 0 0 0 3px var(--pp-card), var(--pp-shadow-1); transition: transform 0.15s ease;
  }
  .pin-av .ic { width: 20px; height: 20px; }
  .pin:hover .pin-av, .pin:focus-visible .pin-av { transform: translateY(-2px) scale(1.06); }
  .pin.done .pin-av { background: color-mix(in srgb, var(--st-delivered) 14%, var(--pp-card)); color: var(--st-delivered); }
  .pin-check {
    position: absolute; right: -4px; bottom: -4px; width: 16px; height: 16px; border-radius: 50%; display: grid; place-items: center;
    background: var(--st-delivered); color: var(--pp-card); box-shadow: 0 0 0 2px var(--pp-card);
  }
  .stem { width: 2px; height: calc(8px + var(--lane) * 40px); border-radius: 2px; background: color-mix(in srgb, var(--c) 45%, transparent); }
  .tip {
    position: absolute; bottom: calc(100% + 8px); left: 50%; transform: translateX(-50%); z-index: 3;
    padding: 6px 10px; border-radius: 8px; white-space: nowrap; pointer-events: none;
    background: var(--pp-toast-bg); color: var(--pp-toast-fg); font-size: 12px; font-weight: 500; opacity: 0; transition: opacity 0.12s ease;
  }
  .pin.edge-l .tip { left: -8px; transform: none; }
  .pin.edge-r .tip { left: auto; right: -8px; transform: none; }
  .pin:hover .tip, .pin:focus-visible .tip { opacity: 1; }
  .road { position: relative; height: 14px; border-radius: 7px; background: var(--pp-road); }
  .road::after {
    content: ''; position: absolute; left: 10px; right: 10px; top: 6px; height: 2px;
    background: repeating-linear-gradient(to right, var(--pp-road-dash) 0 10px, transparent 10px 22px);
  }
  .band { position: absolute; top: 2px; bottom: 2px; border-radius: 5px; background: color-mix(in srgb, var(--c) 46%, transparent); }
  .now-truck {
    position: absolute; z-index: 2; top: 50%; transform: translate(-50%, -50%);
    width: 30px; height: 30px; border-radius: 50%; display: grid; place-items: center;
    background: var(--pp-primary); color: var(--pp-on-primary);
    box-shadow: 0 0 0 4px var(--pp-card), 0 0 0 9px color-mix(in srgb, var(--pp-primary) 18%, transparent);
  }
  .hours { position: relative; height: 18px; margin-top: 10px; font-size: 12px; color: var(--pp-text2); font-variant-numeric: tabular-nums; }
  .hours span { position: absolute; top: 0; transform: translateX(-50%); white-space: nowrap; }
  .hours .now-lab { color: var(--pp-primary); font-weight: 600; }
  @media (max-width: 420px) { .hours .tick:nth-child(even) { display: none; } }
  .anytime { display: flex; flex-wrap: wrap; align-items: center; gap: 8px; margin-top: 16px; }
  .any-label { margin-right: 2px; font-size: 13px; color: var(--pp-text2); }
  .any-chip {
    display: inline-flex; align-items: center; gap: 8px; max-width: 100%; min-width: 0; height: 36px; padding: 0 14px 0 4px; border-radius: 999px;
    border: 1px solid var(--pp-card-line); background: var(--pp-card); box-shadow: var(--pp-shadow-1); font-size: 13px; font-weight: 500;
  }
  .any-chip:hover { box-shadow: var(--pp-shadow-2); }
  .any-name { min-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  .any-av { width: 28px; height: 28px; flex: none; border-radius: 50%; display: grid; place-items: center; background: color-mix(in srgb, var(--c) 15%, var(--pp-card)); color: var(--c); }
  .hero-stats { display: flex; flex-wrap: wrap; gap: 8px; margin-top: 20px; }
  .stat {
    display: inline-flex; align-items: center; gap: 8px; height: 36px; padding: 0 14px 0 5px; border: 0; border-radius: 999px;
    background: color-mix(in srgb, var(--c) 11%, var(--pp-card)); color: var(--pp-text); font-size: 13px; font-weight: 500;
  }
  .stat:hover { background: color-mix(in srgb, var(--c) 18%, var(--pp-card)); }
  .stat .sn {
    min-width: 26px; height: 26px; padding: 0 7px; border-radius: 999px; display: grid; place-items: center;
    background: var(--c); color: var(--pp-card); font: 600 13px / 1 var(--font-display);
  }

  /* Needs a look */
  .attention {
    scroll-margin-top: 76px; padding: 18px 18px 8px; border-radius: var(--r-md);
    background: color-mix(in srgb, var(--st-attention) 6%, var(--pp-card));
    border: 1px solid color-mix(in srgb, var(--st-attention) 22%, var(--pp-card-line));
  }
  .att-head { display: flex; align-items: center; gap: 12px; margin-bottom: 8px; }
  .att-ic { width: 40px; height: 40px; flex: none; border-radius: 50%; display: grid; place-items: center; background: color-mix(in srgb, var(--st-attention) 14%, transparent); color: var(--st-attention); }
  .att-head h3 { font: 600 19px / 1.2 var(--font-display); letter-spacing: -0.01em; }
  .att-head p { margin-top: 2px; font-size: 13px; color: var(--pp-text2); }
  .att-row {
    display: grid; grid-template-columns: 44px minmax(0, 1fr) 20px; align-items: center; gap: 12px; width: 100%;
    padding: 12px 4px; border: 0; background: none; text-align: left;
    border-top: 1px solid color-mix(in srgb, var(--st-attention) 14%, var(--pp-line));
  }
  .att-row .chev { color: var(--pp-text2); }
  .att-row:hover .att-name { text-decoration: underline; }
  .att-av { width: 44px; height: 44px; border-radius: 50%; display: grid; place-items: center; background: color-mix(in srgb, var(--c) 14%, var(--pp-card)); color: var(--c); }
  .att-text { display: grid; gap: 2px; min-width: 0; }
  .att-name { font: 500 16px / 1.25 var(--font-display); }
  .att-reason { font-size: 13px; font-weight: 500; color: var(--c); }
  .att-hint { font-size: 13px; line-height: 1.4; color: var(--pp-text2); }

  /* Groups and cards */
  .group { display: grid; gap: 12px; scroll-margin-top: 76px; }
  .group-h { display: flex; align-items: baseline; gap: 10px; padding: 0 4px; }
  .group-h h3 { font: 600 20px / 1.2 var(--font-display); letter-spacing: -0.012em; }
  .gsub { font-size: 13px; color: var(--pp-text2); }
  .gcount { margin-left: auto; padding: 4px 10px; border-radius: 999px; background: var(--pp-surface2); font-size: 12px; font-weight: 500; color: var(--pp-text2); font-variant-numeric: tabular-nums; }
  .cards { display: grid; gap: 10px; }
  .pkg {
    position: relative; display: grid; grid-template-columns: 56px minmax(0, 1fr) auto 36px; align-items: center; gap: 4px 14px;
    padding: 14px 6px 14px 16px; border-radius: var(--r-md);
    background: var(--pp-card); border: 1px solid var(--pp-card-line); box-shadow: var(--pp-shadow-1);
    cursor: pointer; transition: transform 0.15s ease, box-shadow 0.15s ease;
  }
  .pkg:hover { transform: translateY(-1px); box-shadow: var(--pp-shadow-2); }
  .pkg.menu-open { z-index: 4; }
  .ring { position: relative; display: block; width: 56px; height: 56px; flex: none; }
  .ring > svg { position: absolute; inset: 0; width: 100%; height: 100%; transform: rotate(-90deg); }
  .ring .seg { fill: none; stroke: var(--pp-ring-off); stroke-width: 3.5; stroke-linecap: round; }
  .ring .seg.on { stroke: var(--c); }
  .ring.pending .seg { stroke-dasharray: 3 5; }
  .ring .av { position: absolute; inset: 8px; border-radius: 50%; display: grid; place-items: center; background: color-mix(in srgb, var(--c) 14%, var(--pp-card)); color: var(--c); }
  .ring .av .ic { width: 22px; height: 22px; }
  .ring .done-badge {
    position: absolute; right: 1px; bottom: 1px; width: 18px; height: 18px; border-radius: 50%; display: grid; place-items: center;
    background: var(--st-delivered); color: var(--pp-card); box-shadow: 0 0 0 2px var(--pp-card);
  }
  .ring.lg { width: 96px; height: 96px; }
  .ring.lg .av { inset: 12px; }
  .ring.lg .av .ic { width: 36px; height: 36px; }
  .ring.lg .done-badge { width: 26px; height: 26px; right: 4px; bottom: 4px; }
  .ring.lg .done-badge .ic { width: 16px; height: 16px; }
  .pkg-main { min-width: 0; display: grid; gap: 2px; }
  .pkg-name { font: 500 17px / 1.25 var(--font-display); letter-spacing: -0.005em; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  .pkg-status { display: inline-flex; align-items: center; gap: 6px; font-size: 13px; font-weight: 500; color: var(--c); }
  .pkg-meta { font-size: 13px; color: var(--pp-text2); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  .when { display: grid; justify-items: end; gap: 2px; text-align: right; }
  .when-main { font: 600 16px / 1.2 var(--font-display); font-variant-numeric: tabular-nums; white-space: nowrap; }
  .when-sub { font-size: 12px; color: var(--pp-text2); white-space: nowrap; }
  .pkg.delivered .when-main { color: var(--pp-text2); font-weight: 500; }
  .kebab { width: 36px; height: 36px; color: var(--pp-text2); }
  .menu {
    position: absolute; z-index: 6; right: 8px; top: calc(100% - 6px); min-width: 220px; padding: 6px; border-radius: 14px;
    background: var(--pp-card); border: 1px solid var(--pp-card-line); box-shadow: var(--pp-shadow-2);
  }
  .menu button { display: flex; align-items: center; gap: 12px; width: 100%; padding: 10px 12px; border: 0; border-radius: 10px; background: none; font-size: 14px; text-align: left; color: var(--pp-text); }
  .menu button .ic { color: var(--pp-text2); }
  .menu button:hover { background: var(--pp-hover); }
  .menu .danger, .menu .danger .ic { color: var(--st-attention); }
  @media (max-width: 480px) {
    .pkg { grid-template-columns: 48px minmax(0, 1fr) auto 32px; gap: 2px 10px; padding: 12px 2px 12px 12px; }
    .pkg .ring { width: 48px; height: 48px; }
    .pkg .ring .av { inset: 7px; }
    .pkg .ring .av .ic { width: 20px; height: 20px; }
    .pkg-name { font-size: 16px; }
    .when-main { font-size: 15px; }
    .kebab { width: 32px; height: 32px; }
  }
  .no-match { display: grid; justify-items: center; gap: 10px; padding: 40px 16px; text-align: center; color: var(--pp-text2); }

  /* Empty state */
  .empty { display: grid; justify-items: center; gap: 14px; padding: 56px 16px 24px; text-align: center; }
  .empty-art { position: relative; width: 168px; height: 168px; display: grid; place-items: center; }
  .empty-art .halo { position: absolute; inset: 0; border-radius: 50%; background: color-mix(in srgb, var(--pp-primary) 8%, transparent); }
  .empty-art .halo.two { inset: 22px; background: color-mix(in srgb, var(--pp-primary) 12%, var(--pp-card)); }
  .empty-art .box { position: relative; width: 76px; height: 76px; border-radius: 24px; display: grid; place-items: center; background: var(--pp-card); color: var(--pp-primary); box-shadow: var(--pp-shadow-2); }
  .empty-art .box .ic { width: 40px; height: 40px; }
  .empty h2 { font: 600 26px / 1.15 var(--font-display); letter-spacing: -0.015em; }
  .empty p { max-width: 44ch; color: var(--pp-text2); font-size: 15px; }

  /* Buttons */
  .fab {
    position: fixed; z-index: 7; right: 24px; bottom: 24px; display: inline-flex; align-items: center; gap: 10px; height: 56px; padding: 0 24px 0 18px;
    border: 0; border-radius: 18px; background: var(--pp-primary); color: var(--pp-on-primary);
    font: 500 16px / 1 var(--font-display); box-shadow: 0 8px 24px color-mix(in srgb, var(--pp-primary) 35%, transparent), var(--pp-shadow-1);
  }
  .fab:hover { filter: brightness(1.06); }
  .btn { display: inline-flex; align-items: center; justify-content: center; gap: 8px; height: 40px; padding: 0 18px; border: 0; border-radius: 999px; font-size: 14px; font-weight: 500; white-space: nowrap; text-decoration: none; }
  .btn .ic { width: 18px; height: 18px; }
  .btn.sm { height: 32px; padding: 0 12px; font-size: 13px; }
  .btn.lg { height: 48px; padding: 0 24px; font-size: 15px; }
  .btn.text { background: none; color: var(--pp-primary); padding: 0 12px; }
  .btn.text:hover { background: color-mix(in srgb, var(--pp-primary) 10%, transparent); }
  .btn.filled { background: var(--pp-primary); color: var(--pp-on-primary); }
  .btn.filled:disabled { background: var(--pp-disabled-bg); color: var(--pp-text3); cursor: not-allowed; }
  .btn.tonal { background: var(--pp-surface2); color: var(--pp-text); }
  .btn.tonal:hover { background: color-mix(in srgb, var(--pp-text) 10%, var(--pp-surface2)); }
  .btn.danger { background: var(--pp-danger); color: var(--pp-on-danger); }
  .btn.danger:disabled, .btn.text:disabled { opacity: 0.6; cursor: progress; }
  .btn.danger-text { background: none; color: var(--st-attention); }
  .btn.danger-text:hover { background: color-mix(in srgb, var(--st-attention) 10%, transparent); }

  /* Details sheet */
  .scrim { position: fixed; inset: 0; z-index: 20; background: var(--pp-scrim); animation: fade 0.18s ease-out; }
  .scrim.top { z-index: 30; }
  @keyframes fade { from { opacity: 0; } }
  @keyframes slide-in { from { transform: translateX(36px); opacity: 0; } }
  @keyframes slide-up { from { transform: translateY(44px); opacity: 0; } }
  @keyframes pop { from { opacity: 0; transform: translate(-50%, -48%) scale(0.98); } }
  .sheet {
    position: fixed; z-index: 21; top: 0; right: 0; bottom: 0; width: min(480px, 100%); display: flex; flex-direction: column;
    background: var(--pp-card); box-shadow: -16px 0 48px rgba(0, 0, 0, 0.18); animation: slide-in 0.26s cubic-bezier(0.2, 0.8, 0.2, 1);
  }
  .sheet-bar { display: flex; align-items: center; justify-content: flex-end; padding: 10px 10px 0; }
  .grab { display: none; }
  .sheet-body { flex: 1; overflow: auto; display: grid; align-content: start; gap: 22px; padding: 0 24px 28px; }
  .sheet-hero { display: grid; justify-items: center; gap: 12px; padding-top: 2px; text-align: center; }
  .sheet-hero h2 { font: 600 26px / 1.15 var(--font-display); letter-spacing: -0.015em; overflow-wrap: anywhere; }
  .pill { display: inline-flex; align-items: center; gap: 6px; height: 30px; padding: 0 13px 0 10px; border-radius: 999px; background: color-mix(in srgb, var(--c) 13%, transparent); color: var(--c); font-size: 13px; font-weight: 500; }
  .eta-card { display: grid; gap: 4px; padding: 16px 18px; border-radius: 16px; background: var(--pp-surface2); border: 1px solid var(--pp-card-line); }
  .eta-card .em { font: 600 21px / 1.2 var(--font-display); letter-spacing: -0.01em; }
  .eta-card .es { font-size: 14px; color: var(--pp-text2); }
  .eta-card .ec { margin-top: 2px; font-size: 13px; font-weight: 500; color: var(--c); }
  .journey { list-style: none; margin: 0; padding: 0; display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); }
  .journey .j { position: relative; display: grid; justify-items: center; gap: 8px; padding: 0 2px; text-align: center; font-size: 12px; line-height: 1.25; color: var(--pp-text2); }
  .journey .j:not(:last-child)::after { content: ''; position: absolute; top: 18px; left: calc(50% + 24px); right: calc(-50% + 24px); height: 3px; border-radius: 3px; background: var(--pp-ring-off); }
  .journey .j.done:not(:last-child)::after { background: var(--c); }
  .journey .ji { width: 38px; height: 38px; border-radius: 50%; display: grid; place-items: center; background: var(--pp-surface2); color: var(--pp-text3); border: 2px solid var(--pp-ring-off); }
  .journey .j.done .ji { background: var(--c); border-color: var(--c); color: var(--pp-card); }
  .journey .j.cur .ji { background: color-mix(in srgb, var(--c) 14%, var(--pp-card)); border-color: var(--c); color: var(--c); box-shadow: 0 0 0 5px color-mix(in srgb, var(--c) 15%, transparent); }
  .journey .j.done, .journey .j.cur { color: var(--pp-text); }
  .journey .j.cur { font-weight: 600; }
  .sec-h { margin-bottom: 12px; font: 600 16px / 1.2 var(--font-display); }
  .timeline { list-style: none; margin: 0; padding: 0; }
  .ev { position: relative; display: grid; grid-template-columns: 14px minmax(0, 1fr); gap: 14px; padding-bottom: 16px; }
  .ev:not(:last-child)::before { content: ''; position: absolute; left: 6px; top: 17px; bottom: 0; width: 2px; background: var(--pp-ring-off); }
  .ev .b { width: 14px; height: 14px; margin-top: 3px; border-radius: 50%; border: 2px solid var(--pp-ring-off); background: var(--pp-card); }
  .ev:first-child .b { border-color: var(--c); background: var(--c); box-shadow: 0 0 0 4px color-mix(in srgb, var(--c) 18%, transparent); }
  .ev .e { line-height: 1.35; }
  .ev:first-child .e { font-weight: 500; }
  .ev .m { margin-top: 2px; font-size: 12px; color: var(--pp-text2); }
  .ev .a { margin-top: 4px; font-size: 13px; line-height: 1.4; color: var(--pp-text2); }
  .facts { border-radius: 14px; background: var(--pp-surface2); border: 1px solid var(--pp-card-line); }
  .fact { display: flex; align-items: center; justify-content: space-between; gap: 12px; min-height: 48px; padding: 6px 8px 6px 14px; }
  .fact + .fact { border-top: 1px solid var(--pp-line); }
  .fk { font-size: 13px; color: var(--pp-text2); white-space: nowrap; }
  .fv { display: inline-flex; align-items: center; gap: 2px; min-width: 0; font-weight: 500; text-align: right; overflow-wrap: anywhere; }
  .fv.mono { font: 400 13px / 1.3 var(--font-mono); letter-spacing: 0.02em; }
  .icon-row { display: flex; flex-wrap: wrap; gap: 8px; }
  .ic-choice { width: 44px; height: 44px; border-radius: 12px; display: grid; place-items: center; border: 1px solid var(--pp-card-line); background: var(--pp-card); color: var(--pp-text2); }
  .ic-choice:hover { color: var(--pp-text); border-color: var(--pp-input-line); }
  .ic-choice[aria-pressed='true'] { border-color: var(--pp-primary); background: var(--pp-selected); color: var(--pp-primary); }
  .sheet-foot { display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 10px; padding: 12px 16px; border-top: 1px solid var(--pp-line); }
  @media (max-width: 600px) {
    .sheet { top: auto; left: 0; width: 100%; max-height: 92%; border-radius: 22px 22px 0 0; box-shadow: 0 -16px 48px rgba(0, 0, 0, 0.22); animation-name: slide-up; }
    .sheet-bar { justify-content: space-between; padding: 8px 8px 0 16px; }
    .grab { display: block; width: 40px; height: 4px; margin-left: calc(50% - 36px); border-radius: 2px; background: var(--pp-ring-off); }
    .sheet-body { padding: 0 18px 24px; }
  }

  /* Dialogs */
  .dialog {
    position: fixed; z-index: 31; left: 50%; top: 50%; transform: translate(-50%, -50%);
    width: min(540px, calc(100% - 32px)); max-height: calc(100% - 48px); overflow: auto; display: flex; flex-direction: column;
    background: var(--pp-card); border-radius: 24px; box-shadow: 0 28px 72px rgba(0, 0, 0, 0.24); animation: pop 0.2s ease-out;
  }
  .dialog > header { display: flex; align-items: flex-start; justify-content: space-between; gap: 8px; padding: 22px 14px 4px 26px; }
  .dialog h2 { font: 600 24px / 1.2 var(--font-display); letter-spacing: -0.015em; }
  .dsub { margin-top: 4px; font-size: 14px; color: var(--pp-text2); }
  .form { display: grid; gap: 20px; padding: 16px 26px 8px; }
  .field { position: relative; display: grid; gap: 8px; }
  .field > label { font-size: 13px; font-weight: 500; color: var(--pp-text2); }
  .input { width: 100%; height: 50px; padding: 0 14px; border: 1px solid var(--pp-input-line); border-radius: 14px; background: var(--pp-input-bg); color: var(--pp-text); font-size: 15px; }
  select.input { appearance: auto; }
  .input.xl { height: 58px; font-size: 18px; }
  .input::placeholder { color: var(--pp-text3); }
  .input:focus { outline: none; border-color: var(--pp-primary); box-shadow: 0 0 0 4px color-mix(in srgb, var(--pp-primary) 20%, transparent); }
  .input.mono { font-family: var(--font-mono); letter-spacing: 0.04em; }
  .help { font-size: 13px; line-height: 1.4; color: var(--pp-text2); }
  .form-error { display: flex; align-items: flex-start; gap: 8px; padding: 10px 14px; border-radius: 12px; font-size: 14px; background: color-mix(in srgb, var(--st-attention) 9%, var(--pp-card)); color: var(--st-attention); }
  .carrier-row { display: grid; grid-template-columns: 24px minmax(0, 1fr) auto; align-items: center; gap: 10px; padding: 10px 6px 10px 14px; border-radius: 14px; background: color-mix(in srgb, var(--st-delivered) 9%, var(--pp-card)); color: var(--st-delivered); }
  .carrier-row.warn { background: color-mix(in srgb, var(--st-failed) 9%, var(--pp-card)); color: var(--st-failed); }
  .cr-text { display: grid; gap: 2px; font-size: 14px; color: var(--pp-text); }
  .cr-text b { font-weight: 600; }
  .cr-warn { font-size: 13px; color: var(--st-failed); }
  .combo-wrap { position: relative; }
  .combo-wrap .caret { position: absolute; right: 14px; top: 15px; color: var(--pp-text2); pointer-events: none; }
  .combo-list { position: absolute; z-index: 3; left: 0; right: 0; top: calc(100% + 6px); max-height: 260px; overflow: auto; padding: 6px; background: var(--pp-card); border: 1px solid var(--pp-card-line); border-radius: 14px; box-shadow: var(--pp-shadow-2); }
  .opt-head { padding: 8px 10px 4px; font-size: 11px; font-weight: 600; letter-spacing: 0.08em; text-transform: uppercase; color: var(--pp-text2); }
  .opt { display: flex; justify-content: space-between; gap: 12px; padding: 10px; border-radius: 10px; cursor: pointer; }
  .opt:hover, .opt[aria-selected='true'] { background: var(--pp-surface2); }
  .opt .code { font: 12px / 1.6 var(--font-mono); color: var(--pp-text2); }
  .opt-empty { padding: 10px; font-size: 13px; color: var(--pp-text2); }
  .desc-row { display: grid; grid-template-columns: 50px minmax(0, 1fr); gap: 10px; align-items: center; }
  .desc-av { width: 50px; height: 50px; border-radius: 50%; display: grid; place-items: center; background: color-mix(in srgb, var(--pp-primary) 12%, var(--pp-card)); color: var(--pp-primary); }
  .toggle-row { display: flex; align-items: center; justify-content: space-between; gap: 16px; padding: 2px 0; cursor: pointer; }
  .toggle-row > span { display: grid; gap: 2px; }
  .toggle-title { font-size: 14px; font-weight: 500; }
  .switch { appearance: none; -webkit-appearance: none; position: relative; flex: none; width: 46px; height: 28px; margin: 0; border-radius: 999px; background: var(--pp-switch-off); cursor: pointer; transition: background 0.15s; }
  .switch::after { content: ''; position: absolute; top: 3px; left: 3px; width: 22px; height: 22px; border-radius: 50%; background: #ffffff; box-shadow: 0 1px 3px rgba(0, 0, 0, 0.25); transition: transform 0.15s; }
  .switch:checked { background: var(--pp-primary); }
  .switch:checked::after { transform: translateX(18px); }
  .dialog > footer { display: flex; align-items: center; flex-wrap: wrap; gap: 8px; padding: 16px 18px 20px 26px; }
  .quota { margin-right: auto; font-size: 12px; color: var(--pp-text2); }
  .dialog.small { width: min(420px, calc(100% - 32px)); padding: 26px 24px 18px; gap: 10px; align-items: center; text-align: center; }
  .dialog.small p { max-width: 36ch; font-size: 14px; color: var(--pp-text2); }
  .dialog.small .actions { display: flex; justify-content: center; gap: 8px; margin-top: 10px; }
  .cf-ic { width: 52px; height: 52px; margin-bottom: 4px; border-radius: 50%; display: grid; place-items: center; background: color-mix(in srgb, var(--st-attention) 13%, transparent); color: var(--st-attention); }
  .cf-ic.info { background: color-mix(in srgb, var(--pp-primary) 13%, transparent); color: var(--pp-primary); }
  @media (max-width: 600px) {
    .dialog { left: 0; right: 0; top: auto; bottom: 0; transform: none; width: 100%; max-height: 94%; border-radius: 24px 24px 0 0; animation-name: slide-up; }
    .dialog.small { width: 100%; }
    .form { padding: 14px 18px 8px; }
    .dialog > header { padding: 20px 10px 4px 18px; }
    .dialog > footer { padding: 14px 14px 18px 18px; }
  }

  /* Toast */
  .toast {
    position: fixed; z-index: 40; left: 50%; bottom: 100px; transform: translateX(-50%); display: flex; align-items: center; gap: 10px;
    width: max-content; max-width: calc(100% - 32px); padding: 12px 18px 12px 14px; border-radius: 14px;
    background: var(--pp-toast-bg); color: var(--pp-toast-fg); font-size: 14px; box-shadow: var(--pp-shadow-2); animation: toast-in 0.2s ease-out;
  }
  .toast.error .ic { color: var(--st-attention); }
  @keyframes toast-in { from { opacity: 0; transform: translate(-50%, 8px); } }

  @media (prefers-reduced-motion: reduce) {
    *, *::before, *::after { animation: none !important; transition: none !important; }
  }
`;
