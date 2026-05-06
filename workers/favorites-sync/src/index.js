const FAVORITES_KEY = "favorites:default";
const SYNC_SCHEMA = "publication-favorites-sync";
const MAX_PAYLOAD_BYTES = 1_000_000;

function jsonResponse(request, env, body, status = 200) {
    return new Response(JSON.stringify(body), {
        status,
        headers: {
            ...corsHeaders(request, env),
            "Content-Type": "application/json;charset=utf-8",
            "Cache-Control": "no-store",
        },
    });
}

function emptyResponse(request, env, status = 204) {
    return new Response(null, {
        status,
        headers: corsHeaders(request, env),
    });
}

function configuredOrigins(env) {
    return String(env.ALLOWED_ORIGIN || "https://huwenbo-lab.github.io")
        .split(",")
        .map((origin) => origin.trim())
        .filter(Boolean);
}

function allowedOriginForRequest(request, env) {
    const origin = request.headers.get("Origin") || "";
    const allowed = configuredOrigins(env);
    if (!origin) {
        return allowed[0] || "";
    }
    return allowed.includes(origin) ? origin : "";
}

function corsHeaders(request, env) {
    const origin = allowedOriginForRequest(request, env);
    const headers = {
        Vary: "Origin",
        "Access-Control-Allow-Methods": "GET, PUT, OPTIONS",
        "Access-Control-Allow-Headers": "Authorization, Content-Type",
        "Access-Control-Max-Age": "86400",
    };
    if (origin) {
        headers["Access-Control-Allow-Origin"] = origin;
    }
    return headers;
}

async function digestString(value) {
    const encoded = new TextEncoder().encode(String(value || ""));
    const digest = await crypto.subtle.digest("SHA-256", encoded);
    return new Uint8Array(digest);
}

async function constantTimeEqual(left, right) {
    const leftDigest = await digestString(left);
    const rightDigest = await digestString(right);
    let diff = 0;
    for (let index = 0; index < leftDigest.length; index += 1) {
        diff |= leftDigest[index] ^ rightDigest[index];
    }
    return diff === 0;
}

async function isAuthorized(request, env) {
    const syncKey = String(env.SYNC_KEY || "");
    const header = request.headers.get("Authorization") || "";
    const prefix = "Bearer ";
    if (!syncKey || !header.startsWith(prefix)) {
        return false;
    }
    return constantTimeEqual(header.slice(prefix.length), syncKey);
}

function isPlainObject(value) {
    return Boolean(value) && typeof value === "object" && !Array.isArray(value);
}

function isValidFavoritesPayload(payload) {
    return (
        isPlainObject(payload) &&
        payload.schema === SYNC_SCHEMA &&
        Number(payload.version) === 2 &&
        isPlainObject(payload.library) &&
        Array.isArray(payload.library.folders) &&
        isPlainObject(payload.library.items)
    );
}

async function handlePut(request, env) {
    const contentLength = Number(request.headers.get("Content-Length") || 0);
    if (contentLength > MAX_PAYLOAD_BYTES) {
        return jsonResponse(request, env, { error: "payload_too_large" }, 413);
    }

    let payload;
    try {
        payload = await request.json();
    } catch {
        return jsonResponse(request, env, { error: "invalid_json" }, 400);
    }

    if (!isValidFavoritesPayload(payload)) {
        return jsonResponse(request, env, { error: "invalid_payload" }, 400);
    }

    const stored = {
        ...payload,
        updatedAt: new Date().toISOString(),
    };
    await env.FAVORITES_KV.put(FAVORITES_KEY, JSON.stringify(stored), {
        metadata: {
            revision: String(stored.revision || ""),
            updatedAt: stored.updatedAt,
        },
    });

    return jsonResponse(request, env, {
        ok: true,
        revision: stored.revision || "",
        updatedAt: stored.updatedAt,
    });
}

async function handleGet(request, env) {
    const payload = await env.FAVORITES_KV.get(FAVORITES_KEY, { type: "json" });
    if (!payload) {
        return jsonResponse(request, env, { error: "not_found" }, 404);
    }
    return jsonResponse(request, env, payload);
}

export default {
    async fetch(request, env, ctx) {
        void ctx;
        try {
            if (!allowedOriginForRequest(request, env)) {
                return jsonResponse(request, env, { error: "origin_not_allowed" }, 403);
            }

            if (request.method === "OPTIONS") {
                return emptyResponse(request, env);
            }

            if (!env.FAVORITES_KV || !env.SYNC_KEY) {
                return jsonResponse(request, env, { error: "sync_not_configured" }, 500);
            }

            if (!(await isAuthorized(request, env))) {
                return jsonResponse(request, env, { error: "unauthorized" }, 401);
            }

            if (request.method === "GET") {
                return handleGet(request, env);
            }

            if (request.method === "PUT") {
                return handlePut(request, env);
            }

            return new Response(JSON.stringify({ error: "method_not_allowed" }), {
                status: 405,
                headers: {
                    ...corsHeaders(request, env),
                    Allow: "GET, PUT, OPTIONS",
                    "Content-Type": "application/json;charset=utf-8",
                    "Cache-Control": "no-store",
                },
            });
        } catch (error) {
            console.error(JSON.stringify({
                message: "favorites_sync_error",
                error: String(error?.message || error),
            }));
            return jsonResponse(request, env, { error: "internal_error" }, 500);
        }
    },
};
