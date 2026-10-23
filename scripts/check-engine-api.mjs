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

import { execSync } from "node:child_process";
import { mkdtempSync, readFileSync, rmSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";

const version = process.argv[2];
if (!version) {
    console.error("usage: node scripts/check-engine-api.mjs <version>");
    process.exit(2);
}
// npm is run through the shell (on Windows it's npm.cmd, which can't be spawned
// directly), so only accept a plain version/tag before it's put on a command line.
if (!/^[\w.+-]+$/.test(version)) {
    console.error(`invalid version: ${version}`);
    process.exit(2);
}

const here = fileURLToPath(new URL(".", import.meta.url));
const { required } = JSON.parse(readFileSync(join(here, "engine-api.json"), "utf8"));

const dir = mkdtempSync(join(tmpdir(), "mistlib-api-"));
try {
    execSync("npm init -y", { cwd: dir, stdio: "ignore" });
    execSync(`npm install @tik-choco/mistlib@${version}`, {
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
