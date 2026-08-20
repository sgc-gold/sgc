(function(global) {
  "use strict";

  const TIMEOUT_MS = 8000;
  // 転載ポータルを避け、一次配信に近い主要メディアだけを表示する。
  // 並び順は、同じ記事が複数社から配信された場合の優先順位にも使う。
  const MAIN_NEWS_SOURCES = [
    /NHK(?: NEWS WEB)?/i,
    /日本経済新聞|日経(?:電子版|新聞)?|NIKKEI/i,
    /共同通信|時事通信/i,
    /読売新聞|朝日新聞|毎日新聞|産経新聞|東京新聞/i,
    /ロイター|Reuters(?: Japan)?/i,
    /ブルームバーグ|Bloomberg/i,
    /TBS NEWS DIG|TBSテレビ|テレビ朝日|テレ朝news|日本テレビ|日テレNEWS|FNNプライムオンライン|フジテレビ|テレビ東京|テレ東BIZ/i,
    /QUICK Money World|QUICK/i,
    /みんかぶ|株探ニュース|日本証券新聞/i
  ];
  const TOPIC_QUERY = {
    all: "SGC OR SGCホール OR 大黄金展 OR 金相場 OR 金価格 OR NY金 OR 金先物 OR 金密輸 OR 金塊 密輸 OR 金塊強盗 OR 金 強盗 OR 貴金属 強盗",
    goldMarket: "金相場 OR 金価格 OR ゴールド価格 OR NY金 OR 金先物 OR スポット金 OR 現物金 OR 地金価格",
    goldCrime: "金密輸 OR 金塊 密輸 OR 金地金 密輸 OR 金塊強盗 OR 金 強盗 OR 金地金 強盗 OR 貴金属 強盗 OR 地金 強盗"
  };
  const TOPIC_QUERIES = {
    all: [
      "SGC OR SGCホール OR 大黄金展 OR 金相場 OR 金価格 OR NY金 OR 金先物 OR 金密輸 OR 金塊 密輸 OR 金塊強盗 OR 金 強盗 OR 貴金属 強盗"
    ],
    goldCrime: [
      "SGC OR SGCホール OR 大黄金展 OR 金相場 OR 金価格 OR NY金 OR 金先物 OR 金密輸 OR 金塊 密輸 OR 金塊強盗 OR 金 強盗 OR 貴金属 強盗",
      "金密輸 OR 金塊 密輸 OR 金地金 密輸",
      "金塊強盗 OR 金 強盗 OR 金地金 強盗 OR 貴金属 強盗 OR 地金 強盗 OR インゴット 強盗"
    ],
    exhibition: [
      "SGC OR SGCホール OR 大黄金展 OR 金相場 OR 金価格 OR NY金 OR 金先物 OR 金密輸 OR 金塊 密輸 OR 金塊強盗 OR 金 強盗 OR 貴金属 強盗",
      "大黄金展",
      "大黄金展 Yahoo!ニュース",
      "大黄金展 SGC"
    ]
  };

  function fetchWithTimeout(url, opts = {}) {
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), TIMEOUT_MS);
    return fetch(url, { ...opts, signal: controller.signal })
      .finally(() => clearTimeout(timer));
  }

  function buildRssUrl(query) {
    return `https://news.google.com/rss/search?q=${encodeURIComponent(query)}&hl=ja&gl=JP&ceid=JP:ja`;
  }

  async function tryRss2json(rssUrl) {
    const api = `https://api.rss2json.com/v1/api.json?rss_url=${encodeURIComponent(rssUrl)}&count=50&order_by=pubDate&order_dir=desc`;
    const res = await fetchWithTimeout(api);
    if (!res.ok) throw new Error(`rss2json ${res.status}`);
    const d = await res.json();
    if (d.status !== "ok" || !d.items?.length) throw new Error("rss2json: empty");
    return d.items.map(normalizeRss2jsonItem);
  }

  async function tryAllOrigins(rssUrl) {
    const api = `https://api.allorigins.win/get?url=${encodeURIComponent(rssUrl)}`;
    const res = await fetchWithTimeout(api);
    if (!res.ok) throw new Error(`allorigins ${res.status}`);
    const d = await res.json();
    const items = parseXml(d.contents);
    if (!items.length) throw new Error("allorigins: empty");
    return items;
  }

  async function tryCorsproxy(rssUrl) {
    const api = `https://corsproxy.io/?${encodeURIComponent(rssUrl)}`;
    const res = await fetchWithTimeout(api);
    if (!res.ok) throw new Error(`corsproxy ${res.status}`);
    const xml = await res.text();
    const items = parseXml(xml);
    if (!items.length) throw new Error("corsproxy: empty");
    return items;
  }

  async function tryThingproxy(rssUrl) {
    const api = `https://thingproxy.freeboard.io/fetch/${rssUrl}`;
    const res = await fetchWithTimeout(api);
    if (!res.ok) throw new Error(`thingproxy ${res.status}`);
    const xml = await res.text();
    const items = parseXml(xml);
    if (!items.length) throw new Error("thingproxy: empty");
    return items;
  }

  async function tryFeedrapp(rssUrl) {
    const api = `https://feedrapp.info/api?q=${encodeURIComponent(rssUrl)}&num=50&output=json`;
    const res = await fetchWithTimeout(api);
    if (!res.ok) throw new Error(`feedrapp ${res.status}`);
    const d = await res.json();
    const entries = d.responseData?.feed?.entries;
    if (!entries?.length) throw new Error("feedrapp: empty");
    return entries.map(e => ({
      title: e.title || "",
      link: e.link || "",
      pubDate: e.publishedDate || "",
      description: e.contentSnippet || e.content || "",
      source: e.publisher || ""
    }));
  }

  async function fetchNews(query) {
    const rssUrl = buildRssUrl(query);
    const tryProxy = fn => fn(rssUrl).catch(e => { console.warn(e.message); return null; });
    const results = await Promise.all([
      tryProxy(tryRss2json),
      tryProxy(tryAllOrigins),
      tryProxy(tryCorsproxy),
      tryProxy(tryThingproxy),
      tryProxy(tryFeedrapp)
    ]);

    const merged = dedupeNewsItems(results.flatMap(items => items || []));
    return merged.length ? sortByDateDesc(merged) : null;
  }

  async function fetchTopicNews(topic, fallbackQuery) {
    const queries = TOPIC_QUERIES[topic] || [fallbackQuery || TOPIC_QUERY[topic] || TOPIC_QUERY.all];
    const results = await Promise.all(
      queries.map(query => fetchNews(query).catch(e => { console.warn(e.message); return null; }))
    );
    const merged = dedupeNewsItems(results.flatMap(items => items || []));
    if (!merged.length) return null;
    if (topic === "goldMarket") return sortByDateDesc(merged.filter(isJapanFocusedArticle));
    return sortByDateDesc(merged);
  }

  function parseXml(xmlStr) {
    if (!xmlStr) return [];
    try {
      const parser = new DOMParser();
      const doc = parser.parseFromString(xmlStr, "text/xml");
      if (doc.querySelector("parsererror")) throw new Error("XML parse error");

      return Array.from(doc.querySelectorAll("item")).map(item => {
        let link = "";
        const linkEl = item.querySelector("link");
        if (linkEl) {
          link = linkEl.textContent ||
                 (linkEl.nextSibling?.nodeType === 3 ? linkEl.nextSibling.textContent : "") ||
                 linkEl.getAttribute("href") || "";
        }

        const sourceEl = item.querySelector("source");
        const source = sourceEl?.textContent || sourceEl?.getAttribute("url") || "";

        return {
          title: item.querySelector("title")?.textContent || "",
          link: link.trim(),
          pubDate: item.querySelector("pubDate")?.textContent || "",
          description: item.querySelector("description")?.textContent || "",
          source
        };
      });
    } catch(e) {
      console.warn("parseXml:", e.message);
      return [];
    }
  }

  function normalizeRss2jsonItem(item) {
    return {
      title: item.title || "",
      link: item.link || item.guid || "",
      pubDate: item.pubDate || item.isoDate || "",
      description: item.description || item.content || "",
      source: item.author || (item.source?.name) || ""
    };
  }

  function sortByDateDesc(items) {
    return [...items].sort((a, b) => {
      const da = a.pubDate ? new Date(a.pubDate).getTime() : 0;
      const db = b.pubDate ? new Date(b.pubDate).getTime() : 0;
      return db - da;
    });
  }

  function dedupeNewsItems(items) {
    const out = [];
    sortByDateDesc(items || []).forEach(item => {
      const duplicateIndex = out.findIndex(existing => isSameNewsStory(existing, item));
      if (duplicateIndex < 0) {
        out.push(item);
        return;
      }

      // 同一記事なら、転載元より優先度の高い主要メディアの記事を残す。
      if (getSourcePriority(item) < getSourcePriority(out[duplicateIndex])) {
        out[duplicateIndex] = item;
      }
    });
    return out;
  }

  function isSameNewsStory(a, b) {
    const linkA = normalizeLink(a?.link);
    const linkB = normalizeLink(b?.link);
    if (linkA && linkA === linkB) return true;

    const titleA = normalizeStoryTitle(getDisplayTitle(a));
    const titleB = normalizeStoryTitle(getDisplayTitle(b));
    if (!titleA || !titleB) return false;
    if (titleA === titleB) return true;
    if (!isPublishedNear(a, b)) return false;

    const shorter = titleA.length <= titleB.length ? titleA : titleB;
    const longer = titleA.length > titleB.length ? titleA : titleB;
    if (shorter.length >= 12 && longer.includes(shorter)) return true;

    return bigramSimilarity(titleA, titleB) >= 0.64;
  }

  function normalizeLink(link) {
    return (link || "")
      .replace(/[?#].*$/, "")
      .replace(/\/$/, "")
      .trim()
      .toLowerCase();
  }

  function normalizeStoryTitle(title) {
    return (title || "")
      .normalize("NFKC")
      .toLowerCase()
      .replace(/【(?:速報|続報|独自|解説|更新)】/g, "")
      .replace(/[「」『』【】\[\]（）()〈〉《》]/g, "")
      .replace(/[\s\u3000・,，.。!！?？:：;；\-‐‑–—―]/g, "")
      .trim();
  }

  function bigramSimilarity(a, b) {
    const grams = value => {
      const set = new Set();
      for (let i = 0; i < value.length - 1; i++) set.add(value.slice(i, i + 2));
      return set;
    };
    const gramsA = grams(a);
    const gramsB = grams(b);
    if (!gramsA.size || !gramsB.size) return 0;
    let intersection = 0;
    gramsA.forEach(gram => { if (gramsB.has(gram)) intersection++; });
    return (2 * intersection) / (gramsA.size + gramsB.size);
  }

  function isPublishedNear(a, b) {
    const timeA = a?.pubDate ? new Date(a.pubDate).getTime() : NaN;
    const timeB = b?.pubDate ? new Date(b.pubDate).getTime() : NaN;
    if (!Number.isFinite(timeA) || !Number.isFinite(timeB)) return true;
    return Math.abs(timeA - timeB) <= 48 * 60 * 60 * 1000;
  }

  function getTitleSource(item) {
    const rawTitle = item?.title || "";
    const match = rawTitle.match(/\s[-–]\s*([^-–]+)$/);
    return match ? match[1].trim() : "";
  }

  function getSourcePriority(item) {
    const source = `${item?.source || ""} ${getTitleSource(item)}`;
    const index = MAIN_NEWS_SOURCES.findIndex(pattern => pattern.test(source));
    return index < 0 ? MAIN_NEWS_SOURCES.length : index;
  }

  function isMainNewsSource(item) {
    return getSourcePriority(item) < MAIN_NEWS_SOURCES.length;
  }

  function getSearchText(item) {
    return [
      item?.title || "",
      item?.description || "",
      item?.source || ""
    ].join(" ")
      .replace(/<[^>]+>/g, " ")
      .replace(/&nbsp;|&amp;|&lt;|&gt;|&quot;/g, " ")
      .replace(/\s+/g, " ")
      .trim();
  }

  function getDisplayTitle(item) {
    const rawTitle = item?.title || "";
    const srcMatch = rawTitle.match(/\s[-–]\s*([^-–]+)$/);
    return srcMatch ? rawTitle.slice(0, rawTitle.lastIndexOf(srcMatch[0])).trim() : rawTitle.trim();
  }

  function getSource(item) {
    const rawTitle = item?.title || "";
    const srcMatch = rawTitle.match(/\s[-–]\s*([^-–]+)$/);
    return item?.source || (srcMatch ? srcMatch[1].trim() : "");
  }

  function getCleanDescription(item) {
    return (item?.description || "")
      .replace(/<[^>]+>/g, " ")
      .replace(/&nbsp;/g, " ")
      .replace(/&amp;/g, "&")
      .replace(/&lt;/g, "<")
      .replace(/&gt;/g, ">")
      .replace(/&quot;/g, '"')
      .replace(/\s+/g, " ")
      .trim();
  }

  function isSgcHallArticle(text) {
    return /SGCホール|ＳＧＣホール|sgc\s*hall/i.test(text || "");
  }

  function isExhibitionArticle(text) {
    if (!text) return false;
    return /大黄金展/.test(text);
  }

  function isGoldMarketArticle(text) {
    if (!text) return false;

    const unrelatedMoney = /金メダル|給付金|補助金|助成金|税金|料金|資金|基金|賃金|年金|罰金|預金|送金|借金|金曜|金曜日|金庫|金具|金型|黄金週間|ゴールデンウィーク/;
    const explicitMarket = /金相場|金価格|ゴールド価格|地金価格|国内金価格|純金価格|金地金価格|NY金|ＮＹ金|COMEX金|ＣＯＭＥＸ金|金先物|スポット金|現物金|貴金属市況|金市況|XAU|Gold price/i;
    const goldAsset = /金地金|地金|純金|ゴールド|貴金属|金ＥＴＦ|金ETF|金投資|金需要|金保有|中央銀行.*金|金.*中央銀行/i;
    const marketContext = /相場|市況|価格|先物|現物|スポット|上昇|下落|続伸|反落|高値|安値|最高値|最安値|ドル|米金利|長期金利|FRB|ＦＲＢ|FOMC|インフレ|安全資産|利下げ|利上げ|為替|円建て|ドル建て/i;
    const buyAdContext = /買取店|高価買取|買取専門|査定|キャンペーン|ブランド品|ジュエリー買取|出張買取|宅配買取/;

    if (explicitMarket.test(text)) return true;
    if (unrelatedMoney.test(text) && !goldAsset.test(text)) return false;
    if (buyAdContext.test(text) && !marketContext.test(text)) return false;

    return goldAsset.test(text) && marketContext.test(text);
  }

  function isJapanFocusedArticle(item) {
    const source = getSource(item);
    const text = getSearchText(item);
    const link = item?.link || "";
    const haystack = `${source} ${text} ${link}`;

    const blockedSource = /VIETNAM\.VN|Vietnam\.vn|vietnam\.vn|ベトナム|Vietnam News|VNExpress|VnExpress|Tuoi Tre|Thanh Nien/i;
    if (blockedSource.test(haystack)) return false;

    const knownJapanSource = /Yahoo!ニュース|Yahooニュース|NHK|日本経済新聞|日経|時事通信|共同通信|読売新聞|朝日新聞|毎日新聞|産経新聞|TBS|テレビ朝日|テレ朝|FNN|日テレ|日本テレビ|フジテレビ|テレビ東京|ロイター|Reuters Japan|ブルームバーグ|Bloomberg|みんかぶ|株探|QUICK|モーニングスター|日本証券新聞|財経新聞|東洋経済|ダイヤモンド・オンライン|JBpress|Impress Watch|ITmedia|レスポンス|マイナビニュース|All About|au Webポータル|goo ニュース|livedoor ニュース|BIGLOBEニュース/i;
    if (knownJapanSource.test(haystack)) return true;

    const japaneseChars = (text.match(/[ぁ-んァ-ン一-龥]/g) || []).length;
    const latinChars = (text.match(/[A-Za-z]/g) || []).length;
    if (japaneseChars >= 20 && japaneseChars >= latinChars) return true;

    return false;
  }

  function isGoldSmugglingArticle(text) {
    return /金密輸|金塊密輸|金地金密輸|金塊\s*密輸|金地金\s*密輸|密輸.*(?:金|金塊|金地金)|(?:金|金塊|金地金).*密輸/.test(text || "");
  }

  function isGoldRobberyArticle(text) {
    if (!text) return false;
    const goldTarget = /金塊|金地金|地金|純金|貴金属|金製品|金の延べ棒|延べ棒|インゴット|ゴールド/;
    const robbery = /強盗|強奪|奪う|奪われ|盗難|窃盗|盗まれ|盗む|押し入り|押し入った/;
    const unrelated = /金庫|金具|金型|資金|現金|預金|送金|借金|料金|給付金|補助金|助成金/;

    if (/金塊強盗|金地金強盗|貴金属強盗|地金強盗/.test(text)) return true;
    if (unrelated.test(text) && !goldTarget.test(text)) return false;
    return goldTarget.test(text) && robbery.test(text);
  }

  function isGoldCrimeArticle(text) {
    return isGoldSmugglingArticle(text) || isGoldRobberyArticle(text);
  }

  function getCrimeLabel(text) {
    if (isGoldRobberyArticle(text)) return "金塊強盗";
    if (isGoldSmugglingArticle(text)) return "金密輸";
    return "";
  }

  function getTopicLabel(item) {
    const text = getSearchText(item);
    const crimeLabel = getCrimeLabel(text);
    if (crimeLabel) return crimeLabel;
    if (isGoldMarketArticle(text)) return "金相場";
    if (isExhibitionArticle(text)) return "大黄金展";
    if (/sgc/i.test(text) || isSgcHallArticle(text)) return "SGC";
    return "ニュース";
  }

  function getTopicClass(item) {
    const text = getSearchText(item);
    if (isGoldCrimeArticle(text)) return "crime";
    if (isGoldMarketArticle(text)) return "market";
    if (isExhibitionArticle(text)) return "exhibition";
    if (/sgc/i.test(text) || isSgcHallArticle(text)) return "sgc";
    return "general";
  }

  function filterNewsItems(items, topic) {
    if (!items?.length) return [];
    const filtered = dedupeNewsItems(items.filter(item => {
      const text = getSearchText(item);
      if (topic === "goldMarket") return isGoldMarketArticle(text) && isJapanFocusedArticle(item);
      if (topic === "goldCrime" || topic === "goldSmuggling") return isGoldCrimeArticle(text);
      if (topic === "sgcHall") return isSgcHallArticle(text);
      if (topic === "exhibition") return isExhibitionArticle(text);

      return /sgc|SGCホール|ＳＧＣホール|大黄金展/i.test(text) ||
             isGoldMarketArticle(text) ||
             isGoldCrimeArticle(text);
    }));
    return sortByDateDesc(filtered);
  }

  function excludeSgcHall(items) {
    return (items || []).filter(item => !isSgcHallArticle(getSearchText(item)));
  }

  global.PortalNewsFeed = {
    TOPIC_QUERY,
    fetchNews,
    fetchTopicNews,
    filterNewsItems,
    sortByDateDesc,
    getSearchText,
    getDisplayTitle,
    getSource,
    getCleanDescription,
    isGoldMarketArticle,
    isGoldSmugglingArticle,
    isGoldRobberyArticle,
    isGoldCrimeArticle,
    isJapanFocusedArticle,
    getCrimeLabel,
    getTopicLabel,
    getTopicClass,
    isMainNewsSource,
    dedupeNewsItems,
    excludeSgcHall
  };
})(window);
