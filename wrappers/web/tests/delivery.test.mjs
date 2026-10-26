import assert from 'node:assert/strict';
import { after, before, test } from 'node:test';
import { copyFile, mkdir, mkdtemp, readFile, rm, writeFile } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { pathToFileURL } from 'node:url';

// Load the actual wrapper against a mock package in isolation, without WASM or
// changing the installed engine. Capture the arguments crossing the FFI boundary.
let dir, wrapper, calls, node;
before(async () => {
    dir = await mkdtemp(join(tmpdir(), 'mistlib-delivery-'));
    await writeFile(join(dir, 'package.json'), JSON.stringify({ type: 'module' }));
    for (const name of ['index.js', 'options.js']) {
        await copyFile(new URL(`../${name}`, import.meta.url), join(dir, name));
    }
    const engineDir = join(dir, 'node_modules', '@tik-choco', 'mistlib');
    await mkdir(engineDir, { recursive: true });
    await writeFile(join(engineDir, 'package.json'), JSON.stringify({
        type: 'module', exports: './index.js',
    }));
    const { required } = JSON.parse(await readFile(
        new URL('../../../scripts/engine-api.json', import.meta.url), 'utf8'));
    await writeFile(join(engineDir, 'index.js'), `
        export const calls = [];
        export default async function initialize() {}
        ${[...required, 'set_local_track_audience'].filter(name => name !== 'default').map(name =>
            `export function ${name}(...args) {
                calls.push(['${name}', ...args]);
                if ('${name}' === 'get_version') return '0.7.0';
                if ('${name}' === 'get_build_info') return '{"version":"0.7.0","target":"wasm32-unknown-unknown"}';
                if ('${name}' === 'init_with_config' || '${name}' === 'set_log_level') return true;
                if ('${name}' === 'leave_room_async') return Promise.resolve();
            }`
        ).join('\n')}
    `);
    wrapper = await import(pathToFileURL(join(dir, 'index.js')).href);
    ({ calls } = await import(pathToFileURL(join(engineDir, 'index.js')).href));
    node = new wrapper.MistNode('sender', 'ws://localhost');
});
after(() => dir && rm(dir, { recursive: true, force: true }));

test('public codes preserve 0–2 and add ReliableUnordered = 3', () => {
    assert.deepEqual([
        wrapper.DELIVERY_RELIABLE, wrapper.DELIVERY_UNRELIABLE_ORDERED,
        wrapper.DELIVERY_UNRELIABLE, wrapper.DELIVERY_RELIABLE_UNORDERED,
    ], [0, 1, 2, 3]);
});

test('all codes reach default and room-scoped engine sends unchanged', () => {
    const payload = new Uint8Array([0, 255]);
    for (const code of [0, 1, 2, 3]) {
        calls.length = 0;
        node.sendMessage('peer', payload, code);
        node.sendMessage('peer', payload, code, 'room-1');
        assert.deepEqual(calls, [
            ['send_message', 'peer', payload, code],
            ['send_message_in_room', 'room-1', 'peer', payload, code],
        ]);
    }
});

test('default remains Unreliable and string payloads are encoded', () => {
    calls.length = 0;
    node.sendMessage(null, 'hello');
    assert.deepEqual(calls, [
        ['send_message', '', new TextEncoder().encode('hello'), 2],
    ]);
});


test('room leave uses wasm leave_room(id), including an empty id', async () => {
    await node.init();
    calls.length = 0;
    node.leaveRoom('room-1');
    node.leaveRoom('');
    assert.deepEqual(calls, [['leave_room', 'room-1'], ['leave_room', '']]);
    assert.equal(node.initialized, true);
    const other = new wrapper.MistNode('other', 'ws://localhost');
    await assert.rejects(other.init(), /leaveAllRooms/);
});

test('deprecated aliases warn and forward to the new operations', (t) => {
    const warn = t.mock.method(console, 'warn', () => {});
    calls.length = 0;
    node.leaveRoomId('room-1');
    node.leaveRoom();
    assert.deepEqual(calls, [['leave_room', 'room-1'], ['leave_all_rooms']]);
    assert.equal(node.initialized, false);
    assert.equal(warn.mock.callCount(), 2);
    assert.match(warn.mock.calls[0].arguments[0], /deprecated.*leaveRoom/);
    assert.match(warn.mock.calls[1].arguments[0], /deprecated.*leaveAllRooms/);
});

test('leaveAllRooms releases the engine for another node', async () => {
    await node.init();
    calls.length = 0;
    node.leaveAllRooms();
    assert.deepEqual(calls, [['leave_all_rooms']]);
    assert.equal(node.initialized, false);
    const other = new wrapper.MistNode('other', 'ws://localhost');
    await other.init();
    assert.equal(other.initialized, true);
    other.leaveAllRooms();
});

test('metadata reads the loaded engine without claiming a node', async () => {
    calls.length = 0;
    assert.equal(await wrapper.getVersion(), '0.7.0');
    assert.deepEqual(JSON.parse(await wrapper.getBuildInfo()), {
        version: '0.7.0', target: 'wasm32-unknown-unknown',
    });
    assert.deepEqual(calls, [['get_version'], ['get_build_info']]);
    const other = new wrapper.MistNode('metadata', 'ws://localhost');
    await other.init();
    other.leaveAllRooms();
});

test('missing metadata exports explain how to refresh a stale engine', async () => {
    const source = await readFile(join(dir, 'index.js'), 'utf8');
    for (const missing of ['get_version', 'get_build_info']) {
        const engineName = `old-${missing}.mjs`;
        const metadata = ['get_version', 'get_build_info'].filter(name => name !== missing);
        await writeFile(join(dir, engineName), `
            export default async function init() { throw new Error('must reject before initialization'); }
            ${metadata.map(name => `export function ${name}() {}`).join('\n')}
        `);
        const wrapperName = `wrapper-${missing}.mjs`;
        await writeFile(join(dir, wrapperName), source.replace("'@tik-choco/mistlib'", `'./${engineName}'`));
        const old = await import(pathToFileURL(join(dir, wrapperName)).href);
        for (const read of [old.getVersion, old.getBuildInfo]) {
            await assert.rejects(read(), error => {
                assert.match(error.message, new RegExp(missing));
                assert.match(error.message, /@tik-choco\/mistlib >= 0\.7\.0/);
                assert.match(error.message, /just fetch 0\.7\.0 \/ just sync/);
                return true;
            });
        }
        await assert.rejects(new old.MistNode('stale', 'ws://localhost').init(), /0\.7\.0/);
    }
});

test('audience preserves all peers, nobody and explicit peer ids', () => {
    calls.length = 0;
    node.setLocalTrackAudience('track', null);
    node.setLocalTrackAudience('track');
    node.setLocalTrackAudience('track', []);
    node.setLocalTrackAudience('track', ['相手']);
    assert.deepEqual(calls, [
        ['set_local_track_audience', 'track', null],
        ['set_local_track_audience', 'track', undefined],
        ['set_local_track_audience', 'track', []],
        ['set_local_track_audience', 'track', ['相手']],
    ]);
});

test('async leave waits for the engine cleanup promise', async () => {
    calls.length = 0;
    await node.leaveRoomAsync('room-1');
    assert.deepEqual(calls, [['leave_room_async', 'room-1']]);
});

test('log level and config initialization use 0.7 exports', async () => {
    calls.length = 0;
    assert.equal(await wrapper.setLogLevel('debug'), true);
    const configured = new wrapper.MistNode('configured', { signaling: { mode: 'websocket' } });
    await configured.init();
    assert.deepEqual(calls[0], ['set_log_level', 'debug']);
    assert.equal(calls[1][0], 'init_with_config');
    assert.equal(calls[1][1], 'configured');
    configured.leaveAllRooms();
});

test('storage pin and KV APIs forward bytes and keys to the engine', async () => {
    calls.length = 0;
    const bytes = new Uint8Array([0, 255]);
    await wrapper.storage_add('name', bytes);
    await wrapper.storage_get('cid');
    await wrapper.storage_add_at('name', bytes, 1, 2, 3);
    await wrapper.storage_pin('cid');
    await wrapper.storage_unpin('cid');
    await wrapper.storage_is_pinned('cid');
    await wrapper.storage_add_pinned('name', bytes);
    await wrapper.storage_kv_set('key', bytes);
    await wrapper.storage_kv_get('key');
    await wrapper.storage_kv_delete('key');
    assert.deepEqual(calls, [
        ['storage_add', 'name', bytes], ['storage_get', 'cid'],
        ['storage_add_at', 'name', bytes, 1, 2, 3], ['storage_pin', 'cid'],
        ['storage_unpin', 'cid'], ['storage_is_pinned', 'cid'],
        ['storage_add_pinned', 'name', bytes], ['storage_kv_set', 'key', bytes],
        ['storage_kv_get', 'key'], ['storage_kv_delete', 'key'],
    ]);
});
