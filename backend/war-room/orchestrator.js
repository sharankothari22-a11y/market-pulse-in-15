#!/usr/bin/env node
/**
 * War Room Orchestrator — stub for demo
 * Accepts --ticker and --input (JSON string with dcf + drivers).
 * Returns a realistic multi-analyst debate verdict.
 */

const args = process.argv.slice(2);
const tickerIdx = args.indexOf('--ticker');
const ticker = tickerIdx !== -1 ? args[tickerIdx + 1] : null;
const inputIdx = args.indexOf('--input');
const inputRaw = inputIdx !== -1 ? args[inputIdx + 1] : '{}';

let input = {};
try { input = JSON.parse(inputRaw); } catch (e) {}

const VERDICTS = {
  'HDFCBANK': {
    ticker: 'HDFCBANK',
    vote: 'YES',
    confidence: 78,
    final_report: `HDFC Bank — Investment Verdict: ACCUMULATE (12-month target ₹1,980)

The war room reached a majority BUY vote (4 of 5 analysts) at ₹1,680 CMP, implying ~18% upside to our blended fair value of ₹1,980.

CORE THESIS: HDFC Bank is executing a textbook post-merger balance sheet repair. The loan-to-deposit ratio, which spiked to 110% following the HDFC Ltd merger, is normalising faster than consensus expects — Q3FY25 showed a 250 bps QoQ improvement. Once LDR normalises to 90% (our estimate: Q2FY26), the stock's re-rating catalyst triggers.

BULL CASE (₹2,200): NIM stabilises at 3.5%+ by H2FY26 as deposit repricing completes. Fee income (insurance, mutual fund distribution) grows 18% YoY providing an NIR buffer. CASA ratio holds above 42%. P/BV re-rates to 2.4x — in line with the 5-year average.

BEAR CASE (₹1,450): RBI rate cuts accelerate to 75 bps in FY26 compressing NIMs by 35+ bps. Retail unsecured stress widens; GNPA breaches 1.5%. LDR normalisation stalls below 95%.

DISSENTING VIEW (1 analyst, Sanjeev): Uncomfortable with the pace of wholesale deposit reliance. Term deposit costs are sticky. The market has not fully priced the structural NIM reset.

RISK FACTORS: Continued repo rate cuts; SEBI distribution commission cap; any macro-driven asset quality deterioration in the SME book.

POSITION SIZING: Given the balance sheet repair overhang, we recommend a 60% position now, adding the remaining 40% when LDR crosses below 95% in print.`,
    debate_summary: `Round 1 — DCF read-through: Base scenario fair value ₹1,920 (13% upside). Three analysts flagged the discount to intrinsic value as the primary entry signal.

Round 2 — Drivers stress-test: NIM compression driver debated. Bull side argued deposit repricing is 70% done; bear side countered that the wholesale deposit proportion (37% of total) creates persistent cost-of-funds pressure.

Round 3 — Falsifier check: CASA ratio at 43.1% (above 42% falsifier threshold) — bull thesis holds. LDR trajectory confirmed on track.

Final vote: 4 BUY, 1 HOLD. Confidence 78%. Key watch: Q4FY25 LDR print and CASA ratio.`,
    citations: [
      'HDFC Bank Q3FY25 Investor Presentation',
      'RBI Monetary Policy Feb 2025',
      'Kotak Institutional Equities Banking Note Mar 2025',
      'HDFC Bank Annual Report FY24',
    ],
  },

  'RELIANCE': {
    ticker: 'RELIANCE',
    vote: 'YES',
    confidence: 72,
    final_report: `Reliance Industries — Investment Verdict: BUY (12-month target ₹1,560)

War room reached a majority BUY at ₹1,320 CMP, implying ~18% upside.

CORE THESIS: Reliance is a three-engine conglomerate with a visible re-rating catalyst in Jio. The July 2024 tariff hike (+12–15%) is still working through the ARPU cycle. Our analysis suggests a second hike in H2CY25 could push Jio ARPU to ₹200+, unlocking an incremental ₹8,000–10,000 cr EBITDA over 18 months. At 12x EV/EBITDA, Jio alone is worth ₹900/share on RIL.

RETAIL RECOVERY: The narrative of "RIL Retail is a value trap" is breaking down. FMCG (Aashirvaad, Sunfeast) and fashion (Ajio, Trends) are delivering improving economics. EBITDA margin expanded 120 bps QoQ in Q3FY25.

O2C DRAG: We model GRM mean-reverting from current $8.1/bbl to $9.5/bbl by H2CY25 — Atlantic Basin refinery closures (Phillips 66 Alliance, LyondellBasell Houston) provide the catalyst. This is NOT in consensus numbers.

NEW ENERGY: Green hydrogen capex (₹75,000 cr) is a call option, not a liability — we assign ₹40/share probability-weighted value. First revenues FY26E.

BEAR CASE (₹1,100): Jio second hike delayed to CY26, retail burn accelerates in quick commerce, GRM stays below $8/bbl.

RISK: Government directed O2C or Jio regulation; USD/INR moves impacting O2C import costs.`,
    debate_summary: `Round 1 — SOTP analysis: Analysts debated Jio's standalone multiple (range: 10–14x EV/EBITDA). Consensus landed at 12x on DCF cross-check.

Round 2 — Jio ARPU sensitivity: Every ₹10 ARPU increase = ₹3,500 cr incremental EBITDA. Second hike probability estimated at 65% by H2CY25.

Round 3 — O2C bear case stress: Even with GRM at $7/bbl, overall SOTP holds above ₹1,350 due to Jio + Retail buffer.

Final vote: 4 BUY, 1 HOLD. Confidence 72%. Key watch: Jio ARPU trajectory and Q4FY25 Retail margin print.`,
    citations: [
      'Jio Platforms Investor Day Dec 2024',
      'RIL Q3FY25 Earnings Presentation',
      'Bernstein India Consumer & TMT Note Feb 2025',
      'Platts GRM Weekly Apr 2025',
    ],
  },

  'ITC': {
    ticker: 'ITC',
    vote: 'YES',
    confidence: 81,
    final_report: `ITC Limited — Investment Verdict: BUY (12-month target ₹520)

Highest conviction call in the war room — 5 of 5 analysts voted BUY at ₹440 CMP, implying 18% upside.

CORE THESIS: ITC is a sum-of-parts story where the parts are clearly visible and the discount is unjustified. Cigarette business generates ₹17,000 cr EBITDA at 72% margin with zero capex requirement. The FMCG inflection has arrived — ₹540 cr EBITDA in FY24 vs zero three years ago. Hotels demerger will surface ₹25–30/share in hidden value.

CIGARETTE FRANCHISE: No excise hike in Union Budget FY25 allows volume growth of 3–4% to compound. Pricing power (3–5% annual price increases) is structural. Illicit market share stable at ~23%, not growing.

FMCG INFLECTION: Aashirvaad atta (36% market share), Classmate (leading notebooks brand), Sunfeast (biscuits #2) are category leaders. Distribution leverage means operating margin is approaching 8% — the threshold that historically triggers FMCG re-rating in India.

HOTELS DEMERGER: ITC Hotels with 120+ properties and ~35% market share in luxury segment is being unlocked as a separate listed entity. Comparable: EIH (Oberoi) trades at 25x EV/EBITDA. ITC Hotels should list at 15–20x, adding ₹25–30/share.

VALUATION: At ₹440, ITC trades at 22x FY26E EPS — a 25% discount to FMCG peers despite superior capital allocation. Conglomerate discount is excessive.

RISK: Budget FY26 surprise excise hike; FMCG competitive response from HUL/Nestle; Hotels demerger timeline slippage.`,
    debate_summary: `Round 1 — Cigarette bear case: Stress-tested 10% excise hike scenario; EBITDA impact ₹1,200 cr but still leaves ITC at 19x FY26E — still cheap.

Round 2 — FMCG re-rating trigger: Analysts aligned on 7% EBITDA margin as the re-rating threshold. Current trajectory reaches 7% by Q2FY26.

Round 3 — Hotels demerger probability: 90% probability assigned to completion within 12 months (board resolution already passed).

Final vote: 5 BUY, 0 others. Confidence 81%. Highest conviction in demo set.`,
    citations: [
      'ITC Q3FY25 Earnings Transcript',
      'ITC Hotels Demerger Board Resolution Nov 2024',
      'IIFL FMCG Sector Report Feb 2025',
      'Axis Capital ITC SOTP Note Jan 2025',
    ],
  },

  'ONGC': {
    ticker: 'ONGC',
    vote: 'NO',
    confidence: 62,
    final_report: `ONGC — Investment Verdict: HOLD/AVOID (12-month target ₹240, limited upside)

War room split 3–2 in favour of HOLD at ₹265 CMP. Not a conviction buy.

CORE CONCERN: ONGC's intrinsic value is deeply intertwined with Brent crude, which the war room sees as range-bound ($75–85) with skew to the downside in H2CY25 as OPEC+ unwinds cuts and Chinese demand remains tepid. At $80 Brent, our DCF yields ₹255 fair value — essentially flat from current levels.

HPCL OVERHANG: The ONGC-HPCL structure is a structural discount driver that management cannot fix. HPCL marketing margins turned negative in H1FY25; ONGC consolidated EPS suffers. Until petrol/diesel pricing is fully deregulated — which has no near-term political catalyst — this drag persists.

BULL CASE (₹310): KG-DWN-98/2 deepwater production ramps to 10 mmscmd ahead of schedule, adding ₹4,000 cr EBITDA. Brent sustains above $85 on Middle East supply shock. HPCL margins recover to ₹3/litre.

BEAR CASE (₹195): Brent drops to $70 on China demand disappointment + OPEC+ unwinding. Subsidy burden reinstated on LPG. KG basin delays push first revenue to FY28.

DISSENTING BULL VIEW (2 analysts): At 5x EV/EBITDA vs EM E&P peers at 6–7x, ONGC is cheap on absolute valuation. PSU dividend yield 4%+ provides downside cushion.

VERDICT: Not a compelling asymmetric bet. Better to watch for Brent direction clarity or KG basin operational update before committing capital.`,
    debate_summary: `Round 1 — Oil price macro: War room modelled three Brent scenarios. Base ($80) yields fair value ~₹255 (HOLD). Bull ($88) yields ₹310 (BUY). Bear ($70) yields ₹195 (SELL).

Round 2 — HPCL drag quantification: Estimated ₹8–12 EPS drag annually from HPCL consolidation at current marketing margins.

Round 3 — KG basin optionality: Assigned 55% probability to hitting 10 mmscmd by FY26. Even at 100% probability, the incremental per-share value is ₹18–22.

Final vote: 2 HOLD, 2 HOLD/AVOID, 1 BUY. Majority HOLD. Confidence 62%.`,
    citations: [
      'Brent Forward Curve Bloomberg Apr 2025',
      'ONGC Q3FY25 Operational Update',
      'Kotak Institutional Equities PSU Oil Note',
      'PPAC India Pricing Bulletin Apr 2025',
    ],
  },

  'TCS': {
    ticker: 'TCS',
    vote: 'YES',
    confidence: 70,
    final_report: `Tata Consultancy Services — Investment Verdict: BUY (12-month target ₹4,200)

War room voted 4–1 BUY at ₹3,590 CMP, implying ~17% upside.

CORE THESIS: TCS is executing the clearest AI services pivot among Indian IT majors. The WisdomNext AI platform is now embedded in 60+ active GenAI engagements, positioning TCS as the default transformation partner for Global 500 enterprises. AI-augmented delivery is structurally compressing headcount-per-dollar of revenue — we model EBIT margins expanding from 24.5% (FY25) to 26%+ by FY27 with flat headcount.

BULL CASE (₹4,600): BFSI vertical (25% of revenue) rebounds fully in H1FY26 as US bank IT budgets reopen. Large deal TCV (LTM $10.4B) accelerates to $12B+ on GenAI implementation wins. EBIT margin prints 25.5%+ in FY26. P/E re-rates from 23x to 28x FY26E.

BEAR CASE (₹3,100): US recession delays discretionary IT spend recovery by 4–6 quarters. GenAI cost pass-through to clients proves harder to realise than modelled. EBIT margins stay anchored at 24% with no upside catalyst.

AI UPSIDE NOT IN CONSENSUS: Sell-side consensus models 12% FY26 revenue growth. We see 50–100 bps upside from GenAI deals currently in "advisory" phase transitioning to multi-year implementation. TCS disclosed 12% code-generation productivity gain across 3 large accounts — not yet fully visible in reported margins but traceable in utilisation trends.

DISSENTING VIEW (1 analyst): BFSI headwinds may be structural, not cyclical. Cautious that the street is extrapolating an AI pipeline that has not yet closed into TCV.

RISK FACTORS: US BFSI capex freeze; INR appreciation compressing USD-reported margins; visa/immigration disruption to onsite delivery; Accenture AI competition intensifying.`,
    debate_summary: `Round 1 — Revenue growth scenarios: Bull/base/bear modelled at 15%/12%/9% for FY26. Current 23x P/E already prices 12% — any surprise to 14–15% drives re-rating.

Round 2 — AI margin thesis: Evidence cited: flat headcount vs 12%+ revenue growth implies structural productivity gain. AI code-review and QA automation reducing effort by 8–15% in pilot accounts. Not yet in reported numbers, but trajectory is unambiguous.

Round 3 — BFSI recovery timing: Consensus says H2FY26; two analysts argued H1FY26 based on JPMorgan and Goldman IT hiring signals. Not enough conviction to call earlier — maintained base case of gradual recovery.

Final vote: 4 BUY, 1 HOLD. Confidence 70%. Key watch: Q1FY26 large deal TCV and BFSI vertical revenue growth rate.`,
    citations: [
      'TCS Q3FY25 Earnings Presentation',
      'TCS WisdomNext AI Platform Briefing Nov 2024',
      'Kotak Institutional Equities IT Services Note Mar 2025',
      'IDC Global IT Services Competitive Tracker 2024',
    ],
  },

  'INFY': {
    ticker: 'INFY',
    vote: 'NO',
    confidence: 55,
    final_report: `Infosys — Investment Verdict: HOLD (12-month target ₹1,720)

War room split 2–2–1 (2 BUY, 2 HOLD, 1 REDUCE) — consensus HOLD at ₹1,580 CMP, implying ~9% upside. Below conviction threshold for a BUY.

CORE THESIS (BULL): Infosys is the discounted play on the IT sector recovery cycle. At 20x FY26E EPS, it trades at a 12–15% discount to TCS — historically this gap closes when quarterly delivery stabilises. Multiple guidance cuts in FY24–25 have compressed expectations, creating a low-bar recovery setup that favours the long side.

MARGIN HEADWIND IS REAL: EBIT margin at 20.3% (Q3FY25) is at the bottom of the management-guided 20–22% band. Unlike TCS, Infosys has not converted AI positioning into measurable delivery leverage. Cobalt + Topaz platforms are architecturally sound but deal conversion from advisory to large-TCV implementation is lagging by 1–2 quarters.

DISCRETIONARY RECOVERY IS UNEVEN: BFSI (32% of revenue) is recovering faster; manufacturing and energy are lagging. Infosys' UK/Europe exposure (31% of revenue) faces delayed recovery as European capex cycles trail North America by ~6 months — a structural timing drag on the recovery thesis.

BULL CASE (₹1,950): Management upgrades FY26 guidance to 8–10%; EBIT margin exits FY26 at 22%+; valuation gap to TCS compresses to 8%. P/E re-rates to 23x.

BEAR CASE (₹1,380): Third consecutive guidance cut; margin stays below 20%; large deal TCV disappoints at Q1FY26. P/E compresses to 17x on eroded credibility.

RISK: Europe macro slowdown; client concentration in Vanguard, BT Group, ABN Amro; GenAI commoditising time-and-material projects, pressuring blended billing rates.`,
    debate_summary: `Round 1 — Valuation gap analysis: At 12–15% discount to TCS on forward P/E, INFY looks mechanically cheap. Bear analyst argued the discount is deserved given three guidance cuts in 18 months — premium only returns when delivery track record is restored.

Round 2 — Margin recovery path: Modelled headcount optimisation (net ~10,000 exits in FY25) contributing 80 bps margin improvement in FY26. Bull case requires utilisation rising from 82% to 84%+ — achievable but contingent on demand materialising.

Round 3 — Discretionary timing debate: Key question: is H2FY25 weakness cyclical (budget freeze) or structural (GenAI substitution)? 2 analysts called cyclical and saw H1FY26 unlock; 2 said structural shift is underway. Split persisted — hence HOLD.

Final vote: 2 BUY, 2 HOLD, 1 REDUCE. Consensus HOLD. Confidence 55%. Key watch: FY26 guidance range at Q4FY25 results and Q1FY26 large deal TCV.`,
    citations: [
      'Infosys Q3FY25 Earnings Call Transcript',
      'Infosys Guidance History FY22–FY25',
      'Morgan Stanley INFY Estimate Revision Note Jan 2025',
      'Gartner IT Spending Forecast 2025',
    ],
  },

  'COALINDIA': {
    ticker: 'COALINDIA',
    vote: 'YES',
    confidence: 65,
    final_report: `Coal India — Investment Verdict: BUY (12-month target ₹500)

War room voted 4–1 BUY at ₹395 CMP, implying ~27% upside.

CORE THESIS: Coal India is the textbook high-yield value compounding story. At 4.5x EV/EBITDA and 6.5% dividend yield, the market is pricing in demand destruction that our analysis shows is at minimum 8–10 years away. India's power demand is compounding at 7% CAGR; thermal capacity accounts for 70% of installed generation; and there is no credible non-coal baseload alternative at grid scale before FY32.

DIVIDEND FLOOR IS STRUCTURAL: CIL distributed ₹31/share in FY25 (including special interim dividend) with cash on balance sheet exceeding ₹35,000 cr. Annual free cash flow of ~₹28,000 cr at stable capex allows payout ratio of 60% to be maintained through FY28 in even a stress scenario. This 6.5% yield is a structural attractor for insurance and pension capital.

VOLUME RAMP = OPERATING LEVERAGE: FY25 production 772 MT vs. 1 billion tonne target by FY27. Each 50 MT incremental production at marginal cost (~₹900/MT) adds ₹2,500–3,000 cr EBITDA at current e-auction realisations. OB removal productivity improved 8% YoY, limiting cost inflation.

E-AUCTION PREMIUM UPSIDE: Non-regulated e-auction volumes (~15% of sales) command 20–25% premium over notified prices. Government import substitution push targeting 100 MT reduction in coal imports. If e-auction share rises to 20% of volumes, EPS upside of ₹8–10/share — not in consensus.

BEAR CASE (₹310): Government mandates price rationalisation, cutting e-auction realisations by 8%. Renewable target acceleration forces early retirement of 4GW+ thermal capacity. Cash redirected to non-core diversification, cutting dividend payout ratio below 50%.

RISK: Regulatory price caps on e-auction; state DISCOM payment delays increasing working capital; ESG-mandate-driven institutional selling compressing P/E multiple.`,
    debate_summary: `Round 1 — Demand destruction timeline: Bull modelled coal power at 55% of installed capacity by FY32 (down from 70% today). Even at 55%, absolute coal volume required still grows 4% CAGR on expanding power demand. Bear analyst argued policy acceleration risk is underpriced — held HOLD.

Round 2 — Dividend sustainability stress test: CIL cash ₹35,000 cr + annual FCF ~₹28,000 cr = comfortable coverage of ₹20,000 cr annual dividend outflow at 60% payout. Even in bear-case earnings (25% EBITDA decline), dividend yield holds above 5%.

Round 3 — Valuation floor discussion: At 4x EV/EBITDA vs PSU peer average 5.5x, CIL offers asymmetric protection. NMDC comparable trades at 4.8x with lower FCF. Multiple re-rating to 5x adds ₹60–70/share.

Final vote: 4 BUY, 1 HOLD. Confidence 65%. Key watch: Q1FY26 e-auction realisation trend and FY26 production guidance update.`,
    citations: [
      'Coal India FY25 Production Bulletin and Dividend Announcement',
      'Central Electricity Authority Demand Forecast FY26',
      'Ministry of Coal Import Substitution Policy Note Feb 2025',
      'Kotak Institutional Equities Coal India SOTP Note Mar 2025',
    ],
  },

  'JPM': {
    ticker: 'JPM',
    vote: 'YES',
    confidence: 76,
    final_report: `JPMorgan Chase — Investment Verdict: BUY (12-month target $280)

War room voted 4–1 BUY at $235 CMP, implying ~19% upside.

CORE THESIS: JPMorgan is the best-in-class US money-centre bank, and the current valuation at 12x FY25E EPS underestimates the earnings power of its CIB franchise in a recovering deal cycle. The investment banking fee recovery is real, not cyclical noise — M&A backlog is at multi-year highs and deregulatory tailwinds (proposed Basel III Endgame dilution) could free $15–20B of capital for buybacks over 24 months.

NII HEADWIND IS PRICED IN: The $90B NII guidance (ex-Markets) for FY25 already embeds 2–3 Fed cuts. At current rates (4.25–4.50%), NII is likely to land above guidance. The market is over-discounting NII risk.

IB RECOVERY: Q4FY24 IB fees +49% YoY is not a blip — ECM calendar is robust, leveraged finance pipeline is full on private equity sponsor activity. Consensus underestimates FY26 IB fees by ~12%.

CREDIT QUALITY: Card NCO at 3.52% is ticking up but management guided stabilisation H1FY25. Prime and super-prime consumer cohorts (72% of card book) remain clean. Subprime stress is isolated and reserved.

CAPITAL RETURN: $12B buyback authorisation; Basel III Endgame dilution likely reduces capital requirement by ~$30B — creating additional buyback capacity.

RISK: Recession scenario (hard landing), credit card NCO acceleration, geopolitical events freezing M&A, Dimon succession uncertainty.`,
    debate_summary: `Round 1 — NII scenario analysis: Modelled 3 Fed cut paths. Even in "4 cuts" scenario, JPM NII $87B still supports ₹21+ EPS. Current P/E of 12x is below historical 13–15x.

Round 2 — IB fee sustainability: Debated whether Q4 was one-off. Consensus: deal backlog and sponsor activity confirm 2–3 quarter runway. Not a one-quarter phenomenon.

Round 3 — Bear case (recession): At 9x trough P/E on $17 EPS = $153 downside. Risk/reward still favourable at $235 entry: ₹45 downside vs $45 upside in base.

Final vote: 4 BUY, 1 HOLD. Confidence 76%.`,
    citations: [
      'JPMorgan Q4FY24 Earnings Call Transcript',
      'Fed FOMC January 2025 Minutes',
      'Bloomberg IB League Tables Q1FY25',
      'JPMorgan 2024 Annual Report',
    ],
  },
};

function run(ticker) {
  const t = (ticker || '').toUpperCase().replace('.NS', '');
  if (VERDICTS[t]) {
    console.log(JSON.stringify(VERDICTS[t]));
  } else {
    const dcf = input.dcf || {};
    const upside = dcf.upside_pct;
    const vote = upside != null ? (upside > 10 ? 'YES' : 'NO') : 'NO';
    console.log(JSON.stringify({
      ticker: t,
      vote,
      confidence: 55,
      final_report: `${t} — Limited Coverage\n\nThis ticker is outside the war room's core coverage universe. A preliminary assessment based on DCF inputs suggests the stock is ${upside != null ? (upside > 10 ? 'potentially undervalued' : 'fairly valued or overvalued') : 'unrated'}. Full driver analysis and debate not available for this name.\n\nRecommendation: Seek additional data before taking a position.`,
      debate_summary: 'Ticker not in primary coverage universe. Abbreviated assessment based on DCF metrics only.',
      citations: ['yfinance price data', 'DCF model output'],
    }));
  }
}

if (!ticker) {
  console.error('Usage: orchestrator.js --ticker TICKER --input <json>');
  process.exit(1);
}

run(ticker);
