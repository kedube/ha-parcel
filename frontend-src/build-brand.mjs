// Renders the brand images from the SVG sources in ../brand.
// Usage: npm run brand
//
// Home Assistant and HACS read the PNGs in custom_components/parcel/brand/; the
// README and the repository's social preview use the two in ../brand.
import { mkdir, readFile, writeFile } from 'node:fs/promises';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';
// The WebAssembly build of resvg draws the same pixels on every platform, so CI
// can compare the committed images with what the sources produce.
import { initWasm, Resvg } from '@resvg/resvg-wasm';

const here = dirname(fileURLToPath(import.meta.url));
const sources = join(here, '..', 'brand');
const integration = join(here, '..', 'custom_components', 'parcel', 'brand');

// [source, output, height in pixels]. Home Assistant's sizes: icons are 256 px
// square (512 at @2x); logos are 256 px tall (512 at @2x).
const IMAGES = [
  ['icon.svg', join(integration, 'icon.png'), 256],
  ['icon.svg', join(integration, 'icon@2x.png'), 512],
  ['logo.svg', join(integration, 'logo.png'), 256],
  ['logo.svg', join(integration, 'logo@2x.png'), 512],
  ['logo-dark.svg', join(integration, 'dark_logo.png'), 256],
  ['logo-dark.svg', join(integration, 'dark_logo@2x.png'), 512],
  ['banner.svg', join(sources, 'banner.png'), 600],
  ['social-preview.svg', join(sources, 'social-preview.png'), 640],
];

await initWasm(await readFile(join(here, 'node_modules', '@resvg', 'resvg-wasm', 'index_bg.wasm')));
await mkdir(integration, { recursive: true });

for (const [source, output, height] of IMAGES) {
  const svg = await readFile(join(sources, source), 'utf8');
  if (/<text[\s>]/.test(svg)) {
    // No fonts are loaded, so live text would silently disappear.
    throw new Error(`${source} contains <text>. Convert it to outlines first.`);
  }
  const renderer = new Resvg(svg, { fitTo: { mode: 'height', value: height } });
  const image = renderer.render();
  const png = image.asPng();
  await writeFile(output, png);
  console.log(`${source} -> ${output.slice(join(here, '..').length + 1)}  ${image.width}x${image.height}  ${(png.length / 1024).toFixed(1)}kb`);
  image.free();
  renderer.free();
}
