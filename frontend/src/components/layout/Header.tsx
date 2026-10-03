import React from 'react';
import { FolderGit2, ChevronsUpDown, User } from 'lucide-react';

interface HeaderProps {
  currentRepo?: string;
}

export const Header: React.FC<HeaderProps> = ({
  currentRepo = 'AgentGuard Monitored',
}) => {
  return (
    <header className="fixed top-0 left-64 right-0 h-16 bg-[#F7F2EB]/95 backdrop-blur-[2px] border-b border-[#D9CFBF] z-40 flex items-center justify-between px-8 select-none">
      {/* Left: Monitored Repository & Environment Pill */}
      <div className="flex items-center gap-4">
        <div className="flex items-center gap-2 bg-[#FBF8F3] px-3 py-1.5 rounded border border-[#D9CFBF] text-[13px] text-[#2E3325] cursor-pointer hover:bg-[#EAE2D6]/40 transition-colors">
          <FolderGit2 className="w-4 h-4 text-[#5F664F]" />
          <span className="font-mono text-[12px] font-medium">{currentRepo}</span>
          <ChevronsUpDown className="w-3.5 h-3.5 text-[#8A8E7C]" />
        </div>

        <div className="flex items-center gap-1.5 px-2.5 py-0.5 rounded-full bg-[#E3E8D6] text-[#2E3325] border border-[#BDCD9D] label-caps text-[10px]">
          <span className="w-1.5 h-1.5 rounded-full bg-[#55633C]" />
          <span>Production</span>
        </div>
      </div>

      {/* Right: Custodian User Avatar */}
      <div className="flex items-center gap-4">
        <div
          title="Lead Custodian Auditor"
          className="w-8 h-8 rounded-full bg-[#55633C] text-[#F7F2EB] flex items-center justify-center shadow-xs cursor-pointer hover:bg-[#6F7D55] transition-colors"
        >
          <User className="w-4 h-4 stroke-[2]" />
        </div>
      </div>
    </header>
  );
};
