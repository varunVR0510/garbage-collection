'use client';

import { useState, useEffect } from 'react';
import Header from '@/components/Header';
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer,
} from 'recharts';
import { BrainCircuit, RefreshCw, TrendingUp, CheckCircle } from 'lucide-react';
import { toast } from 'react-hot-toast';

export default function AnalyticsPage() {
  const [retraining, setRetraining] = useState(false);
  const [retrained, setRetrained] = useState(false);
  const [lastMae, setLastMae] = useState<string | null>(null);
  const [analyticsMetrics, setAnalyticsMetrics] = useState<any[]>([]);
  const [fuelChartData, setFuelChartData] = useState<any[]>([]);
  const [collectionsData, setCollectionsData] = useState<any[]>([]);

  const loadAll = () => {
    fetch('http://localhost:8000/api/metrics')
      .then(res => res.json())
      .then(data => setAnalyticsMetrics(data))
      .catch(err => console.error("Error fetching metrics:", err));

    fetch('http://localhost:8000/api/fuel')
      .then(res => res.json())
      .then(data => setFuelChartData(data))
      .catch(err => console.error("Error fetching fuel data:", err));

    fetch('http://localhost:8000/api/collections')
      .then(res => res.json())
      .then(data => setCollectionsData(data))
      .catch(err => console.error("Error fetching collections data:", err));
  };

  useEffect(() => { loadAll(); }, []);

  const handleRetrain = async () => {
    setRetraining(true);
    setRetrained(false);
    try {
      const res = await toast.promise(
        fetch('http://localhost:8000/api/model/retrain', { method: 'POST' })
          .then(async r => {
            if (!r.ok) throw new Error((await r.json()).detail || 'Retrain failed');
            return r.json();
          }),
        {
          loading: 'Retraining XGBoost on real Austin dataset…',
          success: (d: any) => `Retraining complete · MAE = ±${d.mae_tons} T (${d.accuracy_label})`,
          error: (e: any) => e.message || 'Retraining failed',
        }
      );
      setLastMae(`±${res.mae_tons} T (${res.accuracy_label})`);
      setRetrained(true);
      loadAll();
    } catch (e) {
      // toast already shown
    } finally {
      setRetraining(false);
    }
  };

  return (
    <div className="min-h-screen bg-gray-50">
      <Header title="System Performance & AI Evaluation" subtitle="Model accuracy, fuel savings, and feedback loop metrics" />
      <main className="pt-16 p-6 space-y-5">

        {/* Top Metrics */}
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
          {analyticsMetrics.map((m) => (
            <div key={m.label} className="bg-white rounded-xl shadow-sm border border-gray-100 p-5 hover:shadow-md transition-shadow">
              <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-2">{m.label}</p>
              <p className={`text-3xl font-extrabold mb-1 ${m.color}`}>{m.value}</p>
              <p className="text-xs text-gray-500">{m.sub}</p>
            </div>
          ))}
        </div>

        {/* Chart + Table Row */}
        <div className="grid grid-cols-1 xl:grid-cols-2 gap-5">

          {/* Fuel Bar Chart */}
          <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-5">
            <div className="mb-4">
              <h2 className="text-sm font-bold text-gray-800">Fuel Consumption: Traditional vs. AI Optimized</h2>
              <p className="text-xs text-gray-500 mt-0.5">Weekly comparison (Liters consumed)</p>
            </div>
            <ResponsiveContainer width="100%" height={240}>
              <BarChart data={fuelChartData} barCategoryGap="30%" margin={{ top: 5, right: 10, left: -10, bottom: 5 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#f0f4f8" />
                <XAxis dataKey="week" tick={{ fontSize: 11, fill: '#64748b' }} axisLine={false} tickLine={false} />
                <YAxis tick={{ fontSize: 11, fill: '#64748b' }} axisLine={false} tickLine={false} unit="L" />
                <Tooltip
                  contentStyle={{ borderRadius: 8, border: 'none', boxShadow: '0 4px 24px rgba(0,0,0,0.1)', fontSize: 12 }}
                  formatter={((v: unknown) => [`${v} L`]) as never}
                />
                <Legend wrapperStyle={{ fontSize: 12 }} />
                <Bar dataKey="traditional" name="Traditional Route" fill="#fca5a5" radius={[4, 4, 0, 0]} />
                <Bar dataKey="aiOptimized" name="AI Optimized" fill="#6ee7b7" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
            <div className="mt-3 flex items-center gap-2 text-xs text-green-700 bg-green-50 rounded-lg px-3 py-2">
              <TrendingUp size={13} />
              <span>AI routing uses <strong>~{(() => {
                if (!fuelChartData.length) return '0';
                const tot = fuelChartData.reduce((s, w) => s + (w.traditional || 0), 0);
                const ai = fuelChartData.reduce((s, w) => s + (w.aiOptimized || 0), 0);
                return tot > 0 ? Math.round((1 - ai / tot) * 100) : 0;
              })()}% less fuel</strong> on average vs. traditional fixed routes.</span>
            </div>
          </div>

          {/* Data Table */}
          <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-5 flex flex-col">
            <h2 className="text-sm font-bold text-gray-800 mb-3">Recent Collections Data Input</h2>
            <div className="flex-1 overflow-y-auto">
              <table className="w-full text-xs">
                <thead>
                  <tr className="border-b border-gray-100">
                    {['Date', 'Zone', 'Predicted', 'Actual', 'Error'].map(h => (
                      <th key={h} className="pb-2 text-left font-semibold text-gray-500 text-[10px] uppercase tracking-wide pr-2">{h}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {collectionsData.map((row, i) => (
                    <tr key={i} className="border-b border-gray-50 hover:bg-gray-50 transition-colors group">
                      <td className="py-2.5 pr-2 text-gray-600 font-medium whitespace-nowrap">{row.date}</td>
                      <td className="py-2.5 pr-2 text-gray-800 font-medium max-w-[120px] truncate">{row.zone}</td>
                      <td className="py-2.5 pr-2 text-blue-700 font-semibold">{row.predicted}</td>
                      <td className="py-2.5 pr-2 text-gray-800 font-semibold">{row.actual}</td>
                      <td className="py-2.5">
                        <span className={`font-bold px-1.5 py-0.5 rounded text-[10px] ${
                          row.error.startsWith('+') ? 'bg-red-50 text-red-600' : 'bg-green-50 text-green-600'
                        }`}>
                          {row.error}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>

        {/* Retraining Section */}
        <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-5">
          <div className="flex flex-col sm:flex-row sm:items-center gap-4">
            <div className="flex items-center gap-3 flex-1">
              <div className="w-12 h-12 bg-blue-700 rounded-xl flex items-center justify-center flex-shrink-0">
                <BrainCircuit size={22} className="text-white" />
              </div>
              <div>
                <h2 className="text-sm font-bold text-gray-800">Feedback Loop &amp; Model Retraining</h2>
                <p className="text-xs text-gray-500 mt-0.5">
                  Feed this week&apos;s real collection data back into the AI model to improve predictions.
                  {retrained && lastMae && <span className="ml-2 text-green-600 font-semibold">✓ Retraining complete — Avg error = {lastMae}</span>}
                </p>
              </div>
            </div>
            <button
              onClick={handleRetrain}
              disabled={retraining}
              className={`flex items-center gap-2 text-sm font-bold px-5 py-2.5 rounded-xl shadow transition-all flex-shrink-0 ${
                retrained
                  ? 'bg-green-600 hover:bg-green-700 text-white'
                  : 'bg-blue-700 hover:bg-blue-800 text-white'
              } ${retraining ? 'opacity-70 cursor-not-allowed' : ''}`}
            >
              {retraining ? (
                <><RefreshCw size={15} className="animate-spin" /> Training in progress…</>
              ) : retrained ? (
                <><CheckCircle size={15} /> Retraining Complete</>
              ) : (
                <><RefreshCw size={15} /> Trigger Model Retraining (Feedback Loop)</>
              )}
            </button>
          </div>
        </div>

      </main>
    </div>
  );
}
