import React from 'react';
import type { LucideIcon } from 'lucide-react';

interface StatCardProps {
  label: string;
  value: string | number;
  subtitle?: string;
  icon: LucideIcon;
  variant?: 'default' | 'amber' | 'emerald' | 'rose' | 'indigo';
  onClick?: () => void;
}

export const StatCard: React.FC<StatCardProps> = ({
  label,
  value,
  subtitle,
  icon: Icon,
  variant = 'default',
  onClick,
}) => {
  const variantStyles = {
    default: {
      card: 'bg-white border-slate-200 hover:border-slate-300',
      iconBox: 'bg-slate-100 text-slate-700',
      badge: 'text-slate-500',
    },
    amber: {
      card: 'bg-white border-amber-200/80 hover:border-amber-300 shadow-xs',
      iconBox: 'bg-amber-50 text-amber-600 border border-amber-200/50',
      badge: 'text-amber-700',
    },
    emerald: {
      card: 'bg-white border-emerald-200/80 hover:border-emerald-300 shadow-xs',
      iconBox: 'bg-emerald-50 text-emerald-600 border border-emerald-200/50',
      badge: 'text-emerald-700',
    },
    rose: {
      card: 'bg-white border-rose-200/80 hover:border-rose-300 shadow-xs',
      iconBox: 'bg-rose-50 text-rose-600 border border-rose-200/50',
      badge: 'text-rose-700',
    },
    indigo: {
      card: 'bg-white border-indigo-200/80 hover:border-indigo-300 shadow-xs',
      iconBox: 'bg-indigo-50 text-indigo-600 border border-indigo-200/50',
      badge: 'text-indigo-700',
    },
  }[variant];

  return (
    <div
      onClick={onClick}
      className={`p-5 rounded-xl border transition-all ${variantStyles.card} ${
        onClick ? 'cursor-pointer hover:shadow-md hover:-translate-y-0.5' : ''
      }`}
    >
      <div className="flex items-center justify-between">
        <span className="text-xs font-semibold text-slate-500 uppercase tracking-wider">
          {label}
        </span>
        <div className={`p-2.5 rounded-lg ${variantStyles.iconBox}`}>
          <Icon size={18} />
        </div>
      </div>
      <div className="mt-3 flex items-baseline gap-2">
        <span className="text-2xl font-bold text-slate-900 tracking-tight">{value}</span>
      </div>
      {subtitle && <p className="mt-1 text-xs text-slate-500">{subtitle}</p>}
    </div>
  );
};
