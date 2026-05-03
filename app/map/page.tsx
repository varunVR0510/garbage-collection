'use client';

import { useEffect, useState } from 'react';
import dynamic from 'next/dynamic';
import Header from '@/components/Header';

import type { ComponentType } from 'react';

interface MapProps {
  zones: typeof import('@/lib/mockData').zones;
  selectedZone: string | null;
  onSelectZone: (id: string | null) => void;
}

// Dynamically import the map to avoid SSR issues with Leaflet
const AustinMapLeaflet = dynamic(
  () => import('@/components/AustinMapLeaflet') as Promise<{ default: ComponentType<MapProps> }>,
  {
  ssr: false,
  loading: () => (
    <div className="w-full h-full bg-[#0f2744] flex items-center justify-center rounded-xl">
      <div className="text-center text-white">
        <div className="w-10 h-10 border-4 border-blue-400 border-t-transparent rounded-full animate-spin mx-auto mb-3" />
        <p className="text-sm font-medium">Loading Austin Map…</p>
        <p className="text-xs text-blue-300 mt-1">Rendering dropoff sites</p>
      </div>
    </div>
  ),
});

const statusColors: Record<string, { badge: string; text: string; border: string; dot: string }> = {
  critical: { badge: 'bg-red-100 text-red-700', text: 'text-red-600', border: 'border-red-200 hover:border-red-400', dot: 'bg-red-500' },
  medium:   { badge: 'bg-yellow-100 text-yellow-700', text: 'text-yellow-600', border: 'border-yellow-200 hover:border-yellow-400', dot: 'bg-yellow-400' },
  low:      { badge: 'bg-green-100 text-green-700', text: 'text-green-600', border: 'border-green-200 hover:border-green-400', dot: 'bg-green-500' },
};
const levelLabel: Record<string, string> = { critical: 'High', medium: 'Medium', low: 'Low' };

import { useRouter } from 'next/navigation';

export default function MapPage() {
  const [selectedZone, setSelectedZone] = useState<string | null>(null);
  const [zones, setZones] = useState<any[]>([]);
  const router = useRouter();

  useEffect(() => {
    fetch('http://localhost:8000/api/zones')
      .then(res => res.json())
      .then(data => setZones(data))
      .catch(err => console.error("Error fetching zones:", err));
  }, []);

  const sorted = [...zones].sort((a, b) => b.level - a.level);

  return (
    <div className="min-h-screen bg-gray-50">
      <Header title="Austin Waste Prediction Map" subtitle="Real-time Austin dropoff site waste levels · AI-predicted collection priorities" />
      <main className="pt-16 p-6">
        <div className="grid grid-cols-1 xl:grid-cols-3 gap-5" style={{ height: 'calc(100vh - 96px)' }}>

          {/* Real Leaflet Map */}
          <div className="xl:col-span-2 rounded-xl shadow-sm border border-gray-100 overflow-hidden" style={{ minHeight: 480 }}>
            <AustinMapLeaflet selectedZone={selectedZone} onSelectZone={setSelectedZone} zones={zones} />
          </div>

          {/* Priority List */}
          <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-5 flex flex-col overflow-hidden">
            <div className="flex items-center justify-between mb-4 flex-shrink-0">
              <h2 className="text-sm font-bold text-gray-800">Site Priority Ranking</h2>
              <span className="bg-blue-50 text-blue-700 text-xs font-semibold px-2 py-0.5 rounded-full">
                {zones.length} Zones
              </span>
            </div>
            <div className="space-y-3 overflow-y-auto flex-1 pr-1">
              {sorted.map((zone, i) => {
                const c = statusColors[zone.status];
                const isSelected = selectedZone === zone.id;
                return (
                  <button
                    key={zone.id}
                    onClick={() => setSelectedZone(zone.id === selectedZone ? null : zone.id)}
                    className={`w-full text-left rounded-xl border p-3.5 transition-all hover:shadow-md ${c.border} ${
                      isSelected ? 'shadow-md ring-2 ring-blue-300' : ''
                    } bg-white`}
                  >
                    <div className="flex items-start justify-between mb-2">
                      <div className="flex items-center gap-2">
                        <span className="w-6 h-6 rounded-full bg-gray-100 flex items-center justify-center text-xs font-bold text-gray-500 flex-shrink-0">
                          #{i + 1}
                        </span>
                        <p className="text-xs font-semibold text-gray-800 leading-tight text-left">{zone.name}</p>
                      </div>
                    </div>
                    <div className="flex items-center justify-between mb-2.5">
                      <span className={`inline-flex items-center gap-1 text-xs font-bold px-2.5 py-1 rounded-full ${c.badge}`}>
                        <span className={`w-1.5 h-1.5 rounded-full ${c.dot}`}/>
                        {levelLabel[zone.status]} · {zone.level}%
                      </span>
                      <div className="flex-1 mx-3">
                        <div className="w-full h-1.5 bg-gray-100 rounded-full overflow-hidden">
                          <div
                            className={`h-full rounded-full ${c.dot}`}
                            style={{ width: `${zone.level}%` }}
                          />
                        </div>
                      </div>
                    </div>
                    <p className="text-[10px] text-gray-500 mb-2.5 bg-gray-50 rounded px-2 py-1 text-left">
                      🤖 AI Insight: <span className="font-medium text-gray-700">{zone.reason}</span>
                    </p>
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        router.push(`/routes?assignZone=${zone.id}`);
                      }}
                      className="w-full text-xs font-semibold bg-blue-700 hover:bg-blue-800 text-white rounded-lg py-1.5 transition-colors shadow-sm"
                    >
                      Assign GCC Vehicle
                    </button>
                  </button>
                );
              })}
            </div>
          </div>
        </div>
      </main>
    </div>
  );
}
