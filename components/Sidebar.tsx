'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { useEffect, useState } from 'react';
import {
  LayoutDashboard,
  MapPin,
  Truck,
  BarChart3,
  Trash2,
  ChevronRight,
} from 'lucide-react';

const navItems = [
  { href: '/', label: 'Dashboard', icon: LayoutDashboard },
  { href: '/map', label: 'Prediction Map', icon: MapPin },
  { href: '/routes', label: 'Fleet & Routes', icon: Truck },
  { href: '/analytics', label: 'Analytics', icon: BarChart3 },
];

export default function Sidebar() {
  const pathname = usePathname();
  const [modelInfo, setModelInfo] = useState<{ maeTons: number | null; label: string } | null>(null);

  useEffect(() => {
    fetch('http://localhost:8000/api/model/status')
      .then(r => r.json())
      .then(d => setModelInfo({ maeTons: d.mae_tons, label: d.accuracy_label }))
      .catch(() => {});
  }, [pathname]);

  return (
    <aside className="fixed top-0 left-0 h-screen w-60 bg-blue-900 text-white flex flex-col z-50 shadow-xl">
      {/* Logo */}
      <div className="flex items-center gap-3 px-5 py-5 border-b border-blue-800">
        <div className="w-9 h-9 bg-green-500 rounded-lg flex items-center justify-center flex-shrink-0">
          <Trash2 size={18} className="text-white" />
        </div>
        <div>
          <p className="font-bold text-sm leading-tight">Austin SmartWaste</p>
          <p className="text-blue-300 text-xs">Austin · Texas</p>
        </div>
      </div>

      {/* Nav */}
      <nav className="flex-1 py-6 px-3 space-y-1">
        {navItems.map(({ href, label, icon: Icon }) => {
          const active = pathname === href;
          return (
            <Link
              key={href}
              href={href}
              className={`flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium group transition-all ${
                active
                  ? 'bg-blue-700 text-white shadow-md'
                  : 'text-blue-200 hover:bg-blue-800 hover:text-white'
              }`}
            >
              <Icon size={18} className={active ? 'text-green-400' : 'text-blue-400 group-hover:text-green-400'} />
              <span className="flex-1">{label}</span>
              {active && <ChevronRight size={14} className="text-blue-300" />}
            </Link>
          );
        })}
      </nav>

      {/* Footer */}
      <div className="px-5 py-4 border-t border-blue-800">
        <p className="text-blue-400 text-xs">Austin Resource Recovery</p>
        <p className="text-blue-500 text-xs">
          {modelInfo === null
            ? 'Model: loading…'
            : modelInfo.maeTons === null
              ? 'Model: untrained'
              : `Avg error: ±${modelInfo.maeTons} T · ${modelInfo.label}`}
        </p>
      </div>
    </aside>
  );
}
