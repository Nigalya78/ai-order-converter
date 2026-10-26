import React from 'react';
import { Loader2 } from 'lucide-react';

interface LoadingSpinnerProps {
  label?: string;
  size?: 'sm' | 'md' | 'lg';
  className?: string;
}

export const LoadingSpinner: React.FC<LoadingSpinnerProps> = ({
  label,
  size = 'md',
  className = '',
}) => {
  const sizeMap = {
    sm: 16,
    md: 24,
    lg: 32,
  };

  return (
    <div className={`flex items-center justify-center gap-2.5 text-slate-500 ${className}`}>
      <Loader2 size={sizeMap[size]} className="animate-spin text-indigo-600" />
      {label && <span className="text-sm font-medium text-slate-600">{label}</span>}
    </div>
  );
};
