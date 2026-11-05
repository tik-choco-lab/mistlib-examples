import { spawnSync } from 'node:child_process';
import { readFileSync, readdirSync, writeFileSync } from 'node:fs';
import { join } from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';

const root = fileURLToPath(new URL('../', import.meta.url));
const webPackage = 'wrappers/web/package.json';
const unityPackage = 'wrappers/unity/MistLib/package.json';
const webReadme = 'wrappers/web/README.md';
const packageName = '@tik-choco/mistlib-web';
const number = '(0|[1-9][0-9]*)';
const versionPattern = new RegExp(`^${number}\\.${number}\\.${number}(?:-beta\\.${number})?$`);

function parseVersion(version) {
    const match = typeof version === 'string' && version.match(versionPattern);
    if (!match || match[0] !== version) throw new Error(`無効なバージョン: ${version}。X.Y.Z または X.Y.Z-beta.N が必要です。`);
    return match.slice(1).map(value => value === undefined ? undefined : BigInt(value));
}

export function nextVersion(current, channel, bump) {
    let [major, minor, patch, beta] = parseVersion(current);
    if (!['beta', 'stable'].includes(channel)) throw new Error(`無効なチャネル: ${channel}`);
    if (bump !== undefined && !['minor', 'patch', 'major'].includes(bump)) {
        throw new Error(`無効な bump: ${bump}`);
    }
    if (beta !== undefined) {
        if (bump !== undefined) throw new Error('先に stable で beta サイクルを完了してください (finish the beta cycle with stable first)。');
        return `${major}.${minor}.${patch}${channel === 'beta' ? `-beta.${beta + 1n}` : ''}`;
    }
    if (channel === 'stable') throw new Error('すでに stable です。先に beta を開始してください (already stable; start a beta first)。');
    switch (bump ?? 'minor') {
        case 'major': major += 1n; minor = 0n; patch = 0n; break;
        case 'minor': minor += 1n; patch = 0n; break;
        case 'patch': patch += 1n; break;
    }
    return `${major}.${minor}.${patch}-beta.1`;
}

export function distTag(version) {
    return parseVersion(version)[3] === undefined ? 'latest' : 'beta';
}

export function enginePrerelease(version) {
    // Engine pins may use any semver prerelease, unlike wrapper releases.
    const numeric = '(?:0|[1-9][0-9]*)';
    const identifier = '(?:0|[1-9][0-9]*|[0-9A-Za-z-]*[A-Za-z-][0-9A-Za-z-]*)';
    const pattern = new RegExp(`^${numeric}\\.${numeric}\\.${numeric}(?:-(${identifier}(?:\\.${identifier})*))?(?:\\+[0-9A-Za-z-]+(?:\\.[0-9A-Za-z-]+)*)?$`);
    const match = typeof version === 'string' && version.match(pattern);
    if (!match || match[0] !== version) throw new Error(`エンジンは正確な semver に固定してください: ${version}`);
    return match[1] !== undefined;
}

export function assertStableEngine(engine) {
    if (enginePrerelease(engine)) {
        throw new Error(`エンジン ${engine} は prerelease です。先に stable エンジンを対象にしてください。`);
    }
}

export function rewriteReadme(source, engine, current, target) {
    enginePrerelease(engine);
    parseVersion(current);
    parseVersion(target);
    let found = false;
    const result = source.replace(/^([ \t]*npm i )@tik-choco\/mistlib@(\S+) @tik-choco\/mistlib-web@(\S+)([ \t]*\r?)$/gm,
        (line, prefix, enginePin, webPin, suffix) => {
            if (enginePin !== engine || webPin !== current) return line;
            found = true;
            return `${prefix}@tik-choco/mistlib@${engine} @tik-choco/mistlib-web@${target}${suffix}`;
        });
    if (!found) throw new Error('Web README の正確なバージョン付き npm i 行が見つかりません。');
    return result;
}

export function rewriteChangelog(source, web, unity, subjects = [], today = new Date().toISOString().slice(0, 10)) {
    parseVersion(web);
    if (unity !== undefined) parseVersion(unity);
    if (!/^\d{4}-\d{2}-\d{2}$/.test(today)) throw new Error(`無効な日付: ${today}`);
    const heading = /^## \d{4}-\d{2}-\d{2} — [^\r\n]+/m.exec(source);
    if (!heading) throw new Error('CHANGELOG.md の先頭リリース見出しが見つかりません。');
    const title = `Web wrapper ${web}${unity === undefined ? '' : `, Unity package ${unity}`}`;
    if (!heading[0].includes('Web wrapper')) {
        return source.slice(0, heading.index) + `${heading[0]} (${title})` + source.slice(heading.index + heading[0].length);
    }
    const newline = source.includes('\r\n') ? '\r\n' : '\n';
    const entries = subjects.filter(subject => subject && !subject.startsWith('chore(release):'));
    const bullets = entries.length ? entries.map(subject => `- ${subject}`).join(newline) : `- Release Web wrapper ${web}.`;
    const section = `## ${today} — ${title}${newline}${newline}${bullets}${newline}${newline}`;
    return source.slice(0, heading.index) + section + source.slice(heading.index);
}

export function rewritePackage(source, target) {
    parseVersion(target);
    const current = JSON.parse(source).version;
    // Replace only the top-level version token to preserve formatting and EOF.
    const pattern = /^(    "version"[ \t]*:[ \t]*)"([^"\r\n]*)"/m;
    const match = source.match(pattern);
    if (!match || match[2] !== current) {
        throw new Error('package.json の4スペース字下げの version が見つかりません。');
    }
    return source.replace(pattern, (_, prefix) => `${prefix}"${target}"`);
}

export function createReleasePlan({ webVersion, engineVersion, unityVersion, channel, bump, unity = false }) {
    enginePrerelease(engineVersion);
    const web = nextVersion(webVersion, channel, bump);
    const unityTarget = unity ? nextVersion(unityVersion, channel, bump) : undefined;
    return {
        web, unity: unityTarget, engine: engineVersion, tag: distTag(web),
        files: [webPackage, webReadme, 'CHANGELOG.md', ...(unity ? [unityPackage] : [])],
        commitMessage: `chore(release): web wrapper ${web}${unity ? ` and Unity package ${unityTarget}` : ''} for mistlib ${engineVersion}`,
    };
}

export function parseArgs(args) {
    const [channel, ...rest] = args;
    if (channel === 'status' && rest.length === 0) return { channel };
    if (!['beta', 'stable'].includes(channel)) throw new Error('使い方: just publish status | beta [minor|patch|major] [--unity] [--push] [--dry-run] | stable [--unity] [--push] [--dry-run]');
    const options = { channel, unity: false, push: false, dryRun: false };
    const flags = { '--unity': 'unity', '--push': 'push', '--dry-run': 'dryRun' };
    for (const arg of rest) {
        if (Object.hasOwn(flags, arg) && !options[flags[arg]]) options[flags[arg]] = true;
        else if (channel === 'beta' && ['minor', 'patch', 'major'].includes(arg) && options.bump === undefined) options.bump = arg;
        else throw new Error(`無効または重複した引数: ${arg}`);
    }
    return options;
}

function run(command, args, options = {}) {
    // Windows command shims require a shell. Only fixed or validated tokens may
    // reach it; all other commands (including git commit) bypass the shell.
    const shell = process.platform === 'win32' && ['npm', 'just'].includes(command);
    if (shell && args.some(arg => !/^[A-Za-z0-9_@./:=+-]+$/.test(arg))) {
        throw new Error('Windows コマンドに安全でない引数があります。');
    }
    return spawnSync(command, args, { cwd: root, encoding: 'utf8', shell, ...options });
}

function checked(command, args, options) {
    const result = run(command, args, options);
    if (result.error || result.status !== 0) {
        throw new Error(`${command} ${args.join(' ')} が失敗しました: ${result.error?.message ?? result.stderr?.trim() ?? result.status}`);
    }
    return result.stdout.trim();
}

const read = file => readFileSync(join(root, file), 'utf8');
const readJson = file => JSON.parse(read(file));

function gitState() {
    return {
        branch: checked('git', ['branch', '--show-current']) || '(detached HEAD)',
        clean: checked('git', ['status', '--porcelain']) === '',
    };
}

function assertUpToDate() {
    const ref = run('git', ['rev-parse', '--verify', '--quiet', 'refs/remotes/origin/develop']);
    if (ref.error || ref.status !== 0) throw new Error('origin/develop が不明です。git fetch origin を実行してください（自動 fetch はしません）。');
    const behind = checked('git', ['rev-list', '--count', 'develop..origin/develop']);
    if (behind !== '0') throw new Error(`develop は origin/develop より ${behind} コミット遅れています。先に取り込んでください。`);
}

export function assertUnpublishedResult(result, version) {
    parseVersion(version);
    if (result.error) throw new Error(`npm の確認に失敗しました: ${result.error.message}`);
    if (result.status !== 0) {
        if (/\bE404\b/.test(`${result.stderr}\n${result.stdout}`)) return;
        throw new Error(`npm の確認に失敗しました: ${result.stderr?.trim() || `終了コード ${result.status}`}`);
    }
    if (result.stdout.trim()) throw new Error(`Web wrapper ${version} は npm に公開済みです。`);
}

function releaseSubjects() {
    const lastRelease = checked('git', ['log', '-1', '--format=%H', '--grep=^chore(release):']);
    return checked('git', ['log', '--no-merges', '--format=%s', ...(lastRelease ? [`${lastRelease}..HEAD`] : [])])
        .split('\n').filter(Boolean);
}

function renderEdits(plan, current) {
    const edits = new Map([
        [webPackage, rewritePackage(read(webPackage), plan.web)],
        [webReadme, rewriteReadme(read(webReadme), plan.engine, current, plan.web)],
        ['CHANGELOG.md', rewriteChangelog(read('CHANGELOG.md'), plan.web, plan.unity, releaseSubjects())],
    ]);
    if (plan.unity !== undefined) edits.set(unityPackage, rewritePackage(read(unityPackage), plan.unity));
    return edits;
}

export function formatPlan(plan, currentWeb, currentUnity) {
    return [
        'リリース計画:',
        `  Web: ${currentWeb} → ${plan.web}`,
        ...(plan.unity === undefined ? [] : [`  Unity: ${currentUnity} → ${plan.unity}`]),
        `  エンジン: ${plan.engine}`,
        `  npm dist-tag: ${plan.tag}`,
        '  変更ファイル:', ...plan.files.map(file => `    ${file}`),
        `  コミット: ${plan.commitMessage}`,
    ].join('\n');
}

function status() {
    const show = (label, action) => {
        try { console.log(`${label}: ${action()}`); }
        catch (error) { console.error(`${label}: NG — ${error.message}`); }
    };
    show('ブランチ / 作業ツリー', () => {
        const state = gitState();
        return `${state.branch} / ${state.clean ? 'クリーン (clean)' : '変更あり (dirty)'}（develop ガード: ${state.branch === 'develop' && state.clean ? 'OK' : 'NG'}）`;
    });
    show('origin/develop ガード', () => { assertUpToDate(); return 'OK'; });
    let web, engine;
    show('Web バージョン', () => { web = readJson(webPackage).version; parseVersion(web); return web; });
    show('Unity バージョン', () => { const version = readJson(unityPackage).version; parseVersion(version); return version; });
    show('エンジン pin', () => {
        engine = readJson('scripts/engine-api.json').engineVersion;
        return `${engine}（${enginePrerelease(engine) ? 'prerelease' : 'stable'}）`;
    });
    show('エンジン pin 一致ガード', () => {
        if (readJson(webPackage).peerDependencies?.['@tik-choco/mistlib'] !== engine) throw new Error('engine-api.json と Web peerDependencies が一致しません。');
        return 'OK';
    });
    show('stable エンジン pin ガード', () => { assertStableEngine(engine); return 'OK'; });
    const npm = run('npm', ['view', packageName, 'dist-tags'], { timeout: 30000 });
    if (npm.error || npm.status !== 0) console.warn(`警告: npm dist-tags を取得できません: ${npm.error?.message ?? npm.stderr.trim()}`);
    else console.log(`npm dist-tags: ${npm.stdout.trim() || '(なし)'}`);
    for (const channel of ['beta', 'stable']) {
        try { console.log(`次の ${channel}: ${nextVersion(web, channel)}`); }
        catch (error) { console.log(`次の ${channel}: 拒否 — ${error.message}`); }
    }
    console.log('公開済みバージョンと全テストのガードは beta / stable（--dry-run を含む）で確認します。');
    // Status reports guard failures without treating a normal beta cycle as a CLI error.
}

function runChecks(guard) {
    const commands = [
        ['just check', 'just', ['check'], root],
        ['Web テスト', process.execPath, () => {
            const files = readdirSync(join(root, 'wrappers/web/tests')).filter(file => file.endsWith('.mjs')).sort();
            if (files.length === 0) throw new Error('Web テストが見つかりません。');
            return ['--test', ...files.map(file => `wrappers/web/tests/${file}`)];
        }, root],
        ['Python テスト', 'python3', ['-m', 'unittest', 'discover', '-s', 'tests'], join(root, 'wrappers/python')],
    ];
    for (const [label, command, args, cwd] of commands) guard(label, () => {
        const result = run(command, typeof args === 'function' ? args() : args, { cwd, stdio: 'inherit' });
        if (result.error || result.status !== 0) throw new Error(`${label} が失敗しました: ${result.error?.message ?? result.status}`);
    });
}

function printNextSteps(plan) {
    console.log(`次の手順: GitHub Actions の「Publish web wrapper」を確認してください。\nhttps://github.com/tik-choco-lab/mistlib-examples/actions/workflows/publish-web.yml\nnpmjs.com の Staged Packages、または npm stage approve で 2FA 承認してください。\nnpm view ${packageName} dist-tags で ${plan.tag}: ${plan.web} を確認してください。`);
}

function pushRelease() {
    checked('git', ['push', 'origin', 'develop']);
    const ancestor = run('git', ['merge-base', '--is-ancestor', 'origin/main', 'develop']);
    if (ancestor.error || ancestor.status !== 0) {
        throw new Error('develop は push 済みですが、main を fast-forward できません（または origin/main が不明です）。git fetch origin の後、main の変更を develop にマージしてチェックし、git push origin develop と git push origin develop:main を再実行してください。force push は使用しないでください。');
    }
    checked('git', ['push', 'origin', 'develop:main']);
}

function release(options) {
    const failures = [];
    const guard = (label, action) => {
        try { const result = action(); console.log(`OK: ${label}`); return result; }
        catch (error) { failures.push(`${label}: ${error.message}`); console.error(`エラー: ${label}: ${error.message}`); }
    };
    const web = guard('Web package', () => readJson(webPackage));
    const engine = guard('エンジン pin', () => {
        const version = readJson('scripts/engine-api.json').engineVersion;
        enginePrerelease(version);
        return version;
    });
    const unity = options.unity ? guard('Unity package', () => readJson(unityPackage)) : undefined;
    guard('develop ブランチ', () => {
        const state = gitState();
        if (state.branch !== 'develop') throw new Error(`現在は ${state.branch} です。develop で実行してください。`);
    });
    guard('クリーンな作業ツリーと index', () => {
        if (!gitState().clean) throw new Error('作業ツリーまたは index に変更があります。先に変更をコミットするか退避してください。');
    });
    guard('origin/develop に遅れていない', assertUpToDate);
    guard('エンジン pin 一致', () => {
        if (!engine || web?.peerDependencies?.['@tik-choco/mistlib'] !== engine) throw new Error('engine-api.json と Web peerDependencies が一致しません。');
    });
    if (options.channel === 'stable') guard('stable エンジン pin', () => assertStableEngine(engine));
    const plan = guard('バージョン計算', () => createReleasePlan({
        webVersion: web?.version, engineVersion: engine, unityVersion: unity?.version, ...options,
    }));
    if (plan) guard('対象バージョンが npm に未公開', () => {
        assertUnpublishedResult(run('npm', ['view', `${packageName}@${plan.web}`, 'version'], { timeout: 30000 }), plan.web);
    });
    runChecks(guard);
    if (plan) console.log(formatPlan(plan, web.version, unity?.version));
    // Preflight the same transforms during dry-run, even when a guard failed.
    if (options.dryRun && plan) guard('編集内容の検証', () => renderEdits(plan, web.version));
    if (failures.length) {
        console.error(`ガード失敗 ${failures.length} 件。ファイルの変更・コミット・push は行いません。`);
        return 1;
    }
    if (options.dryRun) {
        console.log('dry-run 完了。ファイルの変更・コミット・push は行いません。');
        return 0;
    }
    try {
        const edits = renderEdits(plan, web.version);
        for (const [file, content] of edits) writeFileSync(join(root, file), content);
    } catch (error) {
        // The clean-tree guard makes restoring this exact file list safe.
        try { checked('git', ['checkout', '--', ...plan.files]); }
        catch (restoreError) { console.error(`エラー: 復元に失敗しました: ${restoreError.message}`); }
        throw error;
    }
    checked('git', ['add', '--', ...plan.files]);
    checked('git', ['commit', '-m', plan.commitMessage]);
    console.log(`コミット完了: ${plan.commitMessage}`);
    if (options.push) {
        try { pushRelease(); }
        finally { printNextSteps(plan); }
    } else {
        console.log('push する場合は次を実行してください（origin/main が develop の祖先であることを確認）:\ngit push origin develop\ngit merge-base --is-ancestor origin/main develop && git push origin develop:main');
        printNextSteps(plan);
    }
    return 0;
}

export function main(args = process.argv.slice(2)) {
    try {
        const options = parseArgs(args);
        if (options.channel === 'status') { status(); return 0; }
        return release(options);
    } catch (error) {
        console.error(`エラー: ${error.message}`);
        return 1;
    }
}

if (process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href) {
    process.exitCode = main();
}
