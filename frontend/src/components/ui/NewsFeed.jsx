import { useState, useEffect } from 'react';
import { apiGet, API_ENDPOINTS } from '@/services/api';
import { ExternalLink } from 'lucide-react';

const SOURCE_COLORS = {
  'Economic Times Markets': { bg: '#FEF3C7', fg: '#92400E' },
  'Mint Markets':           { bg: '#DBEAFE', fg: '#1E40AF' },
  'Moneycontrol':           { bg: '#F3E8FF', fg: '#6B21A8' },
};

const defaultColor = { bg: '#F1F5F9', fg: '#475569' };

const formatAge = (published) => {
  if (!published) return '';
  try {
    const d = new Date(published);
    const diffMs = Date.now() - d.getTime();
    const diffMin = Math.floor(diffMs / 60000);
    if (diffMin < 60) return `${diffMin}m ago`;
    const diffHr = Math.floor(diffMin / 60);
    if (diffHr < 24) return `${diffHr}h ago`;
    return d.toLocaleDateString('en-IN', { day: 'numeric', month: 'short' });
  } catch {
    return '';
  }
};

export const NewsFeed = () => {
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    const fetch = async () => {
      try {
        const data = await apiGet(`${API_ENDPOINTS.news}?limit=10`);
        if (!cancelled) setItems(data?.news || []);
      } catch {
        // silent — show empty state
      } finally {
        if (!cancelled) setLoading(false);
      }
    };
    fetch();
    const t = setInterval(fetch, 300000);
    return () => { cancelled = true; clearInterval(t); };
  }, []);

  return (
    <section data-testid="news-feed-section" style={{ marginTop: 24 }}>
      <div style={{
        backgroundColor: 'var(--bi-bg-card)',
        border: '1px solid var(--bi-border-subtle)',
        borderRadius: 12,
        boxShadow: 'var(--bi-shadow-card)',
        padding: 20,
      }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 14 }}>
          <span style={{ fontSize: 13, fontWeight: 600, color: 'var(--bi-text-primary)', letterSpacing: '0.04em' }}>
            Market News
          </span>
          <span style={{ fontSize: 11, color: 'var(--bi-text-tertiary)' }}>
            Sources: ET Markets, Moneycontrol, Mint
          </span>
        </div>

        {loading ? (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
            {[...Array(5)].map((_, i) => (
              <div key={i} style={{ height: 40, backgroundColor: 'var(--bi-bg-subtle)', borderRadius: 6, opacity: 0.6 }} />
            ))}
          </div>
        ) : items.length === 0 ? (
          <p style={{ textAlign: 'center', color: 'var(--bi-text-tertiary)', fontSize: 13, padding: '16px 0' }}>
            News feed updating · Sources: ET Markets, Moneycontrol, Mint
          </p>
        ) : (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 1 }}>
            {items.map((item, idx) => {
              const sc = SOURCE_COLORS[item.source] || defaultColor;
              return (
                <a
                  key={idx}
                  href={item.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  style={{
                    display: 'flex', alignItems: 'center', gap: 10,
                    padding: '9px 6px', borderRadius: 6,
                    textDecoration: 'none',
                    borderBottom: idx < items.length - 1 ? '1px solid var(--bi-border-subtle)' : 'none',
                    transition: 'background 0.15s',
                  }}
                  onMouseEnter={e => e.currentTarget.style.backgroundColor = 'var(--bi-bg-subtle)'}
                  onMouseLeave={e => e.currentTarget.style.backgroundColor = 'transparent'}
                >
                  <span style={{
                    flexShrink: 0, fontSize: 10, fontWeight: 600, padding: '2px 7px',
                    borderRadius: 999, backgroundColor: sc.bg, color: sc.fg,
                    whiteSpace: 'nowrap',
                  }}>
                    {item.source}
                  </span>
                  <span style={{
                    flex: 1, fontSize: 13, color: 'var(--bi-text-primary)',
                    overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap',
                  }}>
                    {item.title}
                  </span>
                  <span style={{ flexShrink: 0, fontSize: 11, color: 'var(--bi-text-tertiary)', minWidth: 40, textAlign: 'right' }}>
                    {formatAge(item.published)}
                  </span>
                  <ExternalLink size={12} style={{ flexShrink: 0, color: 'var(--bi-text-tertiary)' }} />
                </a>
              );
            })}
          </div>
        )}
      </div>
    </section>
  );
};

export default NewsFeed;
