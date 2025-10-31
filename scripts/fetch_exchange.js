// scripts/fetch_exchange.js
const fs = require('fs');
const fetch = require('node-fetch');

async function updateExchange() {
  try {
    const res = await fetch('https://api.exchangerate.host/latest?base=USD&symbols=JPY');
    const data = await res.json();
    const rate = data.rates?.JPY;

    if (!rate) throw new Error("JPY rate not found in API response");

    // ✅ dataフォルダに出力
    const outputPath = 'data/exchange_rate.json';
    const jsonData = {
      base: "USD",
      target: "JPY",
      rate,
      date: new Date().toISOString()
    };

    fs.writeFileSync(outputPath, JSON.stringify(jsonData, null, 2), 'utf8');
    console.log('✅ Exchange rate updated:', jsonData);

  } catch (err) {
    console.error('❌ Failed to update exchange rate:', err);
  }
}

updateExchange();
