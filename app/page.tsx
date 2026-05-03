'use client';

import { useState, useEffect } from 'react';
import Header from '@/components/Header';
import {
  ComposedChart, Bar, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer,
} from 'recharts';
import { Trash2, Truck, Fuel, AlertTriangle, TrendingUp, TrendingDown, Minus } from 'lucide-react';
import { toast } from 'react-hot-toast';

const iconMap: Record<string, React.ElementType> = {
  trash: Trash2, truck: Truck, fuel: Fuel, alert: AlertTriangle,
};

const severityStyles: Record<string, string> = {
  critical: 'border-l-4 border-red-500 bg-red-50',
  warning: 'border-l-4 border-yellow-400 bg-yellow-50',
  success: 'border-l-4 border-green-500 bg-green-50',
};

const severityBadge: Record<string, string> = {
  critical: 'bg-red-100 text-red-700',
  warning: 'bg-yellow-100 text-yellow-700',
  success: 'bg-green-100 text-green-700',
};

export default function DashboardPage() {
  const [kpiCards, setKpiCards] = useState<any[]>([]);
  const [wasteChartData, setWasteChartData] = useState<any[]>([]);
  const [systemAlerts, setSystemAlerts] = useState<any[]>([]);

  useEffect(() => {
    fetch('http://localhost:8000/api/dashboard/kpi')
      .then(res => res.json())
      .then(data => setKpiCards(data))
      .catch(err => console.error("Error fetching KPIs:", err));

    fetch('http://localhost:8000/api/dashboard/chart')
      .then(res => res.json())
      .then(data => setWasteChartData(data))
      .catch(err => console.error("Error fetching chart data:", err));

    fetch('http://localhost:8000/api/alerts')
      .then(res => res.json())
      .then(data => setSystemAlerts(data))
      .catch(err => console.error("Error fetching alerts:", err));
  }, []);

  return (
    <div className="min-h-screen bg-gray-50">
      <Header title="Austin Waste Dashboard" subtitle="Austin Resource Recovery · City of Austin Waste Management" />
      <main className="pt-16 p-6">

        {/* KPI Cards */}
        <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-4 mb-6">
          {kpiCards.map((card) => {
            const Icon = iconMap[card.icon];
            const TrendIcon = card.trendDir === 'up' ? TrendingUp : card.trendDir === 'neutral' ? Minus : AlertTriangle;
            return (
              <div
                key={card.title}
                className={`bg-white rounded-xl p-5 border shadow-sm hover:shadow-md transition-shadow ${card.accent}`}
              >
                <div className="flex items-start justify-between mb-3">
                  <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide leading-tight max-w-[120px]">
                    {card.title}
                  </p>
                  <div className="w-9 h-9 rounded-lg bg-white shadow flex items-center justify-center flex-shrink-0">
                    {Icon && <Icon size={16} className={card.trendColor} />}
                  </div>
                </div>
                <p className="text-2xl font-extrabold text-gray-900 mb-1">{card.value}</p>
                <span className={`inline-flex items-center gap-1 text-xs font-medium ${card.trendColor}`}>
                  <TrendIcon size={12} />
                  {card.trend}
                </span>
              </div>
            );
          })}
        </div>

        {/* Main Content Row */}
        <div className="grid grid-cols-1 xl:grid-cols-3 gap-5">

          {/* Chart — 2/3 width */}
          <div className="xl:col-span-2 bg-white rounded-xl shadow-sm border border-gray-100 p-5">
            <div className="flex items-center justify-between mb-4">
              <div>
                <h2 className="text-sm font-bold text-gray-800">Waste Generation: Predicted vs. Actual</h2>
                <p className="text-xs text-gray-500">Past 7 Days · Tons of waste collected</p>
              </div>
              <span className="bg-blue-50 text-blue-700 text-xs font-semibold px-2.5 py-1 rounded-full">AI Tracking</span>
            </div>
            <ResponsiveContainer width="100%" height={280}>
              <ComposedChart data={wasteChartData} margin={{ top: 5, right: 10, left: -10, bottom: 5 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#f0f4f8" />
                <XAxis dataKey="day" tick={{ fontSize: 12, fill: '#64748b' }} axisLine={false} tickLine={false} />
                <YAxis tick={{ fontSize: 12, fill: '#64748b' }} axisLine={false} tickLine={false} unit=" T" />
                <Tooltip
                  contentStyle={{ borderRadius: 8, border: 'none', boxShadow: '0 4px 24px rgba(0,0,0,0.1)', fontSize: 12 }}
                  formatter={((v: unknown) => [`${v} Tons`]) as never}
                />
                <Legend formatter={(v) => v === 'predicted' ? 'AI Predicted' : 'Actual Collected'} wrapperStyle={{ fontSize: 12 }} />
                <Bar dataKey="actual" fill="#bfdbfe" radius={[4, 4, 0, 0]} name="actual" />
                <Line type="monotone" dataKey="predicted" stroke="#1d4ed8" strokeWidth={2.5} dot={{ fill: '#1d4ed8', r: 4 }} name="predicted" />
              </ComposedChart>
            </ResponsiveContainer>
          </div>

          {/* Alerts — 1/3 width */}
          <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-5 flex flex-col">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-sm font-bold text-gray-800">System Alerts</h2>
              <span className="w-5 h-5 bg-red-500 text-white text-xs font-bold rounded-full flex items-center justify-center">
                {systemAlerts.filter(a => a.severity !== 'success').length}
              </span>
            </div>
            <div className="space-y-3 flex-1 overflow-y-auto">
              {systemAlerts.map((alert) => (
                <div key={alert.id} className={`rounded-lg p-3 ${severityStyles[alert.severity]}`}>
                  <div className="flex items-center gap-2 mb-1">
                    <span className="text-base">{alert.icon}</span>
                    <p className="text-xs font-semibold text-gray-800 leading-tight">{alert.title}</p>
                  </div>
                  <p className="text-xs text-gray-600 mb-1 leading-relaxed">{alert.message}</p>
                  <span className={`text-[10px] font-semibold px-2 py-0.5 rounded-full ${severityBadge[alert.severity]}`}>{alert.time}</span>
                </div>
              ))}
            </div>
            <button 
              onClick={() => toast.success('All system alerts have been acknowledged.')}
              className="mt-4 w-full text-xs font-medium text-blue-700 hover:text-blue-800 bg-blue-50 hover:bg-blue-100 rounded-lg py-2 transition-colors"
            >
              Acknowledge All Alerts →
            </button>
          </div>
        </div>
      </main>
    </div>
  );
}
