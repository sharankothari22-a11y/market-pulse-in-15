import { cn } from "@/lib/utils";

export const DataTable = ({ columns, rows, maxHeight = 320 }) => {
  return (
    <div 
      className="data-table-wrapper overflow-auto"
      style={{ maxHeight: `${maxHeight}px` }}
      data-testid="data-table"
    >
      <table className="w-full text-sm">
        <thead className="sticky top-0 bg-[#f8fafc] z-10">
          <tr>
            {columns.map((col, idx) => (
              <th 
                key={idx}
                className="text-left text-xs text-[#64748b] uppercase tracking-wider py-2 px-3 border-b border-[#e5e7eb]"
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
              className={cn(
                "hover:bg-[#f1f5f9] transition-colors",
                rowIdx % 2 === 0 ? 'bg-[#f8fafc]' : 'bg-[#f1f5f9]'
              )}
              data-testid={`table-row-${rowIdx}`}
            >
              {columns.map((col, colIdx) => (
                <td 
                  key={colIdx}
                  className={cn(
                    "py-2 px-3 text-[#0f172a]",
                    col.className
                  )}
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
