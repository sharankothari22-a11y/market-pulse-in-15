#!/usr/bin/env node
/**
 * Beaver Agent — stub for demo
 * Returns key value drivers per ticker, hardcoded for 5 demo tickers.
 */

const args = process.argv.slice(2);
const tickerIdx = args.indexOf('--ticker');
const ticker = tickerIdx !== -1 ? args[tickerIdx + 1] : null;

const DRIVERS = {
  'HDFCBANK': {
    ticker: 'HDFCBANK',
    drivers: [
      {
        name: 'Net Interest Margin compression',
        chain: 'RBI rate cuts → deposit repricing lag → NIM squeeze of ~20–30 bps in H1FY26; offset partially by CASA franchise (43% CASA ratio)',
        falsifier: 'If CASA ratio holds above 42% through FY26, NIM compression will be contained below 15 bps',
        citation: 'HDFC Bank Q3FY25 Investor Presentation, RBI Monetary Policy Feb 2025',
        exposure_intensity: 0.82,
        confidence: 0.78,
      },
      {
        name: 'Merger-driven loan-to-deposit ratio normalisation',
        chain: 'Post HDFC Ltd merger, LDR spiked to 110%; management guiding 90% by FY26 via retail deposit mobilisation',
        falsifier: 'Quarterly deposit growth falling below 3% QoQ would signal normalisation is stalling',
        citation: 'HDFC Bank Q3FY25 Earnings Call Transcript',
        exposure_intensity: 0.75,
        confidence: 0.82,
      },
      {
        name: 'Retail credit quality under stress',
        chain: 'Unsecured personal loan & credit card GNPA ticking up industry-wide; HDFC Bank exposure ~12% of book',
        falsifier: 'PCR holding above 74% and GNPA below 1.4% through FY26 confirms stress is priced in',
        citation: 'RBI Financial Stability Report Dec 2024, HDFC Bank Annual Report FY24',
        exposure_intensity: 0.60,
        confidence: 0.71,
      },
      {
        name: 'Fee income diversification (third-party distribution)',
        chain: 'Insurance + mutual fund distribution fees growing 18% YoY; provides NIR buffer vs NII headwinds',
        falsifier: 'SEBI fee-cap regulation on distribution commissions would directly impair this thesis',
        citation: 'HDFC Bank Fee Income Breakdown, Q3FY25',
        exposure_intensity: 0.55,
        confidence: 0.85,
      },
    ],
  },
  'RELIANCE': {
    ticker: 'RELIANCE',
    drivers: [
      {
        name: 'Jio 5G ARPU expansion',
        chain: 'Jio 5G coverage at 97% of urban India; tariff hike July 2024 boosted ARPU to ₹181; next hike cycle expected H2CY25 targeting ₹200+',
        falsifier: 'If subscriber churn exceeds 2% QoQ post-hike, pricing power thesis breaks',
        citation: 'Jio Platforms Investor Day Dec 2024, TRAI Telecom Subscriber Report',
        exposure_intensity: 0.88,
        confidence: 0.84,
      },
      {
        name: 'Retail segment EBITDA margin recovery',
        chain: 'JioMart losses narrowing; fashion & lifestyle (Trends, Ajio) hitting positive EBITDA; overall retail margins guided to 8–9% by FY26 vs 6.8% in FY24',
        falsifier: 'Quick commerce burn rates (JioMart vs Blinkit/Zepto) could delay margin inflection by 2–3 quarters',
        citation: 'Reliance Retail Q3FY25 Earnings, Bernstein Retail Sector Note Jan 2025',
        exposure_intensity: 0.72,
        confidence: 0.76,
      },
      {
        name: 'O2C refining margins mean reversion',
        chain: 'GRM declined from $10.3/bbl (FY23 peak) to $8.1/bbl currently; Saudi OSP cuts + Chinese demand tepid; recovery tied to Atlantic Basin refinery outages',
        falsifier: 'Singapore complex GRM sustained above $9/bbl for 2 consecutive quarters would confirm recovery',
        citation: 'Platts Energy, Reliance O2C Segment Report Q3FY25',
        exposure_intensity: 0.65,
        confidence: 0.67,
      },
      {
        name: 'New Energy (green hydrogen + solar) capex optionality',
        chain: 'Dhirubhai Ambani Green Energy Giga Complex: ₹75,000 cr committed; electrolyser + solar panel manufacturing; first revenues FY26E',
        falsifier: 'Delay beyond FY27 in green hydrogen offtake agreements would shift this from asset to liability',
        citation: 'RIL AGM 2023, MNRE Green Hydrogen Policy Framework',
        exposure_intensity: 0.50,
        confidence: 0.58,
      },
    ],
  },
  'TCS': {
    ticker: 'TCS',
    drivers: [
      {
        name: 'AI services pivot and GenAI deal conversion',
        chain: 'WisdomNext platform embedded in 60+ active GenAI engagements; advisory pipeline converting to implementation; TCS disclosed 12% code-generation productivity gain across 3 large accounts; first dedicated AI revenue line items expected FY26',
        falsifier: 'If Q1FY26 large deal TCV falls below $2.5B or GenAI conversions remain stuck in advisory phase for a second consecutive quarter, the AI growth premium unwinds',
        citation: 'TCS Q3FY25 Earnings Call, TCS WisdomNext Platform Briefing Nov 2024',
        exposure_intensity: 0.88,
        confidence: 0.82,
      },
      {
        name: 'EBIT margin expansion via AI-augmented delivery',
        chain: 'Headcount flat YoY while revenue grows 12%+ — implicit productivity gain ~12%; FY25 EBIT at 24.5%; target 26%+ by FY27 via reduced fresher intake and AI code-review and QA workflows replacing manual effort',
        falsifier: 'Utilisation falling below 85% for two consecutive quarters signals demand slowdown, invalidating the margin expansion path; fresher hiring resumption would also reset the cost trajectory',
        citation: 'TCS FY25 Annual Report, Kotak Institutional Equities IT Services Note Mar 2025',
        exposure_intensity: 0.80,
        confidence: 0.78,
      },
      {
        name: 'North America BFSI vertical revenue recovery',
        chain: 'BFSI is 25% of TCS revenue; spend froze FY24–25 on rate uncertainty; JPMorgan, Goldman, Citigroup all signalling 2025 tech budget increases; TCS BFSI revenue growth expected to inflect from low single digits to 8–10% by H1FY26',
        falsifier: 'BFSI revenue growth below 5% YoY in Q1FY26 confirms recovery is delayed into FY27, removing the near-term re-rating catalyst',
        citation: 'TCS Vertical Revenue Mix Q3FY25, JPMorgan 2025 IT Budget Survey',
        exposure_intensity: 0.75,
        confidence: 0.72,
      },
      {
        name: 'Large deal TCV momentum and market share gains',
        chain: 'LTM large deal wins $10.4B (Q3FY25); pipeline skewed to cloud migration + AI transformation bundles; TCS market share in mega-deals (>$500M TCV) expanding vs Accenture and Cognizant',
        falsifier: 'Two consecutive quarters of TCV below $2B would signal pipeline weakness and put double-digit revenue growth guidance at risk',
        citation: 'TCS Q3FY25 Earnings Presentation, IDC Global IT Services Competitive Tracker 2024',
        exposure_intensity: 0.68,
        confidence: 0.76,
      },
    ],
  },
  'INFY': {
    ticker: 'INFY',
    drivers: [
      {
        name: 'Discretionary IT spend recovery across verticals',
        chain: 'BFSI (32% of rev) showing early budget unlocks in H2FY25; manufacturing and energy verticals lagging by ~2 quarters; discretionary mix ~40% of total revenue — the key recovery lever that consensus is undermodelling',
        falsifier: 'If BFSI vertical revenue growth fails to hit 7% YoY by Q2FY26, recovery is stalling and INFY HOLD thesis becomes a REDUCE at current valuation',
        citation: 'Infosys Q3FY25 Vertical Revenue Breakdown, Gartner IT Spending Forecast 2025',
        exposure_intensity: 0.84,
        confidence: 0.62,
      },
      {
        name: 'EBIT margin compression and recovery path',
        chain: 'FY25 EBIT margin 20.3% — bottom of the 20–22% guided band; drag from attrition absorption costs, return-to-office overhead, and underutilisation in project ramp-ups; net ~10,000 headcount exits in FY25 partially restoring cost efficiency',
        falsifier: 'If EBIT margin fails to cross 21% by Q2FY26, it signals structural (not cyclical) degradation — justifying a valuation de-rate to 17x from current 20x',
        citation: 'Infosys Q3FY25 Earnings Call, IIFL IT Sector Margin Analysis Feb 2025',
        exposure_intensity: 0.78,
        confidence: 0.65,
      },
      {
        name: 'Guidance credibility and management execution risk',
        chain: 'Three guidance reductions in FY24–25 damaged confidence; FY25 final guidance 4.5–5% cc growth vs initial 6–8%; historical P/E premium to peers justified by flawless execution — that premium has partially eroded and must be re-earned',
        falsifier: 'Delivering at the upper end of FY26 guidance for two consecutive quarters would restore credibility and justify P/E compression to TCS gap narrowing below 10%',
        citation: 'Infosys Guidance History FY22–FY25, Morgan Stanley INFY Estimate Revision Note Jan 2025',
        exposure_intensity: 0.65,
        confidence: 0.58,
      },
    ],
  },
  'COALINDIA': {
    ticker: 'COALINDIA',
    drivers: [
      {
        name: 'India power demand and structural coal offtake',
        chain: 'India power demand CAGR 7% (FY25–FY30); thermal capacity 70% of installed base; no credible non-coal baseload alternative at scale before FY32; Electricity Act 2023 mandates supply obligations, not fuel-mix targets',
        falsifier: 'Government mandating coal-to-gas fuel switching for >5GW of thermal capacity before FY28, or renewable storage cost falling below ₹3/kWh, would require material downgrade of CIL volume outlook',
        citation: 'Central Electricity Authority Demand Forecast FY26, PPAC India Energy Statistics Apr 2025',
        exposure_intensity: 0.90,
        confidence: 0.80,
      },
      {
        name: 'E-auction realisation premium and import substitution',
        chain: 'E-auction volumes ~15% of total CIL sales at 20–25% premium over notified price; government targeting 100 MT reduction in coal imports; each 1% shift in e-auction mix contributes ~₹500 cr EBITDA; EPS upside of ₹8–10 if mix reaches 20%',
        falsifier: 'Government imposing regulated price caps on e-auction or mandating price parity with notified coal would eliminate the realisation premium and reduce FY26E EPS by ~₹6',
        citation: 'Coal India E-Auction Results Q3FY25, Ministry of Coal Import Policy Note Feb 2025',
        exposure_intensity: 0.75,
        confidence: 0.72,
      },
      {
        name: 'Dividend yield and FCF generation',
        chain: 'FY25 total dividend ₹31/share (including special interim); balance sheet cash ₹35,000 cr; annual FCF ~₹28,000 cr on stable capex; 6.5% yield at CMP attracts insurance and pension mandates that are structurally long the name',
        falsifier: 'Cash redirection to non-core diversification (e.g., power generation JVs, renewable mining) at the cost of payout ratio falling below 50% would erode the yield cushion that underpins valuation floor',
        citation: 'Coal India FY25 Dividend Announcement, BSE CIL Dividend History',
        exposure_intensity: 0.70,
        confidence: 0.82,
      },
      {
        name: 'Production volume ramp and operating leverage',
        chain: 'FY25 production 772 MT vs 1 billion tonne target by FY27; each 50 MT incremental volume at marginal cost (~₹900/MT) adds ₹2,500–3,000 cr EBITDA at current e-auction realisations; OB removal productivity up 8% YoY limiting cost inflation',
        falsifier: 'Monsoon disruptions, mining block cancellations, or environmental clearance delays causing FY26 production to miss 830 MT guidance would reset consensus EPS estimates by 6–8%',
        citation: 'Coal India FY25 Production Bulletin, Ministry of Coal Annual Report 2024–25',
        exposure_intensity: 0.65,
        confidence: 0.75,
      },
    ],
  },
  'ITC': {
    ticker: 'ITC',
    drivers: [
      {
        name: 'Cigarette volume recovery post-GST stability',
        chain: 'Cigarette EBIT margin at 72%; volume growth 3–4% YoY post 3 years of flat volumes; sin tax overhang manageable with no Union Budget hike in FY25',
        falsifier: 'Any excise duty hike >10% in Union Budget FY26 would compress volumes by estimated 4–6%',
        citation: 'ITC Annual Report FY24, Union Budget FY25 Excise Schedule',
        exposure_intensity: 0.85,
        confidence: 0.80,
      },
      {
        name: 'FMCG segment reaching profitability inflection',
        chain: 'FMCG (non-cigarette) EBIT turned positive at ₹540 cr in FY24 vs losses 5 years ago; Aashirvaad, Classmate, Sunfeast scaling; 15% revenue CAGR guided',
        falsifier: 'If FMCG EBIT margin fails to cross 7% by FY26, the sum-of-parts re-rating thesis collapses',
        citation: 'ITC Q3FY25 Earnings, IIFL FMCG Sector Report Feb 2025',
        exposure_intensity: 0.68,
        confidence: 0.77,
      },
      {
        name: 'Hotels demerger value unlock',
        chain: 'ITC Hotels demerger approved; standalone hotel business with 120+ properties to list separately; unlocks ₹25–30/share on ITC standalone basis',
        falsifier: 'Hotel listing premium below 15x EV/EBITDA would signal market not ascribing full value',
        citation: 'ITC Hotels Demerger Board Resolution Nov 2024, Axis Capital SOTP Note',
        exposure_intensity: 0.60,
        confidence: 0.83,
      },
    ],
  },
  'ONGC': {
    ticker: 'ONGC',
    drivers: [
      {
        name: 'Brent crude price sensitivity',
        chain: 'Every $1/bbl move in Brent changes ONGC EBITDA by ~₹800 cr; current Brent at $82; H2CY25 consensus $78–85 range; subsidy burden from LPG under-recoveries has been nil since FY24',
        falsifier: 'Brent falling below $70 for >60 days would trigger subsidy reinstatement risk and materially impair EPS',
        citation: 'Brent Forward Curve, PPAC India Pricing Bulletin Apr 2025',
        exposure_intensity: 0.90,
        confidence: 0.75,
      },
      {
        name: 'KG-DWN-98/2 deepwater gas ramp-up',
        chain: 'Cluster-2 production targeting 10 mmscmd by FY26; incremental EBITDA of ₹4,000+ cr; capex risk from deepwater infill complexity',
        falsifier: 'If plateau production misses 8 mmscmd threshold by Q2FY26, capex return thesis is impaired',
        citation: 'ONGC Operational Update Q3FY25, Kotak Institutional Equities Gas Note',
        exposure_intensity: 0.70,
        confidence: 0.65,
      },
      {
        name: 'HPCL subsidiary drag on consolidated P&L',
        chain: 'ONGC holds 54.9% in HPCL; HPCL marketing margins volatile (turned negative H1FY25); consolidation of HPCL losses overhang on ONGC stock',
        falsifier: 'Full deregulation of petrol/diesel prices OR HPCL marketing margin >₹3/litre for 2 quarters would remove overhang',
        citation: 'HPCL Q3FY25 Results, Motilal Oswal PSU Oil Note Jan 2025',
        exposure_intensity: 0.65,
        confidence: 0.72,
      },
    ],
  },
  'JPM': {
    ticker: 'JPM',
    drivers: [
      {
        name: 'Net Interest Income under Fed rate cut cycle',
        chain: 'JPM guided NII (ex-Markets) of $90B for FY25; Fed cut 100 bps in 2024; deposit beta 45% means NII headwind of ~$3–4B if cuts continue; CIB fixed income trading partially offsets',
        falsifier: 'If Fed pauses and 10Y Treasury stays above 4.2%, NII guidance holds; breach of 3.8% would force guidance cut',
        citation: 'JPMorgan Q4FY24 Earnings Call, Fed FOMC Jan 2025 Minutes',
        exposure_intensity: 0.80,
        confidence: 0.78,
      },
      {
        name: 'Investment banking fee cycle recovery',
        chain: 'IB fees +49% YoY in Q4FY24; M&A advisory backlog at multi-year high; deregulatory tailwind under current administration supports deal activity',
        falsifier: 'Credit spread widening above 400 bps (HY index) or equity vol (VIX >30 for >30 days) would freeze M&A pipeline',
        citation: 'JPM Q4FY24 Supplement, Bloomberg IB League Tables Q1FY25',
        exposure_intensity: 0.72,
        confidence: 0.82,
      },
      {
        name: 'Credit card net charge-off normalisation',
        chain: 'Card NCO rate at 3.52% (Q4FY24), up from trough; management guided stabilisation in H1FY25; subprime cohort stress concentrated in post-COVID vintages',
        falsifier: 'NCO rate exceeding 3.8% for two consecutive quarters signals consumer health worse than modelled',
        citation: 'JPM Consumer Banking Supplement Q4FY24, Fitch US Consumer Credit Monitor',
        exposure_intensity: 0.62,
        confidence: 0.74,
      },
    ],
  },
};

function output(ticker) {
  const t = (ticker || '').toUpperCase().replace('.NS', '');
  if (DRIVERS[t]) {
    console.log(JSON.stringify(DRIVERS[t]));
  } else {
    console.log(JSON.stringify({
      ticker: t,
      drivers: [],
      meta: { coverage: 'thin', note: 'Ticker not in demo corpus — limited driver data available' },
    }));
  }
}

if (!ticker) {
  console.error('Usage: model.js --ticker TICKER --metric drivers [--premium]');
  process.exit(1);
}

output(ticker);
