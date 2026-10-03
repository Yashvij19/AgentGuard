import React, { useState, useMemo } from 'react';
import { FileCode, Columns, AlignJustify } from 'lucide-react';
import clsx from 'clsx';

interface DiffLine {
  type: 'add' | 'delete' | 'context';
  oldLine?: number;
  newLine?: number;
  content: string;
}

interface DiffViewerProps {
  filename: string;
  additions: number;
  deletions: number;
  lines: DiffLine[];
}

interface SplitCell {
  lineNum?: number;
  content: string;
  type: 'context' | 'delete' | 'add';
}

interface SplitRow {
  left?: SplitCell;
  right?: SplitCell;
}

/**
 * Align unified diff lines into side-by-side row pairs for Split View
 */
function computeSplitRows(lines: DiffLine[]): SplitRow[] {
  const rows: SplitRow[] = [];
  let i = 0;

  while (i < lines.length) {
    const line = lines[i];

    if (line.type === 'context') {
      const clean = line.content.startsWith(' ') ? line.content.slice(1) : line.content;
      rows.push({
        left: {
          lineNum: line.oldLine,
          content: clean,
          type: 'context',
        },
        right: {
          lineNum: line.newLine,
          content: clean,
          type: 'context',
        },
      });
      i++;
    } else {
      // Collect contiguous sequence of deletions and additions in the hunk
      const deletions: DiffLine[] = [];
      const additions: DiffLine[] = [];

      while (i < lines.length && (lines[i].type === 'delete' || lines[i].type === 'add')) {
        if (lines[i].type === 'delete') {
          deletions.push(lines[i]);
        } else {
          additions.push(lines[i]);
        }
        i++;
      }

      const rowCount = Math.max(deletions.length, additions.length);
      for (let k = 0; k < rowCount; k++) {
        const del = deletions[k];
        const add = additions[k];

        rows.push({
          left: del
            ? {
                lineNum: del.oldLine,
                content: del.content.startsWith('-') ? del.content.slice(1) : del.content,
                type: 'delete',
              }
            : undefined,
          right: add
            ? {
                lineNum: add.newLine,
                content: add.content.startsWith('+') ? add.content.slice(1) : add.content,
                type: 'add',
              }
            : undefined,
        });
      }
    }
  }

  return rows;
}

export const DiffViewer: React.FC<DiffViewerProps> = ({
  filename,
  additions,
  deletions,
  lines,
}) => {
  const [viewMode, setViewMode] = useState<'unified' | 'split'>('unified');

  const splitRows = useMemo(() => computeSplitRows(lines), [lines]);

  return (
    <div className="card-archival overflow-hidden flex flex-col">
      {/* Diff Bar Header */}
      <div className="flex flex-wrap items-center justify-between gap-3 px-4 py-2.5 bg-[#EAE2D6]/70 border-b border-[#D9CFBF]">
        <div className="flex items-center gap-2">
          <FileCode className="w-4 h-4 text-[#5F664F]" />
          <span className="font-mono text-[12px] font-semibold text-[#2E3325]">{filename}</span>
          <span className="px-1.5 py-0.5 rounded bg-[#E3E8D6] font-mono text-[11px] text-[#55633C] font-medium">
            +{additions} lines
          </span>
          <span className="px-1.5 py-0.5 rounded bg-[#EFDCD6] font-mono text-[11px] text-[#8C4A3F] font-medium">
            -{deletions} lines
          </span>
        </div>

        {/* View Toggle */}
        <div className="inline-flex rounded bg-[#F7F2EB] p-0.5 border border-[#D9CFBF]">
          <button
            type="button"
            onClick={() => setViewMode('unified')}
            className={clsx(
              'px-2.5 py-1 rounded text-[11px] font-sans font-medium transition-colors flex items-center gap-1.5 cursor-pointer',
              viewMode === 'unified'
                ? 'bg-[#FBF8F3] text-[#2E3325] shadow-xs font-semibold'
                : 'text-[#5F664F] hover:text-[#2E3325]'
            )}
            title="Switch to unified single-column diff"
          >
            <AlignJustify className="w-3.5 h-3.5" />
            <span>Unified Diff</span>
          </button>
          <button
            type="button"
            onClick={() => setViewMode('split')}
            className={clsx(
              'px-2.5 py-1 rounded text-[11px] font-sans font-medium transition-colors flex items-center gap-1.5 cursor-pointer',
              viewMode === 'split'
                ? 'bg-[#FBF8F3] text-[#2E3325] shadow-xs font-semibold'
                : 'text-[#5F664F] hover:text-[#2E3325]'
            )}
            title="Switch to side-by-side split comparison"
          >
            <Columns className="w-3.5 h-3.5" />
            <span>Split View</span>
          </button>
        </div>
      </div>

      {/* Code Display Area */}
      {viewMode === 'unified' ? (
        /* UNIFIED DIFF VIEW */
        <div className="overflow-x-auto bg-[#FBF8F3] font-mono text-[12px] leading-relaxed select-text">
          <table className="w-full text-left border-collapse">
            <tbody>
              {lines.map((line, idx) => {
                const isAdd = line.type === 'add';
                const isDelete = line.type === 'delete';

                return (
                  <tr
                    key={idx}
                    className={clsx(
                      'transition-colors',
                      isAdd && 'bg-[#E3E8D6]/50 text-[#25310F]',
                      isDelete && 'bg-[#EFDCD6]/60 text-[#8C4A3F]',
                      !isAdd && !isDelete && 'hover:bg-[#EAE2D6]/30 text-[#2E3325]'
                    )}
                  >
                    {/* Line Numbers */}
                    <td className="w-10 px-2 py-0.5 text-right text-[#8A8E7C] border-r border-[#D9CFBF]/60 select-none text-[11px]">
                      {line.oldLine ?? ''}
                    </td>
                    <td className="w-10 px-2 py-0.5 text-right text-[#8A8E7C] border-r border-[#D9CFBF]/60 select-none text-[11px]">
                      {line.newLine ?? ''}
                    </td>
                    {/* Symbol Column */}
                    <td className="w-6 px-1 text-center select-none font-bold">
                      {isAdd && '+'}
                      {isDelete && '-'}
                    </td>
                    {/* Code Line Content */}
                    <td className="px-3 py-0.5 whitespace-pre">
                      {line.content}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      ) : (
        /* SIDE-BY-SIDE SPLIT VIEW */
        <div className="overflow-x-auto bg-[#FBF8F3] font-mono text-[12px] leading-relaxed select-text">
          {/* Subheader Column Legend */}
          <div className="grid grid-cols-2 bg-[#EAE2D6]/40 border-b border-[#D9CFBF] text-[11px] font-sans font-medium text-[#5F664F]">
            <div className="px-4 py-1.5 border-r border-[#D9CFBF] flex items-center justify-between">
              <span className="label-caps text-[#8A8E7C]">Original (Repository Base)</span>
              <span className="font-mono text-[#8C4A3F] text-[10px]">-{deletions} removed</span>
            </div>
            <div className="px-4 py-1.5 flex items-center justify-between">
              <span className="label-caps text-[#55633C]">Proposed (Agent Modification)</span>
              <span className="font-mono text-[#55633C] text-[10px]">+{additions} added</span>
            </div>
          </div>

          <table className="w-full text-left border-collapse table-fixed">
            <colgroup>
              <col className="w-[50%]" />
              <col className="w-[50%]" />
            </colgroup>
            <tbody>
              {splitRows.map((row, idx) => {
                const isLeftDelete = row.left?.type === 'delete';
                const isRightAdd = row.right?.type === 'add';

                return (
                  <tr key={idx} className="border-b border-[#D9CFBF]/30">
                    {/* LEFT COLUMN: BASE / DELETIONS */}
                    <td
                      className={clsx(
                        'p-0 align-top border-r border-[#D9CFBF]',
                        isLeftDelete && 'bg-[#EFDCD6]/60 text-[#8C4A3F]',
                        !row.left && 'bg-[#EAE2D6]/20 select-none'
                      )}
                    >
                      {row.left ? (
                        <div className="flex items-start">
                          <span className="w-10 px-2 py-0.5 text-right text-[#8A8E7C] border-r border-[#D9CFBF]/60 select-none text-[11px] shrink-0">
                            {row.left.lineNum ?? ''}
                          </span>
                          <span className="w-6 px-1 py-0.5 text-center select-none font-bold shrink-0">
                            {isLeftDelete ? '-' : ''}
                          </span>
                          <span className="px-2 py-0.5 whitespace-pre overflow-x-auto">
                            {row.left.content}
                          </span>
                        </div>
                      ) : (
                        <div className="py-0.5 px-3 text-[#8A8E7C]/40 text-center select-none text-[11px]">
                          &nbsp;
                        </div>
                      )}
                    </td>

                    {/* RIGHT COLUMN: MODIFIED / ADDITIONS */}
                    <td
                      className={clsx(
                        'p-0 align-top',
                        isRightAdd && 'bg-[#E3E8D6]/50 text-[#25310F]',
                        !row.right && 'bg-[#EAE2D6]/20 select-none'
                      )}
                    >
                      {row.right ? (
                        <div className="flex items-start">
                          <span className="w-10 px-2 py-0.5 text-right text-[#8A8E7C] border-r border-[#D9CFBF]/60 select-none text-[11px] shrink-0">
                            {row.right.lineNum ?? ''}
                          </span>
                          <span className="w-6 px-1 py-0.5 text-center select-none font-bold shrink-0 text-[#55633C]">
                            {isRightAdd ? '+' : ''}
                          </span>
                          <span className="px-2 py-0.5 whitespace-pre overflow-x-auto">
                            {row.right.content}
                          </span>
                        </div>
                      ) : (
                        <div className="py-0.5 px-3 text-[#8A8E7C]/40 text-center select-none text-[11px]">
                          &nbsp;
                        </div>
                      )}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
};
