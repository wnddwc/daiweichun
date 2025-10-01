// Cloudflare Worker: 随机重定向到 hsk.txt 中的一个 http/https 链接
const SOURCE_URL = "存储电影文件的网址";
// 缓存时间（秒）
const CACHE_TTL = 300; // 5 分钟

export default {
  async fetch(request, env, ctx) {
    try {
      const urls = await getUrlsFromSource(SOURCE_URL, ctx);
      if (!urls || urls.length === 0) {
        return new Response("No links found in source.", { status: 502 });
      }

      // 随机选一个
      const chosen = getRandomSample(urls);

      // 返回 302 重定向
      return Response.redirect(chosen, 302);

    } catch (err) {
      return new Response("Worker error: " + String(err), { status: 500 });
    }
  }
};

/**
 * 从 SOURCE_URL 获取文本并提取所有 http/https 链接
 * 使用 caches.default 做边缘缓存
 */
async function getUrlsFromSource(sourceUrl, ctx) {
  const cache = caches.default;
  const cacheKey = new Request(sourceUrl);

  // 先查缓存
  let cached = await cache.match(cacheKey);
  if (cached) {
    const text = await cached.text();
    const parsed = extractHttpUrls(text);
    if (parsed.length > 0) return parsed;
  }

  // 没命中，去源站请求
  const resp = await fetch(sourceUrl, {
    cf: { cacheTtl: 0 } // 这里禁止 Cloudflare 自动缓存，完全用 Worker 缓存控制
  });
  if (!resp.ok) throw new Error(`Failed to fetch source: ${resp.status}`);
  const bodyText = await resp.text();

  // 放入缓存（异步，不阻塞主流程）
  ctx.waitUntil(
    cache.put(
      cacheKey,
      new Response(bodyText, {
        headers: {
          "Content-Type": "text/plain; charset=utf-8",
          "Cache-Control": `public, max-age=${CACHE_TTL}`
        }
      })
    )
  );

  return extractHttpUrls(bodyText);
}

/**
 * 提取文本中的 http(s) 链接
 */
function extractHttpUrls(text) {
  if (!text) return [];
  const regex = /https?:\/\/[^\s"'<>)]+/gi;
  const matches = text.match(regex) || [];
  const cleaned = matches.map(u => u.replace(/[.,;:)\]}]+$/, ""));
  // 去重
  const seen = new Set();
  const out = [];
  for (const u of cleaned) {
    if (!seen.has(u)) {
      seen.add(u);
      out.push(u);
    }
  }
  return out;
}

/**
 * 从数组里随机取一个
 */
function getRandomSample(arr) {
  const rand32 = crypto.getRandomValues(new Uint32Array(1))[0];
  return arr[Math.floor((rand32 / 0x100000000) * arr.length)];
}
