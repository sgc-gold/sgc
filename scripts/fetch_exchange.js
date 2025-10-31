// scripts/fetch_exchange.js
const fs = require("fs");
const fetch = (...args) => import("node-fetch").then(({ default: fetch }) => fetch(...args));

async function updateExchange() {
  try {
    const res = await fetch("https://www.gaitameonline.com/rateaj/getrate");
    const data = await res.json();

    if (!data.quotes) throw new Error("Invalid API response");

    // USDJPY のデータを探す
    const usdJpy = data.quotes.find(q => q.currencyPairCode === "USDJPY");
    if (!usdJpy) throw new Error("USDJPY not found in API response");

    const rate = parseFloat(usdJpy.bid);
    const date = new Date().toISOString();

    // 保存先ファイル（dataフォルダ配下）
    const outputPath = "data/exchange_rate.json";
    const outputData = { rate, date };

    fs.writeFileSync(outputPath, JSON.stringify(outputData, null, 2), "utf8");
    console.log(`✅ USD/JPY updated: ${rate} (${date})`);
  } catch (err) {
    console.error("❌ Failed to update exchange rate:", err);
  }
}

updateExchange();
