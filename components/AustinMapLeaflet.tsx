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
  status: 'critical' | 'medium' | 'low';
  reason: string;
}

interface MapProps {
  zones: ZoneData[];
  selectedZone: string | null;
  onSelectZone: (id: string | null) => void;
}

const statusColors = {
  critical: '#ef4444', // red-500
  medium: '#eab308',   // yellow-500
  low: '#22c55e',      // green-500
};

export default function AustinMapLeaflet({ zones, selectedZone, onSelectZone }: MapProps) {
  const [geoData, setGeoData] = useState<FeatureCollection | null>(null);

  useEffect(() => {
    fetch('/AUSTIN.geojson')
      .then((res) => res.json())
      .then((data) => setGeoData(data))
      .catch((err) => console.error('Error loading Austin GeoJSON:', err));
  }, []);

  if (!geoData) return null;

  // Austin coordinates
  const mapCenter: [number, number] = [30.2672, -97.7431];

  const onEachFeature = (feature: Feature, layer: any) => {
    // Determine the neighborhood index to map it to one of the 10 Districts
    // A real mapping file would do this via properties, but we link deterministically
    const featureName = feature.properties?.name || feature.properties?.sec_neigh || 'Unknown';
    // Let's generate a quick deterministic district 1-10 mapping from the feature name length
    const districtNo = (featureName.length % 10) + 1;
    const districtId = `D${districtNo}`;
    
    layer.on({
      click: () => {
        onSelectZone(selectedZone === districtId ? null : districtId);
      },
    });

    layer.bindTooltip(
      () => {
        const zoneData = zones.find(z => z.id === districtId);
        if (!zoneData) return featureName;
        
        return `
          <div class="font-sans">
            <p class="font-bold text-sm mb-1">${zoneData.name} (${featureName})</p>
            <div class="flex items-center gap-2 mb-1">
              <span class="w-2 h-2 rounded-full" style="background-color: ${statusColors[zoneData.status]}"></span>
              <span class="text-xs font-semibold">Level: ${zoneData.level}%</span>
            </div>
            <p class="text-[10px] text-gray-500 max-w-[150px] leading-tight">
              ${zoneData.reason}
            </p>
          </div>
        `;
      },
      { direction: 'top', offset: [0, -10], opacity: 1 }
    );
  };

  const styleFeature = (feature: Feature) => {
    const featureName = feature.properties?.name || feature.properties?.sec_neigh || 'Unknown';
    const districtNo = (featureName.length % 10) + 1;
    const districtId = `D${districtNo}`;
    
    const zoneData = zones.find(z => z.id === districtId);
    const isSelected = selectedZone === districtId;
    
    let fillColor = '#1e3a8a'; // default blue
    if (zoneData) {
      fillColor = statusColors[zoneData.status];
    }

    return {
      fillColor,
      weight: isSelected ? 3 : 1,
      opacity: 1,
      color: isSelected ? '#ffffff' : '#475569',
      fillOpacity: isSelected ? 0.9 : 0.6,
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
