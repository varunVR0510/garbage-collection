'use client';

import { Bell, Search, ChevronDown, Calendar, RotateCcw } from 'lucide-react';
import { useSelectedDate } from '@/lib/useSelectedDate';
import { useEffect, useRef, useState } from 'react';

interface HeaderProps {
  title: string;
  subtitle?: string;
}

function todayIso(): string {
  return new Date().toISOString().slice(0, 10);
}

export default function Header({ title, subtitle }: HeaderProps) {
  const [date, setDate] = useSelectedDate();
  const [open, setOpen] = useState(false);
  const [mounted, setMounted] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => { setMounted(true); }, []);

  const display = mounted
    ? new Date(date + 'T00:00:00').toLocaleDateString('en-US', {
        weekday: 'long', year: 'numeric', month: 'long', day: 'numeric',
      })
    : ' ';
  const isToday = mounted ? date === todayIso() : true;

  return (
    <header className="fixed top-0 left-60 right-0 h-16 bg-white border-b border-gray-200 flex items-center px-6 gap-4 z-40 shadow-sm">
      <div className="flex-1 min-w-0">
        <h1 className="text-base font-bold text-gray-900 leading-tight truncate">{title}</h1>
        {subtitle && <p className="text-xs text-gray-500">{subtitle}</p>}
      </div>

      <div className="hidden md:flex items-center gap-2 bg-gray-100 rounded-lg px-3 py-2 w-52">
        <Search size={14} className="text-gray-400 flex-shrink-0" />
        <input
          placeholder="Search zones, trucks..."
          className="bg-transparent text-sm text-gray-600 outline-none w-full placeholder:text-gray-400"
        />
      </div>

      {/* Date picker */}
      <div className="relative">
        <button
          onClick={() => {
            setOpen(o => !o);
            setTimeout(() => inputRef.current?.showPicker?.(), 0);
          }}
          className={`hidden lg:flex items-center gap-2 text-sm rounded-lg px-3 py-2 border transition ${
            isToday
              ? 'bg-gray-50 border-gray-200 text-gray-600 hover:border-blue-300'
              : 'bg-blue-50 border-blue-300 text-blue-700 hover:border-blue-400'
          }`}
        >
          <Calendar size={14} className={isToday ? 'text-blue-600' : 'text-blue-700'} />
          <span className="text-xs font-medium">{display}</span>
          <ChevronDown size={12} className="text-gray-400" />
        </button>
        <input
          ref={inputRef}
          type="date"
          value={date}
          onChange={(e) => setDate(e.target.value)}
          className="absolute right-0 top-full mt-1 opacity-0 pointer-events-none w-0 h-0"
          aria-hidden
        />
        {!isToday && (
          <button
            onClick={() => setDate(todayIso())}
            title="Reset to today"
            className="absolute -bottom-6 right-0 text-[10px] text-blue-700 hover:underline flex items-center gap-1 whitespace-nowrap"
          >
            <RotateCcw size={10} /> back to today
          </button>
        )}
      </div>

      <button className="relative w-9 h-9 rounded-full bg-gray-100 hover:bg-gray-200 flex items-center justify-center">
        <Bell size={16} className="text-gray-600" />
        <span className="absolute -top-0.5 -right-0.5 w-4 h-4 bg-red-500 rounded-full text-white text-[9px] flex items-center justify-center font-bold">3</span>
      </button>

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
