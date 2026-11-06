const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const { test } = require('node:test');

const source = fs.readFileSync(path.join(__dirname, '../scripts/fetch_exchange.js'), 'utf8');

async function runWith(data, fetchError) {
  const writes = [];
  const exits = [];
  const urls = [];
  const context = {
    __dirname: path.join(__dirname, '../scripts'),
    require(name) {
      if (name === 'fs') return { writeFileSync: (...args) => writes.push(args) };
      if (name === 'path') return path;
      throw new Error(`Unexpected dependency: ${name}`);
    },
    fetch: async (url) => {
      urls.push(url);
      if (fetchError) throw fetchError;
      return { json: async () => data };
    },
    console: { log() {}, error() {} },
    process: { exit: (code) => exits.push(code) },
  };
  await vm.runInNewContext(source, context);
  return { writes, exits, urls };
}

test('native fetch keeps USDJPY bid, output path, and JSON contract', async () => {
  const result = await runWith({ quotes: [{ currencyPairCode: 'EURJPY', bid: '160.00' }, { currencyPairCode: 'USDJPY', bid: '149.25' }] });
  assert.deepEqual(result.urls, ['https://www.gaitameonline.com/rateaj/getrate']);
  assert.equal(result.writes.length, 1);
  assert.equal(result.writes[0][0], path.resolve(__dirname, '../data/exchange_rate.json'));
  const json = JSON.parse(result.writes[0][1]);
  assert.equal(json.rate, 149.25);
  assert.ok(Number.isFinite(Date.parse(json.date)));
  assert.deepEqual(result.exits, []);
});

test('invalid provider responses and network failures do not overwrite prices', async () => {
  for (const [data, error] of [[{}, null], [{ quotes: [] }, null], [null, new Error('offline')]]) {
    const result = await runWith(data, error);
    assert.deepEqual(result.writes, []);
    assert.deepEqual(result.exits, [1]);
  }
});
