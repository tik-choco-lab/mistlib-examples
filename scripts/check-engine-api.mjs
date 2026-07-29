// Verifies that a published @tik-choco/mistlib build still provides everything
// wrappers/web/index.js pulls out of it.
//
// That file destructures the engine's namespace object, so a removed export
// silently becomes `undefined` and only fails when something calls it -- long
// after the page loaded, and only on the code path that uses it. This turns
// that into an up-front failure, which is what lets the engine version be
// bumped automatically: the bump only lands if the wrapper still fits.
//
//   node scripts/check-engine-api.mjs <version>
//
// Installs the exact version into a scratch directory and imports it, rather
// than grepping the source, so the check fails the same way a browser would.

import { execFileSync } from "node:child_process";
import { mkdtempSync, readFileSync, rmSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { pathToFileURL } from "node:url";

const version = process.argv[2];
if (!version) {
    console.error("usage: node scripts/check-engine-api.mjs <version>");
    process.exit(2);
}

const here = new URL(".", import.meta.url).pathname;
const { required } = JSON.parse(readFileSync(join(here, "engine-api.json"), "utf8"));

const dir = mkdtempSync(join(tmpdir(), "mistlib-api-"));
try {
    execFileSync("npm", ["init", "-y"], { cwd: dir, stdio: "ignore" });
    execFileSync("npm", ["install", `@tik-choco/mistlib@${version}`], {
        cwd: dir,
        stdio: "inherit",
    });

    const entry = join(dir, "node_modules/@tik-choco/mistlib/mistlib_wasm.js");
    const mod = await import(pathToFileURL(entry).href);

    const missing = required.filter((name) => mod[name] === undefined);
    if (missing.length > 0) {
        console.error(
            `@tik-choco/mistlib@${version} is missing ${missing.length} export(s) that ` +
            `wrappers/web/index.js uses:\n  ${missing.join("\n  ")}\n\n` +
            "The wrapper needs updating before the examples can move to this version.",
        );
        process.exit(1);
    }

    console.log(`@tik-choco/mistlib@${version}: all ${required.length} required exports present`);
} finally {
    rmSync(dir, { recursive: true, force: true });
}
