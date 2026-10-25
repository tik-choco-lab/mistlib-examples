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
        ${required.filter(name => name !== 'default').map(name =>
            `export function ${name}(...args) { calls.push(['${name}', ...args]); }`
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
