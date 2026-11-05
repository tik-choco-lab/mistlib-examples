import assert from 'node:assert/strict';
import { test } from 'node:test';
import { defaultConfig, normalizeOptions } from '../options.js';

test('the default mode requires an invite', () => {
    assert.equal(defaultConfig().signaling.mode, 'nostr_auto');
    assert.throws(() => normalizeOptions(), /inviteSalt and inviteCode.*must be set/s);
});

for (const mode of ['nostr_auto', 'nostrAuto', 'nostr', undefined]) {
    test(`${mode ?? 'implicit default'} requires both invite values and merges Nostr defaults`, () => {
        const signaling = mode === undefined ? {} : { mode };
        for (const nostr of [{}, { inviteSalt: 'app' }, { inviteCode: 'secret' }]) {
            assert.throws(() => normalizeOptions({ signaling: { ...signaling, nostr } }), /must be set/);
        }
        const nostr = { inviteSalt: 'app', inviteCode: 'secret', ttlSeconds: 42 };
        const input = { signaling: { ...signaling, nostr } };
        const result = normalizeOptions(input);
        assert.deepEqual(result.signaling.nostr, {
            ...defaultConfig().signaling.nostr, ...nostr,
        });
        assert.deepEqual(input.signaling.nostr, nostr);
        assert.equal(result.signaling.mode, mode);
    });
}

test('websocket does not require an invite', () => {
    assert.equal(normalizeOptions({ signaling: { mode: 'websocket' } }).signaling.mode, 'websocket');
});
