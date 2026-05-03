'use client';

import { MapContainer, TileLayer, GeoJSON, Tooltip, ZoomControl } from 'react-leaflet';
import 'leaflet/dist/leaflet.css';
import { useEffect, useState } from 'react';
import type { FeatureCollection, Feature } from 'geojson';

interface ZoneData {
  id: string;
  name: string;
  zoneNo: number;
  level: number;
  status: 'high' | 'medium' | 'low';
  reason: string;
}

interface MapProps {
  zones: ZoneData[];
  selectedZone: string | null;
  onSelectZone: (id: string | null) => void;
}

const statusColors = {
  high: '#ef4444', // red-500
  medium: '#eab308',   // yellow-500
  low: '#22c55e',      // green-500
};

export default function AustinMapLeaflet({ zones, selectedZone, onSelectZone }: MapProps) {
  const [geoData, setGeoData] = useState<FeatureCollection | null>(null);

  useEffect(() => {
    fetch('/austin_route_polygons.geojson')
      .then((res) => res.json())
      .then((data) => setGeoData(data))
      .catch((err) => console.error('Error loading route polygons:', err));
  }, []);

  if (!geoData) return null;

  const mapCenter: [number, number] = [30.2672, -97.7431];

  const districtIdFromName = (name?: string | null) => {
    if (!name) return null;
    const m = name.match(/(\d+)/);
    return m ? `D${m[1]}` : null;
  };

  const onEachFeature = (feature: Feature, layer: any) => {
    const districtName: string | undefined = feature.properties?.district;
    const routeId: string = feature.properties?.route_id ?? 'Unknown';
    const garbDay: string = feature.properties?.garb_day ?? '';
    const opType: string = feature.properties?.op_type ?? '';
    const districtId = districtIdFromName(districtName);

    layer.on({
      click: () => {
        if (districtId) onSelectZone(selectedZone === districtId ? null : districtId);
      },
    });

    layer.bindTooltip(
      () => {
        const zoneData = districtId ? zones.find(z => z.id === districtId) : undefined;
        const header = zoneData ? `${zoneData.name}` : (districtName ?? 'Route');
        const status = zoneData ? `Level: ${zoneData.level}%` : '';
        const dot = zoneData ? `<span class="w-2 h-2 rounded-full" style="background-color: ${statusColors[zoneData.status]}"></span>` : '';
        return `
          <div class="font-sans">
            <p class="font-bold text-sm mb-0.5">${header}</p>
            <p class="text-[10px] text-gray-500 mb-1">Route ${routeId} · ${opType} · ${garbDay}</p>
            <div class="flex items-center gap-2 mb-1">${dot}<span class="text-xs font-semibold">${status}</span></div>
            ${zoneData ? `<p class="text-[10px] text-gray-500 max-w-[170px] leading-tight">${zoneData.reason}</p>` : ''}
          </div>
        `;
      },
      { direction: 'top', offset: [0, -10], opacity: 1 }
    );
  };

  const styleFeature = (feature: Feature) => {
    const districtName: string | undefined = feature.properties?.district;
    const districtId = districtIdFromName(districtName);
    const zoneData = districtId ? zones.find(z => z.id === districtId) : undefined;
    const isSelected = selectedZone === districtId;

    let fillColor = '#64748b';
    if (zoneData) fillColor = statusColors[zoneData.status];

    return {
      fillColor,
      weight: isSelected ? 2.5 : 0.8,
      opacity: 1,
      color: isSelected ? '#ffffff' : '#1e293b',
      fillOpacity: isSelected ? 0.85 : 0.55,
    };
  };

  return (
    <MapContainer 
      center={mapCenter} 
      zoom={11} 
      style={{ height: '100%', width: '100%', background: '#0f2744' }}
      zoomControl={false}
      attributionControl={false}
    >
      <TileLayer
        url="https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png"
      />
      <ZoomControl position="bottomright" />

      <GeoJSON
        key={selectedZone || 'default'} // Force re-render on selection
        data={geoData}
        style={styleFeature}
        onEachFeature={onEachFeature}
      />
    </MapContainer>
  );
}
