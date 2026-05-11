#!/usr/bin/env node
/**
 * stock-sdk → MySQL 全量K线数据补全脚本
 *
 * 用 stock-sdk（腾讯 qt.gtimg.cn 数据源）向 MySQL stock_kline.kline 表
 * 批量写入/更新日K线数据。特别用于修复 pct_chg/change/turnover/amplitude 为 NULL 的存量行。
 *
 * 数据源: stock-sdk 库 (腾讯 ifzq.gtimg.cn 历史K线)
 * 输出: MySQL stock_kline.kline 表
 *
 * 关键列映射:
 *   stock-sdk       MySQL        说明
 *   ─────────────── ──────────── ──────────────────────
 *   date            trade_date    交易日期
 *   open/close/high/low  → 同名  开盘/收盘/最高/最低
 *   volume(手)      volume(股)    ×100 转换
 *   amount          amount        成交额(元)
 *   amplitude       amplitude     振幅%
 *   changePercent   pct_chg       涨跌幅%
 *   change          `change`      涨跌额 (MySQL保留字)
 *   turnoverRate    turnover      换手率%
 *
 * 用法:
 *   NODE_PATH=/home/pebynn/.hermes/node/lib/node_modules \
 *     node /path/to/stock_sdk_backfill.js [--limit N] [--start YYYYMMDD] [--force]
 *
 * 参数:
 *   --limit N        限制处理股票数（测试用，默认全量5512只）
 *   --start YYYYMMDD 起始日期（默认 20200101）
 *   --force          强制覆盖所有字段（默认只更新NULL字段，保留已有值）
 *
 * 注意:
 * - stock-sdk 是 ESM 模块，通过全局 npm 安装的 stock-sdk-mcp 的子依赖可用
 * - NODE_PATH 必须包含 stock-sdk 所在路径
 * - MySQL 密码硬编码在脚本中（stock123），如需改密码同步更新 DB_CONFIG
 * - 进度日志同时输出到 stdout 和 /tmp/stock_sdk_backfill_progress.txt
 * - 12路并发 + 200行 batch 写入，预估 ~30-45min 跑完 5512 只全量
 * - 北交所(92xxxx)、科创板(68xxxx)、ST股全部包含，无过滤
 */

const mysql = require('mysql2/promise');
const fs = require('fs');

const STOCK_SDK_PATH = '/home/pebynn/.hermes/node/lib/node_modules/stock-sdk-mcp/node_modules/stock-sdk/dist/index.cjs';
const { default: StockSDK } = require(STOCK_SDK_PATH);

const DB_CONFIG = {
  host: '127.0.0.1', user: 'stock', password: 'stock123',
  database: 'stock_kline', connectTimeout: 5000,
};
const BATCH_SIZE = 200;
const CONCURRENCY = 12;
const MAX_RETRIES = 3;
const PROGRESS_FILE = '/tmp/stock_sdk_backfill_progress.txt';

const args = process.argv.slice(2);
const OPT = {
  limit: parseInt(args.find(a => a.startsWith('--limit='))?.split('=')[1] || '0'),
  force: args.includes('--force'),
  startDate: args.find(a => a.startsWith('--start='))?.split('=')[1] || '20200101',
};

function sleep(ms) { return new Promise(r => setTimeout(r, ms)); }

function log(msg) {
  const ts = new Date().toISOString().slice(11, 19);
  const line = `[${ts}] ${msg}`;
  console.log(line);
  try { fs.appendFileSync(PROGRESS_FILE, line + '\n'); } catch (_) {}
}

/**
 * 列映射: stock-sdk → MySQL
 * 
 * ⚠️ volume 转换: stock-sdk 返回"手"，MySQL 存储"股"，×100
 * ⚠️ change 是 MySQL 保留字，查询时需反引号
 */
function mapRow(r) {
  return {
    code: r.code, trade_date: r.date,
    open: r.open, close: r.close, high: r.high, low: r.low,
    volume: r.volume != null ? Math.round(r.volume * 100) : null,
    amount: r.amount, amplitude: r.amplitude,
    pct_chg: r.changePercent, change_val: r.change,
    turnover: r.turnoverRate, source: 'stock_sdk',
  };
}

/**
 * COALESCE UPSERT:
 * - 非force模式: 只更新目标列为 NULL 的行，已有值保持不变
 * - force 模式: 覆盖所有字段
 */
async function upsertBatch(conn, rows) {
  if (rows.length === 0) return;
  const values = rows.map(r => [
    r.code, r.trade_date, r.open, r.close, r.high, r.low,
    r.volume, r.amount, r.amplitude, r.pct_chg, r.change_val,
    r.turnover, r.source,
  ]);

  if (OPT.force) {
    await conn.query(`INSERT INTO kline
      (code, trade_date, open, close, high, low, volume, amount, amplitude, pct_chg, \`change\`, turnover, source)
      VALUES ? ON DUPLICATE KEY UPDATE
        open=VALUES(open), close=VALUES(close), high=VALUES(high), low=VALUES(low),
        volume=VALUES(volume), amount=VALUES(amount), amplitude=VALUES(amplitude),
        pct_chg=VALUES(pct_chg), \`change\`=VALUES(\`change\`), turnover=VALUES(turnover),
        source=VALUES(source)`, [values]);
  } else {
    await conn.query(`INSERT INTO kline
      (code, trade_date, open, close, high, low, volume, amount, amplitude, pct_chg, \`change\`, turnover, source)
      VALUES ? ON DUPLICATE KEY UPDATE
        open=COALESCE(VALUES(open), kline.open),
        close=COALESCE(VALUES(close), kline.close),
        high=COALESCE(VALUES(high), kline.high),
        low=COALESCE(VALUES(low), kline.low),
        volume=COALESCE(VALUES(volume), kline.volume),
        amount=COALESCE(VALUES(amount), kline.amount),
        amplitude=COALESCE(VALUES(amplitude), kline.amplitude),
        pct_chg=COALESCE(VALUES(pct_chg), kline.pct_chg),
        \`change\`=COALESCE(VALUES(\`change\`), kline.\`change\`),
        turnover=COALESCE(VALUES(turnover), kline.turnover),
        source=COALESCE(VALUES(source), kline.source)`, [values]);
  }
}

async function main() {
  const sdk = new StockSDK();
  const conn = await mysql.createConnection(DB_CONFIG);

  log(`获取A股列表...`);
  const codes = await sdk.getAShareCodeList({ simple: true });
  log(`共 ${codes.length} 只股票`);

  const targetCodes = OPT.limit > 0 ? codes.slice(0, OPT.limit) : codes;
  log(`目标: ${targetCodes.length} 股票, 起始: ${OPT.startDate}, 强制: ${OPT.force}`);

  let totalRows = 0, totalStocks = 0, failedStocks = 0;
  let batch = [];
  const startTime = Date.now();

  async function processStock(code) {
    for (let attempt = 1; attempt <= MAX_RETRIES; attempt++) {
      try {
        const kline = await sdk.getHistoryKline(code, {
          period: 'daily', adjust: 'qfq', startDate: OPT.startDate,
        });
        if (!kline || kline.length === 0) return 0;

        const mapped = kline.map(mapRow);
        batch.push(...mapped);

        while (batch.length >= BATCH_SIZE) {
          const toInsert = batch.splice(0, BATCH_SIZE);
          await upsertBatch(conn, toInsert);
        }
        return mapped.length;
      } catch (err) {
        if (attempt < MAX_RETRIES) {
          log(`  [RETRY ${attempt}] ${code}: ${err.message.slice(0, 80)}`);
          await sleep(2000 * attempt);
        } else {
          log(`  [FAIL] ${code}: ${err.message.slice(0, 80)}`);
          return -1;
        }
      }
    }
    return -1;
  }

  const worker = async (startIdx) => {
    for (let i = startIdx; i < targetCodes.length; i += CONCURRENCY) {
      const code = targetCodes[i];
      if (i % 100 === 0) {
        const elapsed = ((Date.now() - startTime) / 60000).toFixed(1);
        log(`[${((i / targetCodes.length) * 100).toFixed(1)}%] ${i}/${targetCodes.length} | ${totalRows} rows | ${elapsed}min`);
        await sleep(100);
      }
      const n = await processStock(code);
      n >= 0 ? (totalRows += n, totalStocks++) : failedStocks++;
    }
  };

  const workers = Array.from({ length: CONCURRENCY }, (_, w) => worker(w));
  await Promise.all(workers);

  if (batch.length > 0) {
    await upsertBatch(conn, batch);
  }

  const elapsed = ((Date.now() - startTime) / 60000).toFixed(1);
  log(`\n完成: ${totalStocks} stocks, ${failedStocks} failed, ${totalRows} rows, ${elapsed}min`);

  const [rows] = await conn.query(
    `SELECT source, COUNT(*) as cnt, COUNT(pct_chg) as pct FROM kline GROUP BY source`
  );
  log('数据源分布:');
  rows.forEach(r => log(`  ${r.source}: ${r.cnt}行 pct_chg=${r.pct}`));

  await conn.end();
}

main().catch(err => { console.error('FATAL:', err); process.exit(1); });
