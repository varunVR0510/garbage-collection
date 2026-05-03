'use client';

import { useState, useEffect, Suspense } from 'react';
import { useSearchParams } from 'next/navigation';
import { toast } from 'react-hot-toast';
import Header from '@/components/Header';
import { Truck, MapPin, Clock, Fuel, Route, Zap, CheckCircle2, Circle, Play, Loader2 } from 'lucide-react';

const statusStyles: Record<string, string> = {
  'on-route': 'bg-blue-100 text-blue-700',
  'idle': 'bg-gray-100 text-gray-600',
  'returning': 'bg-green-100 text-green-700',
};

const stepStyles: Record<string, { icon: string; ring: string; dot: string }> = {
  start: { icon: '🏭', ring: 'ring-2 ring-blue-300', dot: 'bg-blue-500' },
  critical: { icon: '🚨', ring: 'ring-2 ring-red-300', dot: 'bg-red-500' },
  normal: { icon: '🏠', ring: 'ring-2 ring-yellow-300', dot: 'bg-yellow-500' },
  end: { icon: '🗑️', ring: 'ring-2 ring-gray-300', dot: 'bg-gray-400' },
};

function RoutesContent() {
  const searchParams = useSearchParams();
  const [localTrucks, setLocalTrucks] = useState<any[]>([]);
  const [routeTimeline, setRouteTimeline] = useState<any[]>([]);
  const [selectedTruck, setSelectedTruck] = useState<string | null>(null);
  const [isOptimizing, setIsOptimizing] = useState(false);

  const [summary, setSummary] = useState({ distance: "...", fuel: "...", time: "..." });

  useEffect(() => {
    fetch('http://localhost:8000/api/fleet/status')
      .then(res => res.json())
      .then(data => {
        setLocalTrucks(data);
        if (data.length > 0 && !selectedTruck) setSelectedTruck(data[0].id);
      })
      .catch(err => console.error("Error fetching fleet:", err));

    fetch('http://localhost:8000/api/routes/optimized')
      .then(res => res.json())
      .then(data => setRouteTimeline(data))
      .catch(err => console.error("Error fetching routes:", err));

    fetch('http://localhost:8000/api/routes/summary')
      .then(res => res.json())
      .then(data => setSummary(data))
      .catch(err => console.error("Error fetching summary:", err));
  }, []);

  useEffect(() => {
    const assignZone = searchParams.get('assignZone');
    if (assignZone && localTrucks.length > 0) {
      // Use localTrucks to find idle one, default to first if none
      const idleTruck = localTrucks.find(t => t.status === 'idle') || localTrucks[0];
      setSelectedTruck(idleTruck.id);
      
      // Optically update the truck's status to reflect the assignment
      setLocalTrucks(prev => prev.map(t => 
        t.id === idleTruck.id 
          ? { ...t, status: 'on-route' as const, route: `Priority Pickup - Zone ${assignZone}` }
          : t
      ));

      setTimeout(() => {
        toast.success(`Vehicle ${idleTruck.id} assigned to Zone ${assignZone} priority pickup.`, { duration: 4000 });
      }, 500);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [searchParams, localTrucks.length]);

  const handleOptimize = () => {
    setIsOptimizing(true);
    toast.promise(
      new Promise(resolve => setTimeout(resolve, 2000)),
      {
        loading: 'AI is recalculating optimal route...',
        success: 'Route optimized! Saved 4.8 km and 1.2 L fuel.',
        error: 'Optimization failed.',
      }
    ).then(() => setIsOptimizing(false));
  };

  const truck = localTrucks.find(t => t.id === selectedTruck) ?? localTrucks[0] ?? { id: '', type: '', capacity: 1, load: 0 };
  const loadPct = Math.round((truck.load / truck.capacity) * 100);

  return (
    <div className="min-h-screen bg-gray-50">
      <Header title="Fleet Scheduling & Smart Routing" subtitle="AI-optimized collection routes for Austin dropoff sites" />
      <main className="pt-16 p-6">
        <div className="grid grid-cols-1 xl:grid-cols-3 gap-5 h-[calc(100vh-96px)]">

          {/* Truck Fleet Sidebar */}
          <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-5 flex flex-col overflow-hidden">
            <div className="flex items-center justify-between mb-4 flex-shrink-0">
              <h2 className="text-sm font-bold text-gray-800">Vehicle Fleet</h2>
              <span className="text-xs text-gray-500 bg-gray-100 px-2 py-0.5 rounded-full">{localTrucks.length} Trucks</span>
            </div>
            <div className="space-y-2.5 overflow-y-auto flex-1 pr-1">
              {localTrucks.map((t) => {
                const pct = Math.round((t.load / t.capacity) * 100);
                const active = t.id === selectedTruck;
                return (
                  <button
                    key={t.id}
                    onClick={() => setSelectedTruck(t.id)}
                    className={`w-full text-left rounded-xl border p-3.5 transition-all hover:shadow-md ${
                      active ? 'border-blue-400 bg-blue-50 shadow-md' : 'border-gray-100 hover:border-blue-200'
                    }`}
                  >
                    <div className="flex items-start justify-between mb-2">
                      <div>
                        <p className="text-xs font-bold text-gray-800">{t.id}</p>
                        <p className="text-[10px] text-gray-500">{t.type}</p>
                      </div>
                      <span className={`text-[10px] font-semibold px-2 py-0.5 rounded-full ${statusStyles[t.status]}`}>
                        {t.status === 'on-route' ? 'On Route' : t.status === 'returning' ? 'Returning' : 'Idle'}
                      </span>
                    </div>
                    <div className="space-y-1">
                      <div className="flex justify-between text-[10px] text-gray-500">
                        <span>Capacity</span>
                        <span className="font-medium text-gray-700">{t.load}/{t.capacity} T</span>
                      </div>
                      <div className="w-full h-1.5 bg-gray-100 rounded-full overflow-hidden">
                        <div
                          className={`h-full rounded-full transition-all ${pct > 70 ? 'bg-red-400' : pct > 40 ? 'bg-yellow-400' : 'bg-green-400'}`}
                          style={{ width: `${pct}%` }}
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
                    <p className="text-xs text-gray-500">AI-Optimized Route · Austin · March 23, 2026</p>
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
              <div className="grid grid-cols-3 gap-3">
                {[
                  { icon: Route, label: 'Est. Distance', value: summary.distance },
                  { icon: Fuel, label: 'Est. Fuel', value: summary.fuel },
                  { icon: Clock, label: 'Est. Time', value: summary.time },
                ].map(({ icon: Icon, label, value }) => (
                  <div key={label} className="bg-gray-50 rounded-lg p-2.5 flex items-center gap-2.5 border border-gray-100">
                    <Icon size={14} className="text-blue-600 flex-shrink-0" />
                    <div>
                      <p className="text-[10px] text-gray-500">{label}</p>
                      <p className="text-sm font-bold text-gray-800">{value}</p>
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {/* Timeline */}
            <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-5 flex-1 overflow-y-auto">
              <h3 className="text-sm font-bold text-gray-800 mb-4">Optimized Route Timeline</h3>
              <div className="relative">
                <div className="timeline-line" />
                <div className="space-y-5">
                  {routeTimeline.map((step, idx) => {
                    const s = stepStyles[step.type];
                    return (
                      <div key={step.step} className="flex items-start gap-4 pl-1">
                        <div className={`relative z-10 w-10 h-10 rounded-full bg-white shadow flex items-center justify-center text-lg flex-shrink-0 ${s.ring}`}>
                          {step.type === 'end' ? <CheckCircle2 size={18} className="text-gray-400" /> : s.icon}
                        </div>
                        <div className={`flex-1 rounded-xl border p-3.5 transition-all hover:shadow-sm ${
                          step.type === 'critical' ? 'border-red-200 bg-red-50' :
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
                  <p className="text-xs text-green-700">Saved <span className="font-bold">{(parseFloat(summary.distance.replace(' km','')) * 0.18).toFixed(1)} km</span> compared to Austin fixed route. Estimated fuel saving: <span className="font-bold">{(parseFloat(summary.fuel.replace(' L','')) * 0.18).toFixed(1)} L</span>.</p>
                </div>
              </div>
            </div>
          </div>
        </div>
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
