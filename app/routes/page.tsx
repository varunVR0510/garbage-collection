'use client';

import { useState, useEffect, Suspense } from 'react';
import { useSearchParams } from 'next/navigation';
import { toast } from 'react-hot-toast';
import Header from '@/components/Header';
import { Truck, MapPin, Clock, Fuel, Route, Zap, CheckCircle2, Circle, Play, Loader2 } from 'lucide-react';
import { useSelectedDate } from '@/lib/useSelectedDate';

const statusStyles: Record<string, string> = {
  'on-route': 'bg-blue-100 text-blue-700',
  'collecting': 'bg-indigo-100 text-indigo-700',
  'departing': 'bg-cyan-100 text-cyan-700',
  'idle': 'bg-gray-100 text-gray-600',
  'returning': 'bg-green-100 text-green-700',
};

const statusLabel = (s: string) => ({
  'on-route': 'On Route',
  'collecting': 'Collecting',
  'departing': 'Departing',
  'returning': 'Returning',
  'idle': 'Idle',
}[s] ?? s);

const stepStyles: Record<string, { icon: string; ring: string; dot: string }> = {
  start: { icon: '🏭', ring: 'ring-2 ring-blue-300', dot: 'bg-blue-500' },
  high: { icon: '🚨', ring: 'ring-2 ring-red-300', dot: 'bg-red-500' },
  medium: { icon: '⚠️', ring: 'ring-2 ring-yellow-300', dot: 'bg-yellow-500' },
  low: { icon: '🏠', ring: 'ring-2 ring-green-300', dot: 'bg-green-500' },
  normal: { icon: '🏠', ring: 'ring-2 ring-yellow-300', dot: 'bg-yellow-500' },
  end: { icon: '🗑️', ring: 'ring-2 ring-gray-300', dot: 'bg-gray-400' },
};
const defaultStepStyle = { icon: '📍', ring: 'ring-2 ring-gray-200', dot: 'bg-gray-400' };

function RoutesContent() {
  const searchParams = useSearchParams();
  const [selectedDate] = useSelectedDate();
  const [localTrucks, setLocalTrucks] = useState<any[]>([]);
  const [routeTimeline, setRouteTimeline] = useState<any[]>([]);
  const [selectedTruck, setSelectedTruck] = useState<string | null>(null);
  const [isOptimizing, setIsOptimizing] = useState(false);

  const [summary, setSummary] = useState<{
    distance: string; fuel: string; time: string;
    savedKm?: number; savedFuelL?: number; savedPct?: number;
    tripsAvoided?: number; totalZones?: number; mustCollect?: number;
    stops?: number; targetDistricts?: string[];
    capacity?: number; currentLoad?: number; tourLoad?: number; loadFraction?: number;
  }>({ distance: "...", fuel: "...", time: "..." });

  const [weekly, setWeekly] = useState<{
    days: Array<{ day: string; routes: number; predicted_tons: number; districts: any[] }>;
    weekTotalRoutes?: number; weekTotalTons?: number;
  }>({ days: [] });

  const [dispatches, setDispatches] = useState<any[]>([]);
  const [plan, setPlan] = useState<any | null>(null);
  const [autoAssigning, setAutoAssigning] = useState(false);

  const loadDispatches = () => {
    fetch('http://localhost:8000/api/dispatch/today')
      .then(r => r.json())
      .then(setDispatches)
      .catch(() => {});
  };

  const loadPlan = () => {
    fetch(`http://localhost:8000/api/dispatch/plan?date=${selectedDate}`)
      .then(r => r.json())
      .then(setPlan)
      .catch(() => {});
  };

  const handleAutoAssign = async () => {
    setAutoAssigning(true);
    try {
      await toast.promise(
        fetch(`http://localhost:8000/api/dispatch/auto-assign?date=${selectedDate}`, { method: 'POST' })
          .then(async r => {
            if (!r.ok) throw new Error((await r.json()).detail || 'Auto-assign failed');
            return r.json();
          }),
        {
          loading: 'AI matching trucks to nearest zones…',
          success: (d: any) =>
            d.dispatched > 0
              ? `Dispatched ${d.dispatched} trucks · saved ${d.saved_km} km / ${d.saved_fuel_l} L (${d.saved_pct}%)`
              : 'No new assignments — all priority zones already covered',
          error: (e: any) => e.message || 'Auto-assign failed',
        }
      );
      loadDispatches();
      loadPlan();
    } finally {
      setAutoAssigning(false);
    }
  };

  const fetchRouteData = async () => {
    const q = `?date=${selectedDate}`;
    // If a truck is selected, fetch its specific route. Otherwise the city-wide VRP plan.
    if (selectedTruck) {
      const truckRes = await fetch(`http://localhost:8000/api/routes/truck/${selectedTruck}${q}`).then(r => r.json());
      if (truckRes && truckRes.timeline) {
        setRouteTimeline(truckRes.timeline);
        if (truckRes.summary) setSummary(truckRes.summary);
        return truckRes.summary;
      }
    }
    const [timelineRes, summaryRes] = await Promise.all([
      fetch(`http://localhost:8000/api/routes/optimized${q}`).then(r => r.json()),
      fetch(`http://localhost:8000/api/routes/summary${q}`).then(r => r.json()),
    ]);
    setRouteTimeline(timelineRes);
    setSummary(summaryRes);
    return summaryRes;
  };

  // Fetch date-dependent data (fleet, weekly schedule, dispatches, plan)
  useEffect(() => {
    const q = `?date=${selectedDate}`;
    fetch(`http://localhost:8000/api/fleet/status${q}`)
      .then(res => res.json())
      .then(data => {
        setLocalTrucks(data);
        if (data.length > 0 && !selectedTruck) setSelectedTruck(data[0].id);
      })
      .catch(err => console.error("Error fetching fleet:", err));

    fetch('http://localhost:8000/api/schedule/weekly')
      .then(r => r.json())
      .then(data => setWeekly(data))
      .catch(err => console.error("Error fetching schedule:", err));

    loadDispatches();
    loadPlan();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedDate]);

  // Re-fetch the truck-specific route whenever the selected truck or date changes
  useEffect(() => {
    fetchRouteData().catch(err => console.error("Error fetching routes:", err));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedTruck, selectedDate]);

  // Reload dispatches when the page is re-entered (e.g., from Map after assigning)
  useEffect(() => {
    const dispatchId = searchParams.get('dispatchId');
    if (dispatchId) {
      loadDispatches();
      setTimeout(loadDispatches, 500);
    }
  }, [searchParams]);

  // (legacy ?assignZone= is now replaced by /api/dispatch/assign — see Map page)

  const handleOptimize = async () => {
    setIsOptimizing(true);
    try {
      await toast.promise(
        fetchRouteData(),
        {
          loading: 'OR-Tools is recalculating optimal route…',
          success: (s: any) =>
            s.savedKm > 0
              ? `Optimized · saved ${s.savedKm} km / ${s.savedFuelL} L vs. naive route (${s.savedPct}%)`
              : `Route already optimal · ${s.distance}, ${s.fuel}`,
          error: 'Optimization failed.',
        }
      );
    } catch (e) {
      // toast already shown
    } finally {
      setIsOptimizing(false);
    }
  };

  const truck = localTrucks.find(t => t.id === selectedTruck) ?? localTrucks[0] ?? { id: '', type: '', capacity: 1, load: 0 };
  const loadPct = Math.round((truck.load / truck.capacity) * 100);

  const [showTodayOnly, setShowTodayOnly] = useState(false);
  const visibleTrucks = showTodayOnly ? localTrucks.filter(t => t.scheduledToday) : localTrucks;
  const trucksScheduledToday = localTrucks.filter(t => t.scheduledToday).length;

  return (
    <div className="min-h-screen bg-gray-50">
      <Header title="Fleet Scheduling & Smart Routing" subtitle="AI-optimized collection routes for Austin dropoff sites" />
      <main className="pt-16 p-6">
        <div className="grid grid-cols-1 xl:grid-cols-3 gap-5 h-[calc(100vh-96px)]">

          {/* Truck Fleet Sidebar */}
          <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-5 flex flex-col overflow-hidden">
            <div className="flex items-center justify-between mb-3 flex-shrink-0">
              <div>
                <h2 className="text-sm font-bold text-gray-800">Vehicle Fleet</h2>
                <p className="text-[10px] text-gray-500">{trucksScheduledToday} scheduled today · {localTrucks.length} total</p>
              </div>
              <button
                onClick={() => setShowTodayOnly(!showTodayOnly)}
                className={`text-[10px] font-semibold px-2 py-1 rounded-full transition ${
                  showTodayOnly ? 'bg-blue-700 text-white' : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
                }`}
              >
                {showTodayOnly ? 'Today only' : 'All days'}
              </button>
            </div>
            <div className="space-y-2.5 overflow-y-auto flex-1 pr-1">
              {visibleTrucks.map((t) => {
                const pct = Math.round((t.load / t.capacity) * 100);
                const active = t.id === selectedTruck;
                const dimmed = !t.scheduledToday;
                return (
                  <button
                    key={t.id}
                    onClick={() => setSelectedTruck(t.id)}
                    className={`w-full text-left rounded-xl border p-3 transition-all hover:shadow-md ${
                      active ? 'border-blue-400 bg-blue-50 shadow-md' : 'border-gray-100 hover:border-blue-200'
                    } ${dimmed ? 'opacity-60' : ''}`}
                  >
                    <div className="flex items-start justify-between mb-2">
                      <div className="min-w-0">
                        <p className="text-xs font-bold text-gray-800 truncate">{t.id}</p>
                        <p className="text-[10px] text-gray-500">{t.type}</p>
                      </div>
                      <span className={`text-[10px] font-semibold px-2 py-0.5 rounded-full whitespace-nowrap ${statusStyles[t.status] ?? 'bg-gray-100 text-gray-600'}`}>
                        {statusLabel(t.status)}
                      </span>
                    </div>
                    <div className="flex items-center gap-1.5 mb-2">
                      <span className="text-[9px] font-semibold bg-purple-50 text-purple-700 rounded-full px-1.5 py-0.5">
                        {t.district ?? '—'}
                      </span>
                      <span className={`text-[9px] font-semibold rounded-full px-1.5 py-0.5 ${
                        t.scheduledToday ? 'bg-green-50 text-green-700' : 'bg-gray-100 text-gray-500'
                      }`}>
                        {t.garbDay ?? 'no day'}
                      </span>
                    </div>
                    <div className="space-y-0.5">
                      <div className="flex justify-between text-[10px] text-gray-500">
                        <span>Capacity</span>
                        <span className="font-medium text-gray-700">{t.load}/{t.capacity} T</span>
                      </div>
                      <div className="w-full h-1.5 bg-gray-100 rounded-full overflow-hidden">
                        <div
                          className={`h-full rounded-full transition-all ${pct > 70 ? 'bg-red-400' : pct > 40 ? 'bg-yellow-400' : 'bg-green-400'}`}
                          style={{ width: `${Math.min(pct, 100)}%` }}
                        />
                      </div>
                    </div>
                  </button>
                );
              })}
            </div>
          </div>

          {/* Route Details */}
          <div className="xl:col-span-2 space-y-4 flex flex-col overflow-hidden">

            {/* Header Card */}
            <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-4 flex-shrink-0">
              <div className="flex items-center justify-between mb-3">
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 bg-blue-700 rounded-lg flex items-center justify-center">
                    <Truck size={18} className="text-white" />
                  </div>
                  <div>
                    <h2 className="text-sm font-bold text-gray-900">{truck.id} — {truck.type}</h2>
                    <p className="text-xs text-gray-500">AI-Optimized Route · Austin · {new Date(selectedDate + 'T00:00:00').toLocaleDateString('en-US', { weekday: 'short', year: 'numeric', month: 'long', day: 'numeric' })}</p>
                  </div>
                </div>
                <button 
                  onClick={handleOptimize}
                  disabled={isOptimizing}
                  className={`flex items-center gap-2 text-white text-xs font-semibold px-4 py-2 rounded-lg transition-colors shadow ${
                    isOptimizing ? 'bg-blue-400 cursor-not-allowed' : 'bg-blue-700 hover:bg-blue-800'
                  }`}
                >
                  {isOptimizing ? <Loader2 size={13} className="animate-spin" /> : <Zap size={13} />}
                  {isOptimizing ? 'Optimizing...' : 'Optimize Route'}
                </button>
              </div>
              {/* Metrics */}
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                {[
                  { icon: Route, label: 'Est. Distance', value: summary.distance },
                  { icon: Fuel, label: 'Est. Fuel', value: summary.fuel },
                  { icon: Clock, label: 'Est. Time', value: summary.time },
                  {
                    icon: Truck,
                    label: `Stops · ${summary.stops ?? 0}`,
                    value: summary.tourLoad !== undefined && summary.capacity !== undefined
                      ? `${summary.tourLoad}/${summary.capacity} T`
                      : (truck.load !== undefined ? `${truck.load}/${truck.capacity} T` : '—'),
                  },
                ].map(({ icon: Icon, label, value }) => (
                  <div key={label} className="bg-gray-50 rounded-lg p-2.5 flex items-center gap-2.5 border border-gray-100">
                    <Icon size={14} className="text-blue-600 flex-shrink-0" />
                    <div className="min-w-0">
                      <p className="text-[10px] text-gray-500 truncate">{label}</p>
                      <p className="text-sm font-bold text-gray-800 truncate">{value}</p>
                    </div>
                  </div>
                ))}
              </div>
              {summary.targetDistricts && summary.targetDistricts.length > 0 && (
                <div className="mt-3 flex items-center gap-2 flex-wrap">
                  <span className="text-[10px] text-gray-500 uppercase tracking-wide font-semibold">Tour:</span>
                  <span className="text-[10px] text-gray-600">Depot</span>
                  {summary.targetDistricts.map((d, i) => (
                    <span key={`${d}-${i}`} className="flex items-center gap-1">
                      <span className="text-gray-400">→</span>
                      <span className="text-[10px] font-semibold bg-purple-50 text-purple-700 rounded-full px-1.5 py-0.5">{d}</span>
                    </span>
                  ))}
                  <span className="text-gray-400">→</span>
                  <span className="text-[10px] text-gray-600">Landfill</span>
                </div>
              )}
            </div>

            {/* Timeline */}
            <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-5 flex-1 overflow-y-auto">
              <h3 className="text-sm font-bold text-gray-800 mb-4">Optimized Route Timeline</h3>
              <div className="relative">
                <div className="timeline-line" />
                <div className="space-y-5">
                  {routeTimeline.map((step, idx) => {
                    const s = stepStyles[step.type] ?? defaultStepStyle;
                    return (
                      <div key={step.step} className="flex items-start gap-4 pl-1">
                        <div className={`relative z-10 w-10 h-10 rounded-full bg-white shadow flex items-center justify-center text-lg flex-shrink-0 ${s.ring}`}>
                          {step.type === 'end' ? <CheckCircle2 size={18} className="text-gray-400" /> : s.icon}
                        </div>
                        <div className={`flex-1 rounded-xl border p-3.5 transition-all hover:shadow-sm ${
                          step.type === 'high' ? 'border-red-200 bg-red-50' :
                          step.type === 'start' || step.type === 'end' ? 'border-blue-100 bg-blue-50' :
                          'border-gray-100 bg-white'
                        }`}>
                          <div className="flex items-center justify-between mb-1">
                            <p className="text-sm font-bold text-gray-800">{step.location}</p>
                            {step.priority && (
                              <span className="text-xs font-bold bg-red-500 text-white px-2 py-0.5 rounded-full">
                                Priority #{step.priority}
                              </span>
                            )}
                          </div>
                          <p className="text-xs text-gray-500">{step.note}</p>
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>

              {/* Efficiency Note */}
              <div className="mt-5 flex items-center gap-3 bg-green-50 border border-green-200 rounded-xl p-3.5">
                <div className="w-8 h-8 bg-green-500 rounded-full flex items-center justify-center flex-shrink-0">
                  <Zap size={14} className="text-white" />
                </div>
                <div>
                  <p className="text-xs font-bold text-green-800">Smart Routing Efficiency Gain</p>
                  <p className="text-xs text-green-700">
                    Saved <span className="font-bold">{summary.savedKm ?? 0} km</span> vs. naive depot-to-all route ({summary.savedPct ?? 0}%). Fuel saving: <span className="font-bold">{summary.savedFuelL ?? 0} L</span>.
                    {summary.tripsAvoided !== undefined && (
                      <> · <span className="font-bold">{summary.tripsAvoided} trips avoided</span> (only {summary.mustCollect}/{summary.totalZones} zones need collection today).</>
                    )}
                  </p>
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Smart Dispatch Plan */}
        {plan && plan.plan && plan.plan.length > 0 && (
          <div className="mt-5 bg-white rounded-xl shadow-sm border border-gray-100 p-5">
            <div className="flex items-center justify-between mb-4 flex-wrap gap-3">
              <div className="min-w-0">
                <h3 className="text-sm font-bold text-gray-800">Smart Dispatch Plan</h3>
                <p className="text-xs text-gray-500">
                  Greedy nearest-neighbor matching · {plan.plan.length} zones × {plan.plan.length} trucks ·
                  smart {plan.smart_km} km vs naive {plan.naive_km} km · saves <span className="font-semibold text-green-700">{plan.saved_km} km / {plan.saved_fuel_l} L ({plan.saved_pct}%)</span>
                </p>
              </div>
              <button
                onClick={handleAutoAssign}
                disabled={autoAssigning}
                className={`flex items-center gap-2 text-xs font-semibold px-4 py-2 rounded-lg shadow transition ${
                  autoAssigning ? 'bg-blue-400 text-white cursor-not-allowed' : 'bg-blue-700 hover:bg-blue-800 text-white'
                }`}
              >
                {autoAssigning ? <Loader2 size={13} className="animate-spin" /> : <Zap size={13} />}
                {autoAssigning ? 'Dispatching…' : 'Auto-Dispatch All'}
              </button>
            </div>
            <div className="overflow-x-auto">
              <table className="w-full text-xs">
                <thead>
                  <tr className="border-b border-gray-100 text-[10px] uppercase tracking-wide text-gray-500">
                    <th className="text-left pb-2 pr-3 font-semibold">Zone</th>
                    <th className="text-left pb-2 pr-3 font-semibold">Fill</th>
                    <th className="text-left pb-2 pr-3 font-semibold">→ Truck</th>
                    <th className="text-left pb-2 pr-3 font-semibold">Home Dist.</th>
                    <th className="text-left pb-2 pr-3 font-semibold">Distance</th>
                    <th className="text-left pb-2 pr-3 font-semibold">vs Naive</th>
                    <th className="text-left pb-2 font-semibold">ETA</th>
                  </tr>
                </thead>
                <tbody>
                  {plan.plan.map((p: any) => {
                    const saved = p.naive_km - p.distance_km;
                    return (
                      <tr key={p.zone_id} className="border-b border-gray-50 hover:bg-gray-50">
                        <td className="py-2 pr-3 font-bold text-gray-800">{p.zone_name}</td>
                        <td className="py-2 pr-3">
                          <span className={`text-[10px] font-semibold rounded-full px-2 py-0.5 ${
                            p.status === 'high' ? 'bg-red-100 text-red-700' : 'bg-yellow-100 text-yellow-700'
                          }`}>{p.fill_level}% · {p.status}</span>
                        </td>
                        <td className="py-2 pr-3">
                          <span className="font-semibold text-blue-700">{p.truck_id}</span>
                          <span className="text-[10px] text-gray-500 ml-1">{p.truck_type}</span>
                        </td>
                        <td className="py-2 pr-3">
                          <span className="text-[10px] font-semibold bg-purple-50 text-purple-700 rounded-full px-1.5 py-0.5">
                            {p.truck_home_district}
                          </span>
                          {p.scheduled_today && <span className="ml-1 text-[10px] text-green-600 font-semibold">✓ today</span>}
                        </td>
                        <td className="py-2 pr-3 font-medium text-gray-800">{p.distance_km} km</td>
                        <td className="py-2 pr-3">
                          <span className={`text-[10px] font-semibold ${saved > 0 ? 'text-green-700' : 'text-gray-500'}`}>
                            {saved > 0 ? `−${saved.toFixed(1)} km` : `${(-saved).toFixed(1)} km`}
                          </span>
                        </td>
                        <td className="py-2 text-blue-700 font-medium">{p.eta_minutes} min</td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {/* Today's Dispatches (real backend log) */}
        {dispatches.length > 0 && (
          <div className="mt-5 bg-white rounded-xl shadow-sm border border-gray-100 p-5">
            <div className="flex items-center justify-between mb-3">
              <div>
                <h3 className="text-sm font-bold text-gray-800">Today's Dispatches</h3>
                <p className="text-xs text-gray-500">{dispatches.length} truck{dispatches.length === 1 ? '' : 's'} dispatched · live from /api/dispatch/today</p>
              </div>
              <span className="bg-blue-50 text-blue-700 text-xs font-semibold px-2.5 py-1 rounded-full">SQLite log</span>
            </div>
            <div className="overflow-x-auto">
              <table className="w-full text-xs">
                <thead>
                  <tr className="border-b border-gray-100 text-[10px] uppercase tracking-wide text-gray-500">
                    <th className="text-left pb-2 pr-3 font-semibold">Truck</th>
                    <th className="text-left pb-2 pr-3 font-semibold">Type</th>
                    <th className="text-left pb-2 pr-3 font-semibold">District</th>
                    <th className="text-left pb-2 pr-3 font-semibold">Zone</th>
                    <th className="text-left pb-2 pr-3 font-semibold">ETA</th>
                    <th className="text-left pb-2 pr-3 font-semibold">Mode</th>
                    <th className="text-left pb-2 pr-3 font-semibold">Status</th>
                    <th className="text-left pb-2 font-semibold">Time</th>
                  </tr>
                </thead>
                <tbody>
                  {dispatches.map((d: any) => (
                    <tr key={d.id} className="border-b border-gray-50 hover:bg-gray-50">
                      <td className="py-2 pr-3 font-bold text-gray-800">{d.truck_id}</td>
                      <td className="py-2 pr-3 text-gray-600">{d.truck_type ?? '—'}</td>
                      <td className="py-2 pr-3"><span className="text-[10px] font-semibold bg-purple-50 text-purple-700 rounded-full px-1.5 py-0.5">{d.district ?? '—'}</span></td>
                      <td className="py-2 pr-3 text-gray-600">{d.zone_id}</td>
                      <td className="py-2 pr-3 font-medium text-blue-700">{d.eta_minutes != null ? `${d.eta_minutes} min` : '—'}</td>
                      <td className="py-2 pr-3">
                        <span className={`text-[10px] font-semibold rounded-full px-2 py-0.5 ${
                          d.mode === 'emergency' ? 'bg-red-100 text-red-700' : 'bg-green-100 text-green-700'
                        }`}>{d.mode === 'emergency' ? '🚨 Emergency' : '📅 Scheduled'}</span>
                      </td>
                      <td className="py-2 pr-3"><span className="text-[10px] font-semibold bg-blue-100 text-blue-700 rounded-full px-2 py-0.5">{d.status}</span></td>
                      <td className="py-2 text-gray-500">{new Date(d.dispatched_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {/* Weekly Schedule (real GARB_DAY data from austin_routes_2015.xlsx) */}
        {weekly.days.length > 0 && (
          <div className="mt-5 bg-white rounded-xl shadow-sm border border-gray-100 p-5">
            <div className="flex items-center justify-between mb-4">
              <div>
                <h3 className="text-sm font-bold text-gray-800">Weekly Collection Schedule</h3>
                <p className="text-xs text-gray-500">Real Austin route assignments · {weekly.weekTotalRoutes ?? 0} routes · {weekly.weekTotalTons ?? 0} T predicted</p>
              </div>
              <span className="bg-blue-50 text-blue-700 text-xs font-semibold px-2.5 py-1 rounded-full">austin_routes_2015</span>
            </div>
            <div className="grid grid-cols-1 md:grid-cols-5 gap-3">
              {weekly.days.map((d) => (
                <div key={d.day} className="rounded-xl border border-gray-100 bg-gray-50 p-3">
                  <div className="flex items-center justify-between mb-2">
                    <p className="text-xs font-bold text-gray-700">{d.day}</p>
                    <span className="text-[10px] font-semibold bg-blue-100 text-blue-700 px-1.5 py-0.5 rounded-full">{d.routes} rt</span>
                  </div>
                  <p className="text-xl font-extrabold text-gray-900">{d.predicted_tons} <span className="text-xs font-medium text-gray-500">T</span></p>
                  <p className="text-[10px] text-gray-500 mb-2">predicted load</p>
                  <div className="space-y-1">
                    {d.districts.slice(0, 4).map((dist: any) => (
                      <div key={dist.district} className="flex items-center justify-between text-[10px] bg-white rounded px-1.5 py-1">
                        <span className="text-gray-700 font-medium truncate">{dist.district}</span>
                        <span className="text-gray-500 ml-1 flex-shrink-0">{dist.routes}r · {dist.predicted_tons}T</span>
                      </div>
                    ))}
                    {d.districts.length > 4 && (
                      <p className="text-[10px] text-gray-400 text-center">+{d.districts.length - 4} more</p>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}
      </main>
    </div>
  );
}

export default function RoutesPage() {
  return (
    <Suspense fallback={<div className="min-h-screen bg-gray-50 pt-32 text-center text-gray-500">Loading Fleet & Routes...</div>}>
      <RoutesContent />
    </Suspense>
  );
}
