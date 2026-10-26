// Verifies that a published @tik-choco/mistlib build still provides everything
// wrappers/web/index.js pulls out of it.
//
// That file destructures the engine's namespace object, so a removed export
// silently becomes `undefined` and only fails when something calls it -- long
// after the page loaded, and only on the code path that uses it. This turns
// that into an up-front failure, which is what lets the engine version be
// checked before updating artifacts or import maps.
//
//   node scripts/check-engine-api.mjs <version>
//   node scripts/check-engine-api.mjs --source   (offline, no artifacts needed)
//
// Installs the exact version into a scratch directory and imports it, rather
// than grepping the source, so the check fails the same way a browser would.

import { execSync } from "node:child_process";
import assert from "node:assert/strict";
import { mkdtempSync, readFileSync, rmSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";

const here = fileURLToPath(new URL(".", import.meta.url));
const { engineVersion, required, events, mediaEvents } = JSON.parse(
    readFileSync(join(here, "engine-api.json"), "utf8"));
const sourceOnly = process.argv[2] === "--source";
const version = sourceOnly ? engineVersion : process.argv[2];
if (!version || process.argv.length !== 3) {
    console.error("usage: node scripts/check-engine-api.mjs <version> | --source");
    process.exit(2);
}
// npm is run through the shell (on Windows it's npm.cmd, which can't be spawned
// directly), so only accept a plain version/tag before it's put on a command line.
if (!/^[\w.+-]+$/.test(version)) {
    console.error(`invalid version: ${version}`);
    process.exit(2);
}

if (version !== engineVersion) {
    console.error(`this wrapper requires engine ${engineVersion}, received ${version}`);
    process.exit(2);
}

// Check the source contract without importing or changing bundled engine files.
const source = (path) => readFileSync(join(here, "..", path), "utf8");
const wrapper = source("wrappers/web/index.js");
const declarations = source("wrappers/web/index.d.ts");
const python = source("wrappers/python/mist/core.py");
const pythonExports = source("wrappers/python/mist/__init__.py");
const unity = source("wrappers/unity/MistLib/Runtime/Protocol/MistLibMessageType.cs");
const constantName = (name, prefix) => prefix + name.replace(/([a-z])([A-Z])/g, "$1_$2").toUpperCase();
for (const [table, prefix] of [[events, "EVENT_"], [mediaEvents, "MEDIA_EVENT_"]]) {
    for (const [name, code] of Object.entries(table)) {
        const constant = constantName(name, prefix);
        assert.match(wrapper, new RegExp(`export const ${constant} = ${code};`), constant);
        assert.match(declarations, new RegExp(`export const ${constant}: ${code};`), constant);
        if (prefix === "EVENT_") {
            assert.match(python, new RegExp(`^${constant} = ${code}$`, "m"), constant);
            assert.match(pythonExports, new RegExp(`\\b${constant}\\b`), constant);
            assert.match(unity, new RegExp(`\\b${name} = ${code}\\b`), name);
        }
    }
}
const imported = ["default", ...wrapper.matchAll(/\b(\w+): mist_\w+/g)].map(
    (match) => typeof match === "string" ? match : match[1]);
assert.deepEqual(imported.sort(), [...required].sort(), "engine export manifest must match wrapper imports");
assert.equal(JSON.parse(source("wrappers/web/package.json")).peerDependencies["@tik-choco/mistlib"], engineVersion);
if (sourceOnly) {
    for (const page of ["index.html", "media.html", "optimization_demo.html"]) {
        const pin = source(`examples/web/${page}`).match(/@tik-choco\/mistlib@(\d+\.\d+\.\d+)\//);
        assert.equal(pin?.[1], engineVersion, page);
    }
    console.log(`engine ${engineVersion}: wrapper events, declarations, exports and pins agree (offline)`);
    process.exit(0);
}

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

    for (const [exportName, table] of [["MistEvent", events], ["MistMediaEvent", mediaEvents]]) {
        for (const [name, code] of Object.entries(table)) {
            assert.equal(mod[exportName]?.[name], code, `${exportName}.${name}`);
        }
    }

    console.log(`@tik-choco/mistlib@${version}: all ${required.length} required exports present`);
} finally {
    rmSync(dir, { recursive: true, force: true });
}
