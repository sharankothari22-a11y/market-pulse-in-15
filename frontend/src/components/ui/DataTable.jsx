import { cn } from '@/lib/utils';

export const DataTable = ({ columns, rows, maxHeight = 320 }) => {
  return (
    <div
      className="data-table-wrapper overflow-auto"
      style={{ maxHeight: `${maxHeight}px` }}
      data-testid="data-table"
    >
      <table className="w-full text-sm tabular-nums">
        <thead
          className="sticky top-0 z-10"
          style={{
            backgroundColor: '#0D3B2E',
          }}
        >
          <tr>
            {columns.map((col, idx) => (
              <th
                key={idx}
                className="text-left py-2.5 px-3"
                style={{
                  color: '#C9A84C',
                  fontSize: 10,
                  letterSpacing: '0.22em',
                  fontWeight: 600,
                  textTransform: 'uppercase',
                  borderBottom: '1px solid rgba(201, 168, 76, 0.3)',
                }}
              >
                {col.header}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row, rowIdx) => (
            <tr
              key={rowIdx}
              className="row-hover transition-colors"
              style={{
                borderBottom: '1px solid rgba(201, 168, 76, 0.08)',
              }}
              data-testid={`table-row-${rowIdx}`}
            >
              {columns.map((col, colIdx) => (
                <td
                  key={colIdx}
                  className={cn('py-2.5 px-3', col.className)}
                  style={{
                    color: '#F5F0E8',
                    fontSize: 12.5,
                  }}
                >
                  {col.render ? col.render(row) : row[col.accessor]}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
};
