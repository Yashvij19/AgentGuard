import React, { useEffect } from 'react';
import { X } from 'lucide-react';
import clsx from 'clsx';

interface ModalProps {
  isOpen: boolean;
  onClose: () => void;
  title: string;
  subtitle?: string;
  children: React.ReactNode;
  maxWidth?: 'sm' | 'md' | 'lg' | 'xl';
}

export const Modal: React.FC<ModalProps> = ({
  isOpen,
  onClose,
  title,
  subtitle,
  children,
  maxWidth = 'md',
}) => {
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose();
    };
    if (isOpen) {
      window.addEventListener('keydown', handleKeyDown);
      document.body.style.overflow = 'hidden';
    }
    return () => {
      window.removeEventListener('keydown', handleKeyDown);
      document.body.style.overflow = 'unset';
    };
  }, [isOpen, onClose]);

  if (!isOpen) return null;

  const maxWidthClass = {
    sm: 'max-w-md',
    md: 'max-w-lg',
    lg: 'max-w-2xl',
    xl: 'max-w-4xl',
  }[maxWidth];

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      {/* Warm soft backdrop */}
      <div
        className="fixed inset-0 bg-[#2E3325]/30 backdrop-blur-[2px] transition-opacity duration-300"
        onClick={onClose}
      />

      {/* Stationery Modal Dialog */}
      <div
        className={clsx(
          'relative w-full bg-[#FBF8F3] border border-[#D9CFBF] rounded-lg shadow-xl overflow-hidden z-10 animate-rise-in',
          maxWidthClass
        )}
      >
        {/* Header */}
        <div className="flex items-start justify-between px-6 py-4 bg-[#EAE2D6]/60 border-b border-[#D9CFBF]">
          <div>
            <h3 className="font-serif text-[22px] font-medium text-[#2E3325]">
              {title}
            </h3>
            {subtitle && (
              <p className="text-[13px] text-[#5F664F] mt-0.5">{subtitle}</p>
            )}
          </div>
          <button
            onClick={onClose}
            className="text-[#8A8E7C] hover:text-[#2E3325] p-1 rounded hover:bg-[#EAE2D6] transition-colors"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Content */}
        <div className="p-6">{children}</div>
      </div>
    </div>
  );
};
