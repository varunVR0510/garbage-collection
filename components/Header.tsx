'use client';

import { Bell, Search, ChevronDown, Calendar } from 'lucide-react';

interface HeaderProps {
  title: string;
  subtitle?: string;
}

export default function Header({ title, subtitle }: HeaderProps) {
  const today = new Date().toLocaleDateString('en-US', {
    weekday: 'long', year: 'numeric', month: 'long', day: 'numeric',
  });

  return (
    <header className="fixed top-0 left-60 right-0 h-16 bg-white border-b border-gray-200 flex items-center px-6 gap-4 z-40 shadow-sm">
      {/* Page Title */}
      <div className="flex-1 min-w-0">
        <h1 className="text-base font-bold text-gray-900 leading-tight truncate">{title}</h1>
        {subtitle && <p className="text-xs text-gray-500">{subtitle}</p>}
      </div>

      {/* Search */}
      <div className="hidden md:flex items-center gap-2 bg-gray-100 rounded-lg px-3 py-2 w-52">
        <Search size={14} className="text-gray-400 flex-shrink-0" />
        <input
          placeholder="Search zones, trucks..."
          className="bg-transparent text-sm text-gray-600 outline-none w-full placeholder:text-gray-400"
        />
      </div>

      {/* Date */}
      <div className="hidden lg:flex items-center gap-2 text-sm text-gray-600 bg-gray-50 border border-gray-200 rounded-lg px-3 py-2 cursor-pointer hover:border-blue-300">
        <Calendar size={14} className="text-blue-600" />
        <span className="text-xs font-medium">{today}</span>
        <ChevronDown size={12} className="text-gray-400" />
      </div>

      {/* Bell */}
      <button className="relative w-9 h-9 rounded-full bg-gray-100 hover:bg-gray-200 flex items-center justify-center">
        <Bell size={16} className="text-gray-600" />
        <span className="absolute -top-0.5 -right-0.5 w-4 h-4 bg-red-500 rounded-full text-white text-[9px] flex items-center justify-center font-bold">3</span>
      </button>

      {/* Avatar */}
      <div className="flex items-center gap-2 cursor-pointer hover:opacity-80">
        <div className="w-9 h-9 rounded-full bg-gradient-to-br from-blue-500 to-blue-700 flex items-center justify-center text-white text-sm font-bold shadow">
          AM
        </div>
        <div className="hidden lg:block text-right">
          <p className="text-xs font-semibold text-gray-800">Admin</p>
          <p className="text-xs text-gray-500">City Manager</p>
        </div>
      </div>
    </header>
  );
}
