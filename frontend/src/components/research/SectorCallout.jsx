import { useState, useEffect } from 'react';
import { apiGet } from '@/services/api';

const formatDriver = (d) =>
  d.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase());

export const SectorCallout = ({ sector }) => {
  const [data, setData] = useState(null);

  useEffect(() => {
    if (!sector || sector === 'other') return;
    let cancelled = false;
    apiGet(`/api/research/sector/${encodeURIComponent(sector)}`)
      .then((d) => { if (!cancelled) setData(d); })
      .catch(() => {});
    return () => { cancelled = true; };
  }, [sector]);

  if (!data || !data.display_name) return null;
  const drivers = data.key_drivers || [];

  return (
    <div style={{
      backgroundColor: 'var(--bi-bg-subtle, #F5F7FA)',
      border: '1px solid var(--bi-border-subtle, #E3E8EF)',
      borderRadius: 8,
      padding: '7px 14px',
      marginBottom: 14,
      display: 'flex',
      alignItems: 'center',
      gap: 6,
      flexWrap: 'wrap',
    }}>
      <span style={{ fontSize: 11, color: 'var(--bi-text-tertiary, #8593AB)', flexShrink: 0 }}>
        Analyzed using
      </span>
      <span style={{
        fontSize: 11, fontWeight: 600,
        color: 'var(--bi-navy-700, #1B3A6B)',
        backgroundColor: 'rgba(27,58,107,0.08)',
        padding: '2px 7px', borderRadius: 999,
        flexShrink: 0,
      }}>
        {data.display_name}
      </span>
      <span style={{ fontSize: 11, color: 'var(--bi-text-tertiary, #8593AB)', flexShrink: 0 }}>
        framework
      </span>
      {drivers.length > 0 && (
        <>
          <span style={{ color: 'var(--bi-border-subtle, #D1D9E4)', fontSize: 11 }}>·</span>
          <span style={{ fontSize: 11, color: 'var(--bi-text-tertiary, #8593AB)', flexShrink: 0 }}>
            Key drivers:
          </span>
          <span style={{ fontSize: 11, color: 'var(--bi-text-secondary, #4B5A75)' }}>
            {drivers.map(formatDriver).join(' · ')}
          </span>
        </>
      )}
      <span style={{ fontSize: 11, color: 'var(--bi-text-tertiary, #8593AB)', marginLeft: 'auto', flexShrink: 0 }}>
        {data.valuation_focus}
      </span>
    </div>
  );
};

export default SectorCallout;
