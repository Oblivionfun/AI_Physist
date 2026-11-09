// Copy the exported run bundles (demo/recorded/*/viz) into dist/recorded so that the static
// build can be opened or hosted without the observatory server.
import { cpSync, existsSync, mkdirSync, readFileSync } from "node:fs";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const here = dirname(fileURLToPath(import.meta.url));
const recorded = resolve(here, "../../demo/recorded");
const dest = resolve(here, "../dist/recorded");
const index = join(recorded, "viz-index.json");
if (!existsSync(index)) {
  console.error(`no ${index}: run \`uv run python -m observatory export <run_id>\` first`);
  process.exit(1);
}
mkdirSync(dest, { recursive: true });
cpSync(index, join(dest, "viz-index.json"));
for (const run of JSON.parse(readFileSync(index, "utf8")).runs) {
  cpSync(join(recorded, run.path), join(dest, run.path), { recursive: true });
  console.log(`bundled ${run.run_id}`);
}
