// ─── Chennai Specific KPI Cards ───────────────────────────────────────────────
export const kpiCards = [
  {
    title: "Total Predicted Waste",
    value: "38.6 Tons",
    trend: "+9% from yesterday",
    trendDir: "up" as const,
    trendColor: "text-red-500",
    icon: "trash",
    accent: "bg-red-50 border-red-100",
  },
  {
    title: "Active Fleet",
    value: "18 / 22 Trucks",
    trend: "Status: Optimal",
    trendDir: "neutral" as const,
    trendColor: "text-blue-500",
    icon: "truck",
    accent: "bg-blue-50 border-blue-100",
  },
  {
    title: "Estimated Fuel Savings",
    value: "62 Liters",
    trend: "+7% efficiency",
    trendDir: "up" as const,
    trendColor: "text-green-600",
    icon: "fuel",
    accent: "bg-green-50 border-green-100",
  },
  {
    title: "High Priority Zones",
    value: "4 Critical",
    trend: "Requires attention",
    trendDir: "critical" as const,
    trendColor: "text-red-600",
    icon: "alert",
    accent: "bg-yellow-50 border-yellow-100",
  },
];

// ─── 7-day Waste Chart ─────────────────────────────────────────────────────────
export const wasteChartData = [
  { day: "Mon", predicted: 34.2, actual: 33.8 },
  { day: "Tue", predicted: 36.5, actual: 36.1 },
  { day: "Wed", predicted: 32.8, actual: 33.4 },
  { day: "Thu", predicted: 39.1, actual: 39.5 },
  { day: "Fri", predicted: 42.6, actual: 41.8 },
  { day: "Sat", predicted: 44.2, actual: 44.9 },
  { day: "Sun", predicted: 38.6, actual: 38.2 },
];

// ─── System Alerts ─────────────────────────────────────────────────────────────
export const systemAlerts = [
  {
    id: 1,
    icon: "🚨",
    severity: "critical" as const,
    title: "Urgent: T. Nagar Market Area",
    message: "Bin capacity > 92% (Pongal Festival Spike). Immediate pickup required.",
    time: "3 min ago",
  },
  {
    id: 2,
    icon: "⚠️",
    severity: "warning" as const,
    title: "Route Change: Mount Road Diversion",
    message: "Traffic congestion near Anna Salai; Route D updated to inner roads.",
    time: "18 min ago",
  },
  {
    id: 3,
    icon: "✅",
    severity: "success" as const,
    title: "Model Retraining Complete",
    message: "Accuracy improved to 93.6%. Chennai seasonal patterns incorporated.",
    time: "2 hrs ago",
  },
];

// ─── Chennai Zone Map Markers (approx centers for each major zone) ────────────
// Positions as percentages on the map view [lng: 80.15–80.32, lat: 12.85–13.23]
export const zones = [
  {
    id: "Z1",
    name: "Zone 1 - Tiruvottiyur",
    zoneNo: 1,
    level: 72,
    status: "medium" as const,
    reason: "Industrial Activity",
    // lat: 13.22, lng: 80.31 → map %: x=84%, y=8%
    x: 84,
    y: 8,
  },
  {
    id: "Z2",
    name: "Zone 2 - Manali",
    zoneNo: 2,
    level: 58,
    status: "medium" as const,
    reason: "Port Area Waste",
    x: 74,
    y: 15,
  },
  {
    id: "Z4",
    name: "Zone 4 - Royapuram",
    zoneNo: 4,
    level: 88,
    status: "high" as const,
    reason: "Harbour Market Spike",
    x: 78,
    y: 28,
  },
  {
    id: "Z6",
    name: "Zone 6 - Thiru Vi Ka Nagar",
    zoneNo: 6,
    level: 45,
    status: "low" as const,
    reason: "Normal Residential",
    x: 62,
    y: 32,
  },
  {
    id: "Z8",
    name: "Zone 8 - Anna Nagar",
    zoneNo: 8,
    level: 91,
    status: "high" as const,
    reason: "Weekend Commercial Peak",
    x: 46,
    y: 38,
  },
  {
    id: "Z9",
    name: "Zone 9 - Teynampet (T.Nagar)",
    zoneNo: 9,
    level: 94,
    status: "high" as const,
    reason: "Festival Shopping Surge",
    x: 55,
    y: 52,
  },
  {
    id: "Z10",
    name: "Zone 10 - Kodambakkam",
    zoneNo: 10,
    level: 66,
    status: "medium" as const,
    reason: "Film Industry Area",
    x: 38,
    y: 54,
  },
  {
    id: "Z11",
    name: "Zone 11 - Valasaravakkam",
    zoneNo: 11,
    level: 38,
    status: "low" as const,
    reason: "Low Weekend Activity",
    x: 25,
    y: 56,
  },
  {
    id: "Z13",
    name: "Zone 13 - Adyar",
    zoneNo: 13,
    level: 85,
    status: "high" as const,
    reason: "Coastal Tourism Waste",
    x: 60,
    y: 72,
  },
  {
    id: "Z15",
    name: "Zone 15 - Sholinganallur",
    zoneNo: 15,
    level: 42,
    status: "low" as const,
    reason: "IT Corridor Weekend",
    x: 70,
    y: 88,
  },
];

// ─── Truck Fleet (CMWSSB / GCC fleet) ─────────────────────────────────────────
export const trucks = [
  { id: "GCC-101", type: "Heavy Compactor", capacity: 12, load: 4.8, status: "on-route" as const, route: "Route A - T.Nagar" },
  { id: "GCC-102", type: "Mini Tipper", capacity: 4, load: 0, status: "idle" as const, route: null },
  { id: "GCC-103", type: "Heavy Compactor", capacity: 12, load: 10.2, status: "returning" as const, route: "Perungudi Depot" },
  { id: "GCC-104", type: "Auto Tipper", capacity: 2, load: 1.8, status: "on-route" as const, route: "Route B - Adyar" },
  { id: "GCC-105", type: "Heavy Compactor", capacity: 12, load: 0, status: "idle" as const, route: null },
  { id: "GCC-106", type: "Mini Tipper", capacity: 4, load: 3.6, status: "on-route" as const, route: "Route C - Anna Nagar" },
];

// ─── Smart Route Timeline (T.Nagar focus area) ───────────────────────────────
export const routeTimeline = [
  { step: 1, location: "Sholinganallur Depot (Start)", type: "start" as const, note: "Departure: 05:30 AM", priority: null },
  { step: 2, location: "T. Nagar Market - Panagal Park (Zone 9)", type: "critical" as const, note: "Est. 34 bins – 94% full · Festival surge", priority: 1 },
  { step: 3, location: "Anna Nagar Tower Park Area (Zone 8)", type: "critical" as const, note: "Est. 28 bins – 91% full · Weekend peak", priority: 2 },
  { step: 4, location: "Royapuram Harbour Colony (Zone 4)", type: "critical" as const, note: "Est. 22 bins – 88% full · Market waste", priority: 3 },
  { step: 5, location: "Adyar Besant Nagar Beach (Zone 13)", type: "normal" as const, note: "Est. 18 bins – 85% full · Coastal tourism", priority: 4 },
  { step: 6, location: "Kodambakkam (Zone 10)", type: "normal" as const, note: "Est. 14 bins – 66% full · Regular pickup", priority: 5 },
  { step: 7, location: "Perungudi Land Fill / Transfer Station", type: "end" as const, note: "ETA: 11:45 AM", priority: null },
];

// ─── Fuel Chart (Analytics) ───────────────────────────────────────────────────
export const fuelChartData = [
  { week: "Week 1", traditional: 890, aiOptimized: 698 },
  { week: "Week 2", traditional: 940, aiOptimized: 731 },
  { week: "Week 3", traditional: 870, aiOptimized: 662 },
  { week: "Week 4", traditional: 1020, aiOptimized: 792 },
];

// ─── Collections Table (Chennai zones) ───────────────────────────────────────
export const collectionsData = [
  { date: "2026-03-22", zone: "Zone 9 - Teynampet", predicted: "28.4 tons", actual: "30.1 tons", error: "+6.0%" },
  { date: "2026-03-22", zone: "Zone 8 - Anna Nagar", predicted: "22.1 tons", actual: "21.4 tons", error: "-3.2%" },
  { date: "2026-03-22", zone: "Zone 4 - Royapuram", predicted: "18.6 tons", actual: "19.0 tons", error: "+2.2%" },
  { date: "2026-03-21", zone: "Zone 13 - Adyar", predicted: "15.2 tons", actual: "14.8 tons", error: "-2.6%" },
  { date: "2026-03-21", zone: "Zone 1 - Tiruvottiyur", predicted: "12.4 tons", actual: "13.1 tons", error: "+5.6%" },
  { date: "2026-03-20", zone: "Zone 10 - Kodambakkam", predicted: "10.8 tons", actual: "10.5 tons", error: "-2.8%" },
];

// ─── Analytics Top Metrics ─────────────────────────────────────────────────────
export const analyticsMetrics = [
  { label: "Model Accuracy (R² Score)", value: "0.91", sub: "Chennai seasonal pattern trained", color: "text-green-600" },
  { label: "Total Distance Reduced", value: "16%", sub: "vs. GCC traditional routing", color: "text-blue-700" },
  { label: "Cost Efficiency Improved", value: "21%", sub: "Monthly fuel + labour savings", color: "text-green-600" },
];
