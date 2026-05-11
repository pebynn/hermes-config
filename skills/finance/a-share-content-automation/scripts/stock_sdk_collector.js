#!/usr/bin/env node
/**
 * stock-sdk collector for a-share-content-automation pipeline.
 * Called via subprocess by collect_data.py.
 *
 * Collects: up/down stats + limit up/down detection from ALL A-share stocks.
 * Data source: stock-sdk (Tencent qt.gtimg.cn primary + EastMoney batch fallback)
 *
 * Usage: NODE_PATH=/home/pebynn/.hermes/node/lib/node_modules \\
 *        node /tmp/stock_sdk_collector.js
 *
 * Source file (copy to /tmp/ after reboot):
 *   ~/.hermes/skills/finance/a-share-content-automation/scripts/stock_sdk_collector.js
 *
 * Output: JSON to stdout with up_down_stats + limit_stocks
 *
 * Dependencies: npm -g stock-sdk-mcp (provides stock-sdk CJS dist)
 */
const {default: StockSDK} = require('/home/pebynn/.hermes/node/lib/node_modules/stock-sdk-mcp/node_modules/stock-sdk/dist/index.cjs');
const sdk = new StockSDK();

async function main() {
  const result = { up_down_stats: {}, limit_stocks: {}, _errors: [] };

  try {
    const all = await sdk.getAllAShareQuotes({ market: 'all', batchSize: 2000, concurrency: 3 });
    if (!all || all.length === 0) throw new Error('empty response');

    let up=0, down=0, flat=0, limitUp=0, limitDown=0;
    const limitUpSamples = [], limitDownSamples = [];

    for (const s of all) {
      const cp = s.changePercent;
      const code = String(s.code || '');
      const name = s.name || '';

      // Filter out 北交所 / ST / delisted
      if (code.startsWith('8') || code.startsWith('92') || code.startsWith('4')) continue;
      if (name.includes('ST') || name.includes('退')) continue;

      if (cp > 0) up++;
      else if (cp < 0) down++;
      else flat++;

      if (cp >= 9.5) {
        limitUp++;
        if (limitUpSamples.length < 50) {
          limitUpSamples.push({ code, name, price: s.price, change_pct: cp, turnover: s.amount });
        }
      } else if (cp <= -9.5) {
        limitDown++;
        if (limitDownSamples.length < 20) {
          limitDownSamples.push({ code, name, price: s.price, change_pct: cp, turnover: s.amount });
        }
      }
    }

    result.up_down_stats = {
      up, down, flat,
      limit_up: limitUp, limit_down: limitDown,
      source: 'stock_sdk'
    };
    result.limit_stocks = {
      limit_up: { total: limitUp, samples: limitUpSamples },
      limit_down: { total: limitDown, samples: limitDownSamples }
    };
    result._total_stocks = all.length;

  } catch(e) {
    result._errors.push('all_quotes: ' + e.message);
  }

  console.log(JSON.stringify(result));
}

main().catch(e => {
  console.log(JSON.stringify({ _errors: ['fatal: ' + e.message] }));
  process.exit(1);
});
