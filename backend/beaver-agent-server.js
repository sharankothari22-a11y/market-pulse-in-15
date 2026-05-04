/**
 * beaver-agent/server.js
 *
 * Copy this file to ~/Desktop/beaver-agent/server.js on your Mac.
 *
 * Assumes the following layout on your Mac:
 *   ~/Desktop/beaver-agent/
 *     modeling.js          ← exports getDrivers(ticker) → Promise<{ticker, drivers[]}>
 *     server.js            ← THIS FILE
 *   ~/Desktop/war-room-module/
 *     warRoom.js           ← exports runWarRoom({ticker, dcf, drivers}) → Promise<{ticker, vote, confidence, final_report, debate_summary, citations[]}>
 *
 * If your module filenames or export shapes differ, adjust the two
 * ADAPTER blocks below — everything else stays the same.
 */

'use strict';

const express = require('express');

// ── ADAPTER: adjust these paths if your modules live elsewhere ────────────
let getDrivers, runWarRoom;

try {
  const modeling = require('./modeling.js');
  // Support both  module.exports = fn  and  module.exports = { getDrivers }
  getDrivers = typeof modeling === 'function' ? modeling : modeling.getDrivers || modeling.default;
} catch (err) {
  console.error('[beaver-server] Could not load modeling.js:', err.message);
  getDrivers = null;
}

// try {
//   const warRoomMod = require('../war-room-module/warRoom.js');
//   runWarRoom = typeof warRoomMod === 'function' ? warRoomMod : warRoomMod.runWarRoom || warRoomMod.default;
// } catch (err) {
//   console.error('[beaver-server] Could not load war-room-module/warRoom.js:', err.message);
//   runWarRoom = null;
// }
runWarRoom = null;
// ──────────────────────────────────────────────────────────────────────────

const PORT = process.env.PORT || 3001;
const app = express();
app.use(express.json({ limit: '2mb' }));

// Health check
app.get('/health', (_req, res) => res.json({ ok: true, ts: new Date().toISOString() }));

/**
 * POST /drivers
 * Body: { ticker: string, metric?: string, premium?: boolean }
 * Returns: { ticker, drivers: [...] }
 */
app.post('/drivers', async (req, res) => {
  const ticker = (req.body.ticker || '').toUpperCase().replace('.NS', '');
  if (!ticker) return res.status(400).json({ error: 'ticker required', drivers: [] });

  if (!getDrivers) {
    return res.status(503).json({ error: 'modeling.js not loaded', drivers: [] });
  }

  try {
    const result = await Promise.race([
      getDrivers(ticker, { metric: req.body.metric || 'drivers', premium: !!req.body.premium }),
      new Promise((_, reject) => setTimeout(() => reject(new Error('timeout')), 25000)),
    ]);
    // Normalise: ensure result has a drivers array
    if (Array.isArray(result)) {
      return res.json({ ticker, drivers: result });
    }
    return res.json(result);
  } catch (err) {
    console.error(`[/drivers] ${ticker}:`, err.message);
    return res.status(500).json({ error: err.message, ticker, drivers: [] });
  }
});

/**
 * POST /warroom
 * Body: { ticker: string, dcf?: object, drivers?: array }
 * Returns: { ticker, vote, confidence, final_report, debate_summary, citations }
 */
app.post('/warroom', async (_req, res) => {
  return res.status(503).json({ error: 'War room not enabled in tunnel mode — using Emergent stubs' });
});

app.listen(PORT, () => {
  console.log(`[beaver-server] Listening on http://localhost:${PORT}`);
  console.log(`[beaver-server] getDrivers loaded: ${!!getDrivers}`);
  console.log(`[beaver-server] runWarRoom  loaded: ${!!runWarRoom}`);
});
