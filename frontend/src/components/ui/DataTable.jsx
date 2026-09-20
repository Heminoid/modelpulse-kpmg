import React from 'react';
import './DataTable.css';

export const DataTable = ({ columns = [], data = [], emptyMessage = 'No data available', compact = false }) => {
  return (
    <div className={`data-table-container ${compact ? 'compact' : ''}`}>
      <table className="data-table">
        <thead>
          <tr>
            {columns.map((col, index) => (
              <th 
                key={col.key || index} 
                style={{ textAlign: col.align || 'left' }}
              >
                {col.label}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {data.length === 0 ? (
            <tr>
              <td colSpan={columns.length} className="data-table-empty">
                {emptyMessage}
              </td>
            </tr>
          ) : (
            data.map((row, rowIndex) => (
              <tr key={row.id || rowIndex}>
                {columns.map((col, colIndex) => (
                  <td 
                    key={`${rowIndex}-${col.key || colIndex}`}
                    style={{ textAlign: col.align || 'left' }}
                  >
                    {col.render ? col.render(row, row[col.key]) : row[col.key]}
                  </td>
                ))}
              </tr>
            ))
          )}
        </tbody>
      </table>
    </div>
  );
};

export default DataTable;
