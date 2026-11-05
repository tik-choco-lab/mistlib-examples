import assert from 'node:assert/strict';
import { test } from 'node:test';
import {
    assertStableEngine, assertUnpublishedResult, createReleasePlan, distTag,
    enginePrerelease, formatPlan, nextVersion, parseArgs, rewriteChangelog,
    rewritePackage, rewriteReadme,
} from './publish-web.mjs';

test('stable → beta defaults to minor; explicit bumps reset lower components', () => {
    for (const [current, bump, expected] of [
        ['0.3.0', undefined, '0.4.0-beta.1'],
        ['0.3.0', 'minor', '0.4.0-beta.1'],
        ['0.3.0', 'patch', '0.3.1-beta.1'],
        ['0.3.0', 'major', '1.0.0-beta.1'],
        ['1.2.9', 'minor', '1.3.0-beta.1'],
        ['1.2.9', 'patch', '1.2.10-beta.1'],
        ['1.2.9', 'major', '2.0.0-beta.1'],
        ['0.0.0', 'patch', '0.0.1-beta.1'],
        ['9007199254740993.0.0', 'major', '9007199254740994.0.0-beta.1'],
    ]) assert.equal(nextVersion(current, 'beta', bump), expected);
});

test('beta increments its counter or finishes as stable', () => {
    assert.equal(nextVersion('0.4.0-beta.1', 'beta'), '0.4.0-beta.2');
    assert.equal(nextVersion('0.4.0-beta.9', 'beta'), '0.4.0-beta.10');
    assert.equal(nextVersion('0.0.0-beta.0', 'beta'), '0.0.0-beta.1');
    assert.equal(nextVersion('0.4.0-beta.1', 'stable'), '0.4.0');
    assert.equal(nextVersion('1.2.3-beta.9007199254740993', 'beta'), '1.2.3-beta.9007199254740994');
});

test('a stable release requires a beta cycle; explicit bumps cannot interrupt it', () => {
    assert.throws(() => nextVersion('0.3.0', 'stable'), /already stable; start a beta first/);
    for (const channel of ['beta', 'stable']) {
        for (const bump of ['major', 'minor', 'patch']) {
            assert.throws(() => nextVersion('0.4.0-beta.1', channel, bump), /finish the beta cycle with stable first/);
        }
    }
});

test('wrapper versions reject malformed semver, other prereleases and leading zeros', () => {
    for (const version of [
        '', 'v1.2.3', '1.2', '1.2.3.4', '01.2.3', '1.02.3', '1.2.03',
        '1.2.3-beta.01', '1.2.3-beta', '1.2.3-beta.-1', '1.2.3-beta.1.2',
        '1.2.3-alpha.1', '1.2.3-rc.1', '1.2.3+build', '1.2.3-beta.1+build',
        '-1.2.3', '1.2.3 ', ' 1.2.3', '1.2.3\n', '1.2.3-beta.1\n',
        '1.2.3;echo', null, undefined, 123, {},
    ]) {
        assert.throws(() => nextVersion(version, 'beta'), /無効なバージョン/);
        assert.throws(() => distTag(version), /無効なバージョン/);
    }
    assert.throws(() => nextVersion('1.2.3', 'alpha'), /無効なチャネル/);
    assert.throws(() => nextVersion('1.2.3', 'beta', 'tiny'), /無効な bump/);
});

test('npm dist-tags separate beta releases from latest', () => {
    assert.equal(distTag('0.3.0'), 'latest');
    assert.equal(distTag('0.4.0-beta.1'), 'beta');
    assert.equal(distTag('0.0.0-beta.0'), 'beta');
});

test('stable engine guard rejects all prereleases and non-exact pins', () => {
    for (const engine of ['0.7.3-beta.3', '1.0.0-rc.1', '1.0.0-0', '1.0.0-alpha+build']) {
        assert.equal(enginePrerelease(engine), true);
        assert.throws(() => assertStableEngine(engine), /先に stable エンジンを対象/);
    }
    for (const engine of ['0.7.3', '1.0.0+build-1']) {
        assert.equal(enginePrerelease(engine), false);
        assert.doesNotThrow(() => assertStableEngine(engine));
    }
    for (const engine of ['^0.7.3', 'latest', '01.2.3', '1.0.0-beta.01', '1.0.0\n', undefined]) {
        assert.throws(() => assertStableEngine(engine), /正確な semver/);
    }
});

test('CHANGELOG appends versions to the existing top heading only', () => {
    const source = '# Changelog\n\n## 2026-11-04 — engine 0.7.3-beta.3\n\n- Existing notes.\n\n## 2026-10-26 — older\n';
    assert.equal(rewriteChangelog(source, '0.4.0-beta.1', undefined, ['ignored']),
        source.replace('engine 0.7.3-beta.3', 'engine 0.7.3-beta.3 (Web wrapper 0.4.0-beta.1)'));
    assert.equal(rewriteChangelog(source, '0.4.0-beta.1', '0.3.0-beta.1'),
        source.replace('engine 0.7.3-beta.3', 'engine 0.7.3-beta.3 (Web wrapper 0.4.0-beta.1, Unity package 0.3.0-beta.1)'));
});

test('CHANGELOG inserts a new dated section and non-release subjects', () => {
    const source = '# Changelog\n\n## 2026-11-04 — Web wrapper 0.4.0-beta.1\n\n- Prior notes.\n';
    const result = rewriteChangelog(source, '0.4.0-beta.2', '0.3.0-beta.2',
        ['feat(web): add feature', 'chore(release): previous', 'fix(web): fix bug'], '2026-11-05');
    assert.equal(result, '# Changelog\n\n## 2026-11-05 — Web wrapper 0.4.0-beta.2, Unity package 0.3.0-beta.2\n\n- feat(web): add feature\n- fix(web): fix bug\n\n' + source.slice('# Changelog\n\n'.length));
});

test('CHANGELOG uses a fallback bullet when there are no non-release commits', () => {
    const source = '# Changelog\n\n## 2026-11-04 — engine (Web wrapper 0.4.0-beta.1)\n\n- Notes.\n';
    for (const subjects of [[], ['chore(release): old', '']]) {
        const result = rewriteChangelog(source, '0.4.0', undefined, subjects, '2026-11-05');
        assert.ok(result.includes('## 2026-11-05 — Web wrapper 0.4.0\n\n- Release Web wrapper 0.4.0.\n\n'));
        assert.ok(result.endsWith(source.slice('# Changelog\n\n'.length)));
    }
    assert.throws(() => rewriteChangelog('# Changelog\n', '0.4.0'), /見出し/);
});

test('CHANGELOG preserves CRLF line endings', () => {
    const source = '# Changelog\r\n\r\n## 2026-11-04 — Web wrapper 0.3.0\r\n\r\n- Notes.\r\n';
    const result = rewriteChangelog(source, '0.4.0-beta.1', undefined, [], '2026-11-05');
    assert.equal(result.replaceAll('\r\n', '').includes('\n'), false);
    assert.ok(result.endsWith(source.slice('# Changelog\r\n\r\n'.length)));
});

test('README rewrites only the exact install line and pins beta versions', () => {
    const source = '# Wrapper\n\n```sh\nnpm i @tik-choco/mistlib@0.7.3-beta.3 @tik-choco/mistlib-web@0.3.0\n```\n\nOther 0.3.0 notes.\n';
    for (const target of ['0.4.0-beta.1', '0.4.0']) {
        assert.equal(rewriteReadme(source, '0.7.3-beta.3', '0.3.0', target),
            source.replace('mistlib-web@0.3.0', `mistlib-web@${target}`));
    }
    const crlf = source.replaceAll('\n', '\r\n');
    assert.equal(rewriteReadme(crlf, '0.7.3-beta.3', '0.3.0', '0.4.0-beta.1'), crlf.replace('mistlib-web@0.3.0', 'mistlib-web@0.4.0-beta.1'));
    for (const bad of [
        '', source.replace('npm i ', 'npm install '),
        source.replace('mistlib-web@0.3.0', 'mistlib-web@^0.3.0'),
        source.replace('mistlib@0.7.3-beta.3', 'mistlib@0.7.1'),
    ]) assert.throws(() => rewriteReadme(bad, '0.7.3-beta.3', '0.3.0', '0.4.0-beta.1'), /npm i 行/);
});

test('package version edits preserve key order, formatting and trailing newline state', () => {
    for (const ending of ['', '\n', '\r\n']) {
        const source = '{\n    "name": "example",\n    "version": "0.3.0",\n    "files": ["index.js"]\n}' + ending;
        assert.equal(rewritePackage(source, '0.4.0-beta.1'), source.replace('"0.3.0"', '"0.4.0-beta.1"'));
    }
});

test('plans compute Unity independently and use exact release commit messages', () => {
    const input = { webVersion: '0.3.0', unityVersion: '0.2.0', engineVersion: '0.7.3-beta.3', channel: 'beta' };
    const web = createReleasePlan(input);
    assert.equal(web.web, '0.4.0-beta.1');
    assert.equal(web.unity, undefined);
    assert.equal(web.tag, 'beta');
    assert.equal(web.commitMessage, 'chore(release): web wrapper 0.4.0-beta.1 for mistlib 0.7.3-beta.3');
    assert.deepEqual(web.files, ['wrappers/web/package.json', 'wrappers/web/README.md', 'CHANGELOG.md']);
    const both = createReleasePlan({ ...input, unity: true, bump: 'patch' });
    assert.equal(both.web, '0.3.1-beta.1');
    assert.equal(both.unity, '0.2.1-beta.1');
    assert.equal(both.commitMessage, 'chore(release): web wrapper 0.3.1-beta.1 and Unity package 0.2.1-beta.1 for mistlib 0.7.3-beta.3');
    assert.ok(both.files.includes('wrappers/unity/MistLib/package.json'));
    const stable = createReleasePlan({ ...input, webVersion: '0.4.0-beta.2', unityVersion: '0.3.0-beta.1', engineVersion: '0.7.3', channel: 'stable', unity: true });
    assert.equal(stable.web, '0.4.0');
    assert.equal(stable.unity, '0.3.0');
    assert.equal(stable.tag, 'latest');
    assert.throws(() => createReleasePlan({ ...input, unity: true, unityVersion: '0.2.1-beta.1', bump: 'patch' }), /finish the beta cycle/);
    const output = formatPlan(web, input.webVersion, input.unityVersion);
    for (const part of ['0.3.0 → 0.4.0-beta.1', 'npm dist-tag: beta', ...web.files, web.commitMessage]) assert.ok(output.includes(part));
});

test('argument parsing rejects unknown flags, duplicates, stable bumps and status flags', () => {
    assert.deepEqual(parseArgs(['status']), { channel: 'status' });
    assert.deepEqual(parseArgs(['beta', 'patch', '--unity', '--push', '--dry-run']), {
        channel: 'beta', bump: 'patch', unity: true, push: true, dryRun: true,
    });
    assert.deepEqual(parseArgs(['stable']), { channel: 'stable', unity: false, push: false, dryRun: false });
    for (const args of [[], ['latest'], ['stable', 'minor'], ['status', '--push'], ['beta', '--wat'], ['beta', '--push', '--push'], ['beta', 'minor', 'patch']]) {
        assert.throws(() => parseArgs(args));
    }
});

test('npm availability never guesses on failures other than E404', () => {
    for (const result of [
        { status: 0, stdout: '', stderr: '' },
        { status: 1, stdout: '', stderr: 'npm error code E404' },
    ]) assert.doesNotThrow(() => assertUnpublishedResult(result, '0.4.0-beta.1'));
    assert.throws(() => assertUnpublishedResult({ status: 0, stdout: '0.4.0-beta.1\n', stderr: '' }, '0.4.0-beta.1'), /公開済み/);
    for (const result of [
        { status: 1, stdout: '', stderr: 'npm error code ECONNRESET' },
        { status: 1, stdout: '', stderr: '' },
        { status: 1, stdout: '', stderr: 'npm error code E401' },
        { status: null, error: new Error('timeout'), stderr: 'E404' },
    ]) assert.throws(() => assertUnpublishedResult(result, '0.4.0-beta.1'), /確認に失敗/);
});
