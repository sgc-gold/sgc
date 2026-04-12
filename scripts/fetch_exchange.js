// scripts/fetch_exchange.js
const fs = require("fs");
const path = require("path");
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

    // ✅ 絶対パスで指定（GitHub Actionsでもズレない）
    const outputPath = path.join(__dirname, "../data/exchange_rate.json");

    // JSONデータ
    const outputData = { rate, date };

    fs.writeFileSync(outputPath, JSON.stringify(outputData, null, 2), "utf8");

    console.log(`✅ USD/JPY updated: ${rate} (${date})`);
    console.log(`💾 Saved to: ${outputPath}`);
  } catch (err) {
    console.error("❌ Failed to update exchange rate:", err);
    process.exit(1); // ← エラー時に終了コード1を返すように（GitHub Actionsで検知可能）
  }
}

updateExchange();
