// fetch_exchange.js
const fs = require('fs');
const fetch = require('node-fetch');

async function updateExchange() {
  try {
    const res = await fetch('https://api.exchangerate.host/latest?base=USD&symbols=JPY');
    const data = await res.json();
    const rate = data.rates.JPY;

    // JSONに保存
    fs.writeFileSync('exchange_rate.json', JSON.stringify({ rate, date: new Date().toISOString() }, null, 2));
    console.log('Exchange rate updated:', rate);
  } catch (err) {
    console.error(err);
  }
}

updateExchange();
