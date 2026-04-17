// API Configuration
export const API_BASE_URL = process.env.REACT_APP_BACKEND_URL || '';

// API Endpoints
export const API_ENDPOINTS = {
  // Health
  health: '/api/health',

  // Market
  marketOverview: '/api/market/overview',
  prices: (ticker) => `/api/prices/${ticker}`,

  // Macro
  macro: '/api/macro',

  // Signals & Alerts
  signals: '/api/signals',
  alerts: '/api/alerts',

  // Research
  researchNew: '/api/research/analyze',
  research: (sessionId) => `/api/research/${sessionId}`,
  researchReport: (sessionId) => `/api/research/${sessionId}/report`,
  researchSignals: (sessionId) => `/api/research/${sessionId}/signals`,
  researchScenarios: (sessionId) => `/api/research/${sessionId}/run-scenarios`,
  researchAssumption: (sessionId) => `/api/research/${sessionId}/assumption`,
  researchCatalyst: (sessionId) => `/api/research/${sessionId}/catalyst`,
  researchThesis: (sessionId) => `/api/research/${sessionId}/thesis`,
  sessions: '/api/sessions',

  // Chat
  chat: '/api/chat',

  // Reports
  reportMarket: '/api/reports/market',
  reportCommodity: '/api/reports/commodity',
  reportMacro: '/api/reports/macro',
  reportInvestor: '/api/reports/investor',
};

// API Helper Functions
export const apiRequest = async (endpoint, options = {}) => {
  const url = `${API_BASE_URL}${endpoint}`;

  const defaultOptions = {
    headers: {
      'Content-Type': 'application/json',
    },
  };

  const mergedOptions = {
    ...defaultOptions,
    ...options,
    headers: {
      ...defaultOptions.headers,
      ...options.headers,
    },
  };

  try {
    const response = await fetch(url, mergedOptions);

    if (!response.ok) {
      throw new Error(`API Error: ${response.status} ${response.statusText}`);
    }

    return await response.json();
  } catch (error) {
    console.error(`API Request Failed: ${endpoint}`, error);
    throw error;
  }
};

// GET request helper
export const apiGet = (endpoint) => apiRequest(endpoint, { method: 'GET' });

// POST request helper
export const apiPost = (endpoint, data) => apiRequest(endpoint, {
  method: 'POST',
  body: JSON.stringify(data),
});