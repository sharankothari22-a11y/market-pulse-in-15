import { cn } from "@/lib/utils";

export const DataTable = ({ columns, rows, maxHeight = 320 }) => {
  return (
    <div 
      className="data-table-wrapper overflow-auto"
      style={{ maxHeight: `${maxHeight}px` }}
      data-testid="data-table"
    >
      <table className="w-full text-sm">
        <thead className="sticky top-0 bg-[#111827] z-10">
          <tr>
            {columns.map((col, idx) => (
              <th 
                key={idx}
                className="text-left text-xs text-[#9ca3af] uppercase tracking-wider py-2 px-3 border-b border-[#1f2937]"
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
                "hover:bg-[#1f2937] transition-colors",
                rowIdx % 2 === 0 ? 'bg-[#111827]' : 'bg-[#0d1117]'
              )}
              data-testid={`table-row-${rowIdx}`}
            >
              {columns.map((col, colIdx) => (
                <td 
                  key={colIdx}
                  className={cn(
                    "py-2 px-3 text-[#f9fafb]",
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
