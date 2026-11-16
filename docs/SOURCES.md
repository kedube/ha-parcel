# Sources

This integration was written from scratch. No code from other Home Assistant integrations was copied or consulted while writing it. This page records where each fact about Parcel came from.

## Parcel's documentation

- [API overview](https://parcel.app/help/api.html), [View Deliveries](https://parcelapp.net/help/api-view-deliveries.html) and [Add Delivery](https://parcelapp.net/help/api-add-delivery.html): endpoints, the `api-key` header, `filter_mode`, response fields, status codes 0–8, the `pholder` carrier, and the limits of 20 reads an hour and 20 adds a day.
- [Carrier list](https://api.parcel.app/external/supported_carriers.json): carrier codes, names and `extra_required`.

## Parcel's own web app

Read first-hand from the public JavaScript that web.parcelapp.net serves (`/js/3.3.6/*.js`), on 2026-11-15:

- Deleting is a form post to `delete-ajax.php` with `number` and `type`, authorized by the account's sign-in cookie.
- The read-only list download is `download-ajax.php` with `existing_deliveries`.
- What `extra_required` values 1–5 mean, from the web app's add form: postcode, email, PIN, phone, and country code with postcode.
- The API panel's labels: **API**, **Create a Key**, **Copy the Key**, **Revoke the Key**.

## Observed behavior

- Error responses, probed with made-up credentials: HTTP 401 `Account not found` for a bad API key, and `failed_verification` or `missing_data` from the web app for a bad or missing sign-in.
- Real responses from the maintainer's own account: Amazon's date-only ETAs (`… 00:00:00`) and `--//--` event dates. Parcel generates its own tracking number for placeholder packages, and the web app's delete reports success even when nothing matched.
- The web sign-in cookie (`account_token`) is issued with a 360-day lifetime and isn't re-issued when it's used, so the integration counts down from when the token was entered.
- Rate limiting, seen once on 2026-11-15: the deliveries endpoint answered HTTP 429 after about 10 API reads in the preceding hour (the documented limit is 20), during a development session that also made about a dozen web-app calls. Requests kept being rejected for 3 to 5 minutes, including five quick retries. The cause isn't known; Parcel's limiter may count more than the documented endpoint, or react to bursts. The integration therefore treats any 429 as "stop asking for a while" instead of relying on its own count.

## Home Assistant

- Home Assistant's developer documentation, and the signatures of the platform functions an integration must call (config flows, coordinators, entities, panels, websocket commands, device triggers, repairs), read from an installed copy of Home Assistant.
- Home Assistant starts its web server before custom integrations finish loading, and the frontend's websocket library repeats a subscription after a reconnect without reporting it when that fails (both read from an installed copy of Home Assistant and its frontend). The panel therefore subscribes again itself whenever the connection comes back.
- The entity registry keeps a removed entity's unique ID and entity ID for as long as its config entry exists, and clears them 30 days after the entry is removed. `async_migrate_entries` changes unique IDs without touching entity IDs, and an entity's `suggested_object_id` is what a new entity ID is made from (all read from an installed copy of Home Assistant). Package sensors' unique IDs are therefore keyed hashes, the move to them is a config entry minor version, and a package without a name gets an entity ID from its carrier.
- The manifest's `categories` key and its allowed values: Home Assistant's [integration categories](https://contributors.home-assistant.io/core/integrations/categories/) page.
- Schemas are written with [Probatio](https://probatio.frenck.dev), which Home Assistant has used in place of voluptuous since 2026.9 ([announcement](https://contributors.home-assistant.io/blog/2026/09/30/probatio-validation-engine)).

## Logo and icon

The box logo was drawn from scratch for this integration; the drawings are the SVG files in `brand/`.

- The Parcel app's own icon (from the installed Mac app, version 8.7.1) was looked at on 2026-11-15 for its subject and colors: a terracotta cardboard box with cream tape on a cream background. Nothing was traced or copied from it, and no Parcel artwork is in this repository. The proportions, lighting and details are this project's own: the tape folds over the left face, and a small house stands where Parcel's icon has an arrow and a label.
- The lettering is Outfit SemiBold and Medium, converted to outlines.
- Image names and sizes follow Home Assistant's [brand image guide](https://contributors.home-assistant.io/core/integrations/brands/) and the [2026.3 announcement](https://contributors.home-assistant.io/blog/2026/02/24/brands-proxy-api/) that custom integrations can ship a `brand/` folder. HACS's [brand check](https://www.hacs.xyz/docs/publish/include/) reads the same folder.
- No other integration's brand images were looked at.

## Disclosure

Before the from-scratch requirement was set, the README, one documentation page and a few short excerpts of another Parcel integration ([jmdevita/parcel-ha](https://github.com/jmdevita/parcel-ha)) were briefly viewed while checking whether deleting was possible. Nothing from it was used. The delete mechanism was then confirmed independently from Parcel's own web app, as described above.

## Third-party components

- [Lit](https://lit.dev) (BSD-3-Clause), bundled into the panel.
- [Material Design Icons](https://pictogrammers.com/library/mdi/) via `@mdi/js` (Apache 2.0).
- [Outfit](https://fonts.google.com/specimen/Outfit) via `@fontsource/outfit` (SIL Open Font License 1.1).
- [esbuild](https://esbuild.github.io) (MIT), build-time only.
- [resvg](https://github.com/yisibl/resvg-js) via `@resvg/resvg-wasm` (MPL-2.0), build-time only: it draws the brand PNGs from the SVG files.
- [ESLint](https://eslint.org) (MIT), [mypy](https://mypy-lang.org) (MIT) and [Ruff](https://docs.astral.sh/ruff/) (MIT), for checking the code only.
