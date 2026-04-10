// Mock Data for Indian Financial Markets Dashboard

export const marketIndices = [
  { id: 'nifty', title: 'NIFTY 50', value: '24,567.85', change: '+1.24%', changeType: 'positive', subtitle: '↑ 301.25 pts' },
  { id: 'sensex', title: 'SENSEX', value: '81,234.67', change: '+1.18%', changeType: 'positive', subtitle: '↑ 948.32 pts' },
  { id: 'banknifty', title: 'BANK NIFTY', value: '52,890.40', change: '-0.45%', changeType: 'negative', subtitle: '↓ 238.15 pts' },
  { id: 'usdinr', title: 'USD/INR', value: '83.42', change: '+0.12%', changeType: 'positive', subtitle: '₹ +0.10' },
  { id: 'vix', title: 'INDIA VIX', value: '13.85', change: '-2.34%', changeType: 'positive', subtitle: 'Low volatility' },
];

export const topMovers = [
  { symbol: 'RELIANCE', ltp: '2,945.60', change: '+3.24%', changeType: 'positive', volume: '12.4M' },
  { symbol: 'TCS', ltp: '4,128.75', change: '+2.15%', changeType: 'positive', volume: '5.8M' },
  { symbol: 'HDFCBANK', ltp: '1,678.90', change: '+1.89%', changeType: 'positive', volume: '8.2M' },
  { symbol: 'INFY', ltp: '1,856.40', change: '-1.12%', changeType: 'negative', volume: '6.5M' },
  { symbol: 'ICICIBANK', ltp: '1,234.55', change: '+1.45%', changeType: 'positive', volume: '9.1M' },
  { symbol: 'IRFC', ltp: '187.65', change: '+4.82%', changeType: 'positive', volume: '45.2M' },
  { symbol: 'WIPRO', ltp: '478.30', change: '-0.78%', changeType: 'negative', volume: '4.3M' },
  { symbol: 'AXISBANK', ltp: '1,156.80', change: '+2.01%', changeType: 'positive', volume: '7.6M' },
  { symbol: 'BAJFINANCE', ltp: '7,234.15', change: '-1.56%', changeType: 'negative', volume: '2.1M' },
];

export const commodities = [
  { id: 'gold', title: 'GOLD', value: '₹71,234', change: '+0.45%', changeType: 'positive', subtitle: 'MCX Spot' },
  { id: 'crude', title: 'CRUDE OIL', value: '$78.45', change: '-1.23%', changeType: 'negative', subtitle: 'Brent' },
  { id: 'bitcoin', title: 'BITCOIN', value: '$97,845', change: '+2.87%', changeType: 'positive', subtitle: 'BTC/USD' },
  { id: 'silver', title: 'SILVER', value: '₹84,560', change: '+0.34%', changeType: 'positive', subtitle: 'MCX Spot' },
];

export const fiiDiiData = {
  summary: { fii: '-₹2,345 Cr', dii: '+₹1,890 Cr', net: '-₹455 Cr' },
  weekly: [
    { day: 'Mon', fii: -1200, dii: 800 },
    { day: 'Tue', fii: -800, dii: 1200 },
    { day: 'Wed', fii: 500, dii: 600 },
    { day: 'Thu', fii: -1500, dii: 900 },
    { day: 'Fri', fii: -2345, dii: 1890 },
  ],
};

export const newsSignals = [
  { id: 1, title: 'SEBI tightens F&O regulations for retail investors', timestamp: '10:45 AM', severity: 'warning', sector: 'Regulatory', signalType: 'Policy' },
  { id: 2, title: 'RBI maintains repo rate at 6.5%, signals cautious stance', timestamp: '09:30 AM', severity: 'info', sector: 'Banking', signalType: 'Monetary' },
  { id: 3, title: 'TCS Q4 results beat estimates, declares ₹28 dividend', timestamp: '08:15 AM', severity: 'positive', sector: 'IT', signalType: 'Earnings' },
  { id: 4, title: 'Reliance announces $10B green energy investment', timestamp: 'Yesterday', severity: 'positive', sector: 'Energy', signalType: 'Corporate' },
  { id: 5, title: 'IRFC secures ₹5,000 Cr funding for rail infrastructure', timestamp: 'Yesterday', severity: 'positive', sector: 'Infrastructure', signalType: 'Corporate' },
  { id: 6, title: 'Crude oil surges on OPEC+ production cut extension', timestamp: '2 days ago', severity: 'danger', sector: 'Commodity', signalType: 'Global' },
];

export const signalsAlerts = [
  { id: 1, title: 'Crude oil breaks $80 resistance - Petroleum stocks under pressure', timestamp: '11:20 AM', severity: 'danger', sector: 'Petroleum', signalType: 'Technical', transmission: 'Higher input costs impacting OMCs margin guidance' },
  { id: 2, title: 'RBI liquidity measures boost banking sentiment', timestamp: '10:45 AM', severity: 'positive', sector: 'Banking', signalType: 'Policy', transmission: 'Improved NIM expectations for PSU banks' },
  { id: 3, title: 'FDA approval for Sun Pharma generic drug', timestamp: '09:30 AM', severity: 'positive', sector: 'Pharma', signalType: 'Regulatory', transmission: 'Revenue visibility improved for FY26' },
  { id: 4, title: 'Tata Motors JLR deal closes at premium valuation', timestamp: '08:15 AM', severity: 'info', sector: 'Auto', signalType: 'M&A', transmission: 'EV strategy gains momentum' },
  { id: 5, title: 'FMCG volume growth slows in rural India', timestamp: 'Yesterday', severity: 'warning', sector: 'FMCG', signalType: 'Demand', transmission: 'Margin pressure expected Q4' },
  { id: 6, title: 'IT sector faces headwinds from US banking crisis', timestamp: 'Yesterday', severity: 'danger', sector: 'IT', signalType: 'Global', transmission: 'Deal pipeline slowdown anticipated' },
  { id: 7, title: 'Infosys wins $1.5B deal with European bank', timestamp: '2 days ago', severity: 'positive', sector: 'IT', signalType: 'Deal Win', transmission: 'FY26 guidance upgrade likely' },
  { id: 8, title: 'IRFC bond issuance oversubscribed 3x', timestamp: '2 days ago', severity: 'positive', sector: 'Infrastructure', signalType: 'Funding', transmission: 'Strong investor confidence in rail capex' },
];

export const activeAlerts = [
  { id: 1, condition: 'NIFTY crosses 24,800', status: 'active', type: 'Price Alert' },
  { id: 2, condition: 'RELIANCE volume > 15M', status: 'active', type: 'Volume Alert' },
  { id: 3, condition: 'VIX > 18', status: 'triggered', type: 'Volatility Alert' },
];

export const researchData = {
  ticker: 'RELIANCE',
  sector: 'Oil & Gas / Retail / Telecom',
  sessionId: 'RS-2024-0892',
  status: 'Active Analysis',
  hypothesis: 'Reliance is undervalued relative to sum-of-parts valuation. Jio and Retail segments trading at significant discount to peers. O2C business provides stable cash flow base.',
  variantView: 'Market underestimates synergies between Retail and Jio platforms. New Energy investments could unlock $50B+ value by 2030.',
  catalysts: [
    { event: 'Jio IPO announcement', timeline: 'H2 FY25', impact: 'High' },
    { event: 'Retail EBITDA margin expansion', timeline: 'Q4 FY25', impact: 'Medium' },
  ],
  scenarios: [
    { label: 'Bull', price: '₹3,450', upside: '+17.2%' },
    { label: 'Base', price: '₹3,050', upside: '+3.5%' },
    { label: 'Bear', price: '₹2,650', upside: '-10.0%' },
  ],
  reverseDCF: 'Current price implies 8% terminal growth. Market consensus at 6%. Suggests 15-20% mispricing.',
  assumptionChanges: [
    { assumption: 'Jio ARPU', old: '₹178', new: '₹195', impact: '+₹180 per share' },
    { assumption: 'Retail margin', old: '7.5%', new: '8.2%', impact: '+₹85 per share' },
    { assumption: 'O2C GRM', old: '$8/bbl', new: '$9.5/bbl', impact: '+₹45 per share' },
    { assumption: 'New Energy capex', old: '₹50,000 Cr', new: '₹75,000 Cr', impact: '-₹120 per share' },
    { assumption: 'WACC', old: '10.5%', new: '10.0%', impact: '+₹210 per share' },
  ],
};

export const macroData = {
  indicators: [
    { id: 'gdp', title: 'GDP Growth', value: '7.2%', change: '+0.3%', changeType: 'positive', subtitle: 'Q3 FY25 YoY' },
    { id: 'cpi', title: 'CPI Inflation', value: '4.8%', change: '-0.2%', changeType: 'positive', subtitle: 'Jan 2025' },
    { id: 'repo', title: 'Repo Rate', value: '6.50%', change: '0.00%', changeType: 'neutral', subtitle: 'RBI Policy' },
    { id: 'fed', title: 'Fed Funds', value: '4.50%', change: '-0.25%', changeType: 'positive', subtitle: 'US Federal Reserve' },
  ],
  globalEvents: [
    { id: 1, event: 'US Fed signals rate cut pause amid sticky inflation', impact: 'Negative', region: 'Global' },
    { id: 2, event: 'China stimulus measures boost commodity demand', impact: 'Positive', region: 'Asia' },
    { id: 3, event: 'ECB maintains dovish stance, Euro weakens', impact: 'Mixed', region: 'Europe' },
    { id: 4, event: 'Japan exits negative rates, Yen strengthens', impact: 'Mixed', region: 'Asia' },
    { id: 5, event: 'Middle East tensions elevate oil risk premium', impact: 'Negative', region: 'Global' },
  ],
  macroMicro: [
    { macro: 'Crude Oil Price', trigger: '> $85/bbl', sector: 'Petroleum', impact: 'OMC margins compress 15-20%' },
    { macro: 'Repo Rate Cut', trigger: '-25bps', sector: 'Banking', impact: 'NIM pressure, credit growth +' },
    { macro: 'CPI > 6%', trigger: 'Sustained', sector: 'FMCG', impact: 'Volume growth slowdown' },
    { macro: 'DXY Strength', trigger: '> 105', sector: 'IT', impact: 'Revenue tailwind, margin +' },
  ],
};

export const chatMessages = [
  { id: 1, type: 'user', text: 'Why did Nifty fall today?' },
  { id: 2, type: 'ai', text: 'Nifty declined 1.2% due to FII selling of ₹2,345 Cr and crude oil surge above $80. Banking stocks led the fall on NIM concerns.' },
  { id: 3, type: 'user', text: 'What are the signals for RELIANCE?' },
  { id: 4, type: 'ai', text: '1. Strong buy signal on daily RSI crossover\n2. Resistance at ₹3,000, support ₹2,850\n3. Positive on Jio IPO speculation' },
];

export const mockAIResponses = {
  default: 'I can help you analyze Indian market trends, stock signals, and macro indicators. What would you like to know?',
  nifty: 'NIFTY is showing bullish momentum with support at 24,200. Key resistance at 24,800. FII flows remain a concern.',
  reliance: 'RELIANCE trading near ₹2,945. Sum-of-parts suggests 15% upside. Watch for Jio IPO timeline clarity.',
  banking: 'Banking sector facing NIM pressure from rate cut expectations. PSU banks preferred over private for value play.',
  it: 'IT sector headwinds from US slowdown. Infosys and TCS showing resilience. Mid-caps attractive at current valuations.',
  macro: 'India GDP at 7.2% leads major economies. Inflation cooling supports RBI rate cut in H1 2025.',
  irfc: 'IRFC showing strong momentum with 45M+ volume. Railway capex theme intact. ₹200 target in near term.',
};
