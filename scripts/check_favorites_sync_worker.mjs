#!/usr/bin/env node
import assert from "node:assert/strict";
import worker from "../workers/favorites-sync/src/index.js";

const payload = {
    schema: "publication-favorites-sync",
    version: 2,
    revision: "test",
    updatedAt: "2026-05-06T00:00:00.000Z",
    library: {
        version: 2,
        folders: [],
        items: {},
    },
};

function createEnv() {
    return {
        SYNC_KEY: "test-secret",
        ALLOWED_ORIGIN: "https://huwenbo-lab.github.io",
        FAVORITES_KV: {
            value: null,
            async get(key, options = {}) {
                assert.equal(key, "favorites:default");
                if (!this.value) return null;
                return options.type === "json" ? JSON.parse(this.value) : this.value;
            },
            async put(key, value) {
                assert.equal(key, "favorites:default");
                this.value = value;
            },
        },
    };
}

function request(method, headers = {}, body = undefined) {
    return new Request("https://sync.example.test/", {
        method,
        headers: {
            Origin: "https://huwenbo-lab.github.io",
            ...headers,
        },
        body,
    });
}

async function main() {
    const env = createEnv();

    const preflight = await worker.fetch(request("OPTIONS"), env, {});
    assert.equal(preflight.status, 204);
    assert.equal(preflight.headers.get("Access-Control-Allow-Origin"), "https://huwenbo-lab.github.io");

    const unauthorized = await worker.fetch(request("GET"), env, {});
    assert.equal(unauthorized.status, 401);

    const missing = await worker.fetch(request("GET", {
        Authorization: "Bearer test-secret",
    }), env, {});
    assert.equal(missing.status, 404);

    const saved = await worker.fetch(request("PUT", {
        Authorization: "Bearer test-secret",
        "Content-Type": "application/json",
    }, JSON.stringify(payload)), env, {});
    assert.equal(saved.status, 200);
    assert.equal((await saved.json()).ok, true);

    const loaded = await worker.fetch(request("GET", {
        Authorization: "Bearer test-secret",
    }), env, {});
    assert.equal(loaded.status, 200);
    assert.equal((await loaded.json()).schema, "publication-favorites-sync");

    const blocked = await worker.fetch(new Request("https://sync.example.test/", {
        method: "GET",
        headers: {
            Origin: "https://example.com",
            Authorization: "Bearer test-secret",
        },
    }), env, {});
    assert.equal(blocked.status, 403);
}

await main();
