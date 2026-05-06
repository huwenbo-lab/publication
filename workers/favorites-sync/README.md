# Favorites Sync Worker

低风险同步层：网页仍以浏览器 `localStorage` 为主，Worker 只保存一份可手动 Pull/Push 的收藏 JSON。

## Deploy

```bash
cd workers/favorites-sync
wrangler kv namespace create FAVORITES_KV
```

把输出的 namespace `id` 填到 `wrangler.jsonc` 的 `<KV_NAMESPACE_ID>`。

```bash
wrangler secret put SYNC_KEY
wrangler deploy
```

部署后，在收藏页填入 Worker URL 和同一个 `SYNC_KEY`，然后用 `Pull` / `Push` 手动同步。

## Notes

- 不要把 `SYNC_KEY` 写入仓库。
- `ALLOWED_ORIGIN` 默认只允许 `https://huwenbo-lab.github.io`。
- Worker 只暴露 `GET`、`PUT`、`OPTIONS`，数据保存在 KV key `favorites:default`。
