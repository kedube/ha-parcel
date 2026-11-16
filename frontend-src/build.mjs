// Builds the Packages panel into custom_components/parcel/frontend/.
// Usage: npm run build   (or: npm run watch)
import { build, context } from 'esbuild';
import { copyFile, mkdir } from 'node:fs/promises';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

const here = dirname(fileURLToPath(import.meta.url));
const outDir = join(here, '..', 'custom_components', 'parcel', 'frontend');

const options = {
  entryPoints: [join(here, 'src', 'parcel-panel.js')],
  outfile: join(outDir, 'parcel-panel.js'),
  bundle: true,
  format: 'esm',
  target: ['es2021'],
  minify: true,
  legalComments: 'eof',
  logLevel: 'info',
};

// Outfit (SIL Open Font License) for names, headings and times.
async function copyFonts() {
  const fontDir = join(outDir, 'fonts');
  await mkdir(fontDir, { recursive: true });
  for (const weight of [400, 500, 600]) {
    const file = `outfit-latin-${weight}-normal.woff2`;
    await copyFile(join(here, 'node_modules', '@fontsource', 'outfit', 'files', file), join(fontDir, file));
  }
  await copyFile(join(here, 'node_modules', '@fontsource', 'outfit', 'LICENSE'), join(fontDir, 'OFL.txt'));
}

await mkdir(outDir, { recursive: true });
await copyFonts();
if (process.argv.includes('--watch')) {
  const ctx = await context(options);
  await ctx.watch();
} else {
  await build(options);
}
