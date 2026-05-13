import { useEffect, useRef, useState, useCallback, Component, ReactNode } from 'react';
import mapboxgl from 'mapbox-gl';
import 'mapbox-gl/dist/mapbox-gl.css';

interface ErrorBoundaryState {
  hasError: boolean;
  error?: Error;
}

class MapErrorBoundary extends Component<{ children: ReactNode; fallback?: ReactNode }, ErrorBoundaryState> {
  constructor(props: { children: ReactNode; fallback?: ReactNode }) {
    super(props);
    this.state = { hasError: false };
  }

  static getDerivedStateFromError(error: Error): ErrorBoundaryState {
    return { hasError: true, error };
  }

  render() {
    if (this.state.hasError) {
      return this.props.fallback || (
        <div className="w-full h-[500px] bg-stone-800 rounded-lg flex items-center justify-center border border-stone-700">
          <div className="text-center p-6">
            <div className="text-4xl mb-4">🗺️</div>
            <p className="text-stone-300 mb-2">Map temporarily unavailable</p>
            <p className="text-sm text-stone-500">Geographic data is displayed in the sections below</p>
          </div>
        </div>
      );
    }
    return this.props.children;
  }
}

interface GeoJSONFeature {
  type: 'Feature';
  id?: string;
  geometry: GeoJSON.Geometry;
  properties: {
    layer: string;
    [key: string]: any;
  };
}

interface GeoJSONCollection {
  type: 'FeatureCollection';
  features: GeoJSONFeature[];
}

interface MapMetadata {
  opportunity_id: number;
  category: string;
  center: { lat: number; lng: number };
  bounds: { radius_miles: number };
  signal_count: number;
  has_demographics: boolean;
}

interface LayerConfig {
  service_area: {
    type: string;
    visible: boolean;
    label: string;
    style?: {
      fillColor: string;
      fillOpacity: number;
      strokeColor: string;
      strokeWidth: number;
    };
  };
  opportunity_center: {
    type: string;
    visible: boolean;
    label: string;
  };
  heatmap: {
    type: string;
    visible: boolean;
    label: string;
    radius?: number;
    blur?: number;
  };
  growth_trajectory: {
    type: string;
    visible: boolean;
    label: string;
  };
  migration_flow?: {
    type: string;
    visible: boolean;
    label: string;
    animated?: boolean;
    style?: {
      inboundColor: string;
      outboundColor: string;
    };
  };
}

interface MapDataResponse {
  geojson: GeoJSONCollection;
  metadata: MapMetadata;
  layer_config: LayerConfig;
}

interface LayerVisibility {
  service_area: boolean;
  heatmap: boolean;
  growth_trajectory: boolean;
  opportunity_center: boolean;
  migration_flow: boolean;
}

type MapTier = 'free' | 'pro' | 'business' | 'enterprise';

interface OpportunityMapProps {
  opportunityId: number;
  height?: string;
  showControls?: boolean;
  initialZoom?: number;
  className?: string;
  tier?: MapTier;
  lazyLoad?: boolean;
}

const GROWTH_COLORS: Record<string, string> = {
  booming: '#22c55e',
  growing: '#84cc16',
  stable: '#facc15',
  declining: '#ef4444',
  unknown: '#6b7280'
};

const _GROWTH_ICONS: Record<string, string> = {
  booming: '🚀',
  growing: '📈',
  stable: '➡️',
  declining: '📉',
  unknown: '❓'
};
void _GROWTH_ICONS;

export default function OpportunityMap({
  opportunityId,
  height = '500px',
  showControls = true,
  initialZoom = 10,
  className = '',
  tier = 'business',
  lazyLoad = false
}: OpportunityMapProps) {
  const mapContainer = useRef<HTMLDivElement>(null);
  const map = useRef<mapboxgl.Map | null>(null);
  const [mapData, setMapData] = useState<MapDataResponse | null>(null);
  const [loading, setLoading] = useState(!lazyLoad);
  const [error, setError] = useState<string | null>(null);
  const [isMapActivated, setIsMapActivated] = useState(!lazyLoad);
  const [layerVisibility, setLayerVisibility] = useState<LayerVisibility>({
    service_area: true,
    heatmap: tier === 'business' || tier === 'enterprise',
    growth_trajectory: tier === 'business' || tier === 'enterprise',
    opportunity_center: true,
    migration_flow: tier === 'enterprise'
  });
  const animationRef = useRef<number | null>(null);

  const fetchMapData = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const response = await fetch(`/api/v1/map/opportunity/${opportunityId}`);
      if (!response.ok) {
        throw new Error(`Failed to fetch map data: ${response.status}`);
      }
      const data: MapDataResponse = await response.json();
      setMapData(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load map data');
    } finally {
      setLoading(false);
    }
  }, [opportunityId]);

  useEffect(() => {
    if (!isMapActivated || tier === 'free') return;
    if (map.current) {
      map.current.remove();
      map.current = null;
    }
    fetchMapData();
  }, [fetchMapData, isMapActivated, tier]);

  useEffect(() => {
    if (!mapContainer.current || !mapData) return;
    
    if (map.current) {
      map.current.remove();
      map.current = null;
    }

    const accessToken = (import.meta as any).env?.VITE_MAPBOX_ACCESS_TOKEN;
    if (!accessToken) {
      setError('Mapbox access token not configured');
      return;
    }

    mapboxgl.accessToken = accessToken;

    if (!mapboxgl.supported()) {
      setError('WebGL is not supported in this browser — map unavailable');
      return;
    }

    const { center } = mapData.metadata;

    let mapInstance: mapboxgl.Map;
    try {
      mapInstance = new mapboxgl.Map({
        container: mapContainer.current,
        style: 'mapbox://styles/mapbox/dark-v11',
        center: [center.lng, center.lat],
        zoom: initialZoom,
        attributionControl: false
      });
    } catch (webglErr) {
      setError('Map could not be initialised — WebGL unavailable');
      return;
    }
    map.current = mapInstance;

    map.current.addControl(new mapboxgl.NavigationControl(), 'top-right');
    map.current.addControl(new mapboxgl.AttributionControl({ compact: true }), 'bottom-right');

    map.current.on('load', () => {
      if (!map.current || !mapData) return;

      const serviceAreaFeatures = mapData.geojson.features.filter(
        f => f.properties.layer === 'service_area'
      );
      if (serviceAreaFeatures.length > 0) {
        map.current.addSource('service-area', {
          type: 'geojson',
          data: {
            type: 'FeatureCollection',
            features: serviceAreaFeatures as any
          }
        });

        map.current.addLayer({
          id: 'service-area-fill',
          type: 'fill',
          source: 'service-area',
          paint: {
            'fill-color': mapData.layer_config.service_area.style?.fillColor || '#8B5CF6',
            'fill-opacity': mapData.layer_config.service_area.style?.fillOpacity || 0.15
          }
        });

        map.current.addLayer({
          id: 'service-area-outline',
          type: 'line',
          source: 'service-area',
          paint: {
            'line-color': mapData.layer_config.service_area.style?.strokeColor || '#8B5CF6',
            'line-width': mapData.layer_config.service_area.style?.strokeWidth || 2
          }
        });
      }

      const heatmapFeatures = mapData.geojson.features.filter(
        f => f.properties.layer === 'heatmap'
      );
      if (heatmapFeatures.length > 0) {
        map.current.addSource('heatmap', {
          type: 'geojson',
          data: {
            type: 'FeatureCollection',
            features: heatmapFeatures as any
          }
        });

        map.current.addLayer({
          id: 'heatmap-layer',
          type: 'heatmap',
          source: 'heatmap',
          paint: {
            'heatmap-weight': ['get', 'weight'],
            'heatmap-intensity': 1,
            'heatmap-color': [
              'interpolate',
              ['linear'],
              ['heatmap-density'],
              0, 'rgba(0,0,0,0)',
              0.2, '#7c3aed',
              0.4, '#8b5cf6',
              0.6, '#a78bfa',
              0.8, '#c4b5fd',
              1, '#ede9fe'
            ],
            'heatmap-radius': mapData.layer_config.heatmap.radius || 25,
            'heatmap-opacity': 0.8
          }
        });
      }

      const growthFeatures = mapData.geojson.features.filter(
        f => f.properties.layer === 'growth_trajectory'
      );
      if (growthFeatures.length > 0) {
        map.current.addSource('growth-trajectory', {
          type: 'geojson',
          data: {
            type: 'FeatureCollection',
            features: growthFeatures as any
          }
        });

        map.current.addLayer({
          id: 'growth-trajectory-circles',
          type: 'circle',
          source: 'growth-trajectory',
          paint: {
            'circle-radius': 12,
            'circle-color': [
              'match',
              ['get', 'growth_category'],
              'booming', GROWTH_COLORS.booming,
              'growing', GROWTH_COLORS.growing,
              'stable', GROWTH_COLORS.stable,
              'declining', GROWTH_COLORS.declining,
              GROWTH_COLORS.unknown
            ],
            'circle-stroke-width': 2,
            'circle-stroke-color': '#ffffff',
            'circle-opacity': 0.9
          }
        });

        map.current.on('click', 'growth-trajectory-circles', (e) => {
          if (!e.features?.[0]) return;
          const props = e.features[0].properties ?? {};
          const coords = (e.features[0].geometry as any).coordinates;
          const category = props.growth_category || 'unknown';
          const growthRate = props.population_growth_rate 
            ? `${(props.population_growth_rate * 100).toFixed(1)}%` 
            : 'N/A';
          
          new mapboxgl.Popup({ closeButton: true, closeOnClick: true })
            .setLngLat(coords)
            .setHTML(`
              <div style="padding: 8px; font-family: system-ui;">
                <div style="font-weight: 600; font-size: 14px; margin-bottom: 4px;">
                  ${props.city || props.geography_name || 'Unknown'}
                </div>
                <div style="display: flex; align-items: center; gap: 6px; margin-bottom: 4px;">
                  <span style="display: inline-block; width: 10px; height: 10px; border-radius: 50%; background: ${GROWTH_COLORS[category] || GROWTH_COLORS.unknown};"></span>
                  <span style="text-transform: capitalize; font-weight: 500;">${category}</span>
                </div>
                <div style="font-size: 12px; color: #666;">
                  Growth Rate: ${growthRate}
                </div>
                <div style="font-size: 12px; color: #666;">
                  Score: ${props.growth_score?.toFixed(0) || 'N/A'}
                </div>
              </div>
            `)
            .addTo(map.current!);
        });

        map.current.on('mouseenter', 'growth-trajectory-circles', () => {
          if (map.current) map.current.getCanvas().style.cursor = 'pointer';
        });
        map.current.on('mouseleave', 'growth-trajectory-circles', () => {
          if (map.current) map.current.getCanvas().style.cursor = '';
        });
      }

      const centerFeatures = mapData.geojson.features.filter(
        f => f.properties.layer === 'opportunity_center'
      );
      if (centerFeatures.length > 0) {
        map.current.addSource('opportunity-center', {
          type: 'geojson',
          data: {
            type: 'FeatureCollection',
            features: centerFeatures as any
          }
        });

        map.current.addLayer({
          id: 'opportunity-center-marker',
          type: 'circle',
          source: 'opportunity-center',
          paint: {
            'circle-radius': 10,
            'circle-color': '#8B5CF6',
            'circle-stroke-width': 3,
            'circle-stroke-color': '#ffffff'
          }
        });

        map.current.addLayer({
          id: 'opportunity-center-pulse',
          type: 'circle',
          source: 'opportunity-center',
          paint: {
            'circle-radius': 20,
            'circle-color': '#8B5CF6',
            'circle-opacity': 0.3,
            'circle-stroke-width': 0
          }
        });
      }

      const migrationFeatures = mapData.geojson.features.filter(
        f => f.properties.layer === 'migration_flow'
      );
      if (migrationFeatures.length > 0) {
        map.current.addSource('migration-flows', {
          type: 'geojson',
          data: {
            type: 'FeatureCollection',
            features: migrationFeatures as any
          },
          lineMetrics: true
        });

        map.current.addLayer({
          id: 'migration-flow-lines',
          type: 'line',
          source: 'migration-flows',
          paint: {
            'line-color': [
              'match',
              ['get', 'flow_direction'],
              'inbound', '#22C55E',
              'outbound', '#EF4444',
              '#6B7280'
            ],
            'line-width': ['coalesce', ['get', 'line_width'], 3],
            'line-opacity': 0.7,
            'line-dasharray': [2, 2]
          },
          layout: {
            'line-cap': 'round',
            'line-join': 'round'
          }
        });

        map.current.addLayer({
          id: 'migration-flow-arrows',
          type: 'circle',
          source: 'migration-flows',
          paint: {
            'circle-radius': 4,
            'circle-color': [
              'match',
              ['get', 'flow_direction'],
              'inbound', '#22C55E',
              'outbound', '#EF4444',
              '#6B7280'
            ],
            'circle-stroke-width': 1,
            'circle-stroke-color': '#ffffff',
            'circle-opacity': 0.9
          }
        });

        let step = 0;
        const animateDash = () => {
          step = (step + 1) % 100;
          const dashPhase = step / 25;
          if (map.current?.getLayer('migration-flow-lines')) {
            map.current.setPaintProperty('migration-flow-lines', 'line-dasharray', [
              2 + Math.sin(dashPhase) * 0.3,
              2 + Math.cos(dashPhase) * 0.3
            ]);
          }
          animationRef.current = requestAnimationFrame(animateDash);
        };
        animateDash();
        
        map.current.on('click', 'migration-flow-lines', (e) => {
          if (!e.features || e.features.length === 0) return;
          const feature = e.features[0];
          const props = feature.properties;
          
          new mapboxgl.Popup()
            .setLngLat(e.lngLat)
            .setHTML(`
              <div class="text-sm p-2">
                <div class="font-semibold mb-1">${props?.flow_direction === 'inbound' ? '⬅️ Inbound' : '➡️ Outbound'}</div>
                <div class="text-gray-300">${props?.origin_name} → ${props?.destination_name}</div>
                <div class="text-gray-400 mt-1">${props?.flow_count?.toLocaleString() || 0} people/year</div>
                ${props?.year ? `<div class="text-gray-500 text-xs">Year: ${props.year}</div>` : ''}
              </div>
            `)
            .addTo(map.current!);
        });

        map.current.on('mouseenter', 'migration-flow-lines', () => {
          if (map.current) map.current.getCanvas().style.cursor = 'pointer';
        });

        map.current.on('mouseleave', 'migration-flow-lines', () => {
          if (map.current) map.current.getCanvas().style.cursor = '';
        });
      }
    });

    return () => {
      if (animationRef.current) {
        cancelAnimationFrame(animationRef.current);
        animationRef.current = null;
      }
      if (map.current) {
        map.current.remove();
        map.current = null;
      }
    };
  }, [mapData, initialZoom]);

  useEffect(() => {
    if (!map.current || !map.current.isStyleLoaded()) return;

    const layerMappings: Record<keyof LayerVisibility, string[]> = {
      service_area: ['service-area-fill', 'service-area-outline'],
      heatmap: ['heatmap-layer'],
      growth_trajectory: ['growth-trajectory-circles'],
      opportunity_center: ['opportunity-center-marker', 'opportunity-center-pulse'],
      migration_flow: ['migration-flow-lines', 'migration-flow-arrows']
    };

    Object.entries(layerVisibility).forEach(([key, visible]) => {
      const layers = layerMappings[key as keyof LayerVisibility];
      layers.forEach(layerId => {
        if (map.current?.getLayer(layerId)) {
          map.current.setLayoutProperty(layerId, 'visibility', visible ? 'visible' : 'none');
        }
      });
    });
  }, [layerVisibility]);

  const toggleLayer = (layer: keyof LayerVisibility) => {
    setLayerVisibility(prev => ({
      ...prev,
      [layer]: !prev[layer]
    }));
  };

  const activateMap = () => {
    setIsMapActivated(true);
    setLoading(true);
  };

  if (!isMapActivated && lazyLoad) {
    return (
      <div 
        className={`bg-gradient-to-br from-stone-800 to-stone-900 rounded-lg flex items-center justify-center border border-stone-700 cursor-pointer hover:border-violet-500/50 transition-all group ${className}`}
        style={{ height }}
        onClick={activateMap}
      >
        <div className="text-center p-6">
          <div className="text-5xl mb-4 group-hover:scale-110 transition-transform">🗺️</div>
          <p className="text-stone-300 mb-2 font-medium">Interactive Map</p>
          <p className="text-sm text-stone-500 mb-4">Service areas, growth trends, and migration flows</p>
          <button
            className="px-4 py-2 bg-violet-600 hover:bg-violet-500 text-white rounded-lg text-sm font-medium transition-colors inline-flex items-center gap-2"
          >
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M14.752 11.168l-3.197-2.132A1 1 0 0010 9.87v4.263a1 1 0 001.555.832l3.197-2.132a1 1 0 000-1.664z" />
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            Load Interactive Map
          </button>
          {tier === 'free' && (
            <p className="text-xs text-stone-600 mt-3">Upgrade to Pro for enhanced map features</p>
          )}
        </div>
      </div>
    );
  }

  if (tier === 'free') {
    return (
      <div 
        className={`bg-stone-800 rounded-lg overflow-hidden border border-stone-700 relative ${className}`}
        style={{ height }}
      >
        <div className="absolute inset-0 flex items-center justify-center bg-gradient-to-br from-blue-900/30 to-violet-900/30">
          <div className="text-center p-6">
            <div className="text-4xl mb-4">📍</div>
            <p className="text-stone-300 mb-2 font-medium">Service Area Preview</p>
            <p className="text-sm text-stone-500 mb-4">Upgrade to Pro for interactive maps</p>
            <div className="inline-flex items-center gap-2 text-xs text-stone-400">
              <span className="w-3 h-3 rounded-full bg-violet-500"></span>
              Opportunity Location
            </div>
          </div>
        </div>
      </div>
    );
  }

  if (loading) {
    return (
      <div 
        className={`bg-stone-800 rounded-lg flex items-center justify-center border border-stone-700 ${className}`}
        style={{ height }}
      >
        <div className="text-center">
          <div className="animate-spin w-8 h-8 border-2 border-violet-500 border-t-transparent rounded-full mx-auto mb-3"></div>
          <p className="text-stone-400">Loading map data...</p>
        </div>
      </div>
    );
  }

  if (error || !mapData) {
    return (
      <div 
        className={`bg-stone-800 rounded-lg flex items-center justify-center border border-stone-700 ${className}`}
        style={{ height }}
      >
        <div className="text-center p-6">
          <div className="text-4xl mb-4">🗺️</div>
          <p className="text-stone-300 mb-2">{error || 'Map data unavailable'}</p>
          <button
            onClick={fetchMapData}
            className="text-sm text-violet-400 hover:text-violet-300 underline"
          >
            Retry
          </button>
        </div>
      </div>
    );
  }

  return (
    <MapErrorBoundary>
      <div className={`relative ${className}`}>
        <div 
          ref={mapContainer} 
          style={{ height }} 
          className="rounded-lg overflow-hidden border border-stone-700"
        />
        
        {showControls && (
          <div className="absolute top-4 left-4 bg-stone-900/90 backdrop-blur-sm rounded-lg p-3 border border-stone-700">
            <div className="text-xs text-stone-400 uppercase tracking-wide mb-2">Layers</div>
            <div className="space-y-2">
              <label className="flex items-center gap-2 cursor-pointer">
                <input
                  type="checkbox"
                  checked={layerVisibility.service_area}
                  onChange={() => toggleLayer('service_area')}
                  className="w-4 h-4 rounded border-stone-600 bg-stone-700 text-violet-500 focus:ring-violet-500"
                />
                <span className="text-sm text-stone-300">Service Area</span>
              </label>
              <label className="flex items-center gap-2 cursor-pointer">
                <input
                  type="checkbox"
                  checked={layerVisibility.heatmap}
                  onChange={() => toggleLayer('heatmap')}
                  className="w-4 h-4 rounded border-stone-600 bg-stone-700 text-violet-500 focus:ring-violet-500"
                />
                <span className="text-sm text-stone-300">Signal Heatmap</span>
              </label>
              <label className="flex items-center gap-2 cursor-pointer">
                <input
                  type="checkbox"
                  checked={layerVisibility.growth_trajectory}
                  onChange={() => toggleLayer('growth_trajectory')}
                  className="w-4 h-4 rounded border-stone-600 bg-stone-700 text-violet-500 focus:ring-violet-500"
                />
                <span className="text-sm text-stone-300">Growth Trajectory</span>
              </label>
              <label className="flex items-center gap-2 cursor-pointer">
                <input
                  type="checkbox"
                  checked={layerVisibility.opportunity_center}
                  onChange={() => toggleLayer('opportunity_center')}
                  className="w-4 h-4 rounded border-stone-600 bg-stone-700 text-violet-500 focus:ring-violet-500"
                />
                <span className="text-sm text-stone-300">Opportunity Center</span>
              </label>
              <label className="flex items-center gap-2 cursor-pointer">
                <input
                  type="checkbox"
                  checked={layerVisibility.migration_flow}
                  onChange={() => toggleLayer('migration_flow')}
                  className="w-4 h-4 rounded border-stone-600 bg-stone-700 text-violet-500 focus:ring-violet-500"
                />
                <span className="text-sm text-stone-300">Migration Flows</span>
              </label>
            </div>
          </div>
        )}

        <div className="absolute bottom-4 left-4 bg-stone-900/90 backdrop-blur-sm rounded-lg p-2 border border-stone-700">
          <div className="flex items-center gap-3 text-xs">
            <div className="flex items-center gap-1">
              <div className="w-3 h-3 rounded-full bg-green-500"></div>
              <span className="text-stone-400">Booming</span>
            </div>
            <div className="flex items-center gap-1">
              <div className="w-3 h-3 rounded-full bg-lime-500"></div>
              <span className="text-stone-400">Growing</span>
            </div>
            <div className="flex items-center gap-1">
              <div className="w-3 h-3 rounded-full bg-yellow-400"></div>
              <span className="text-stone-400">Stable</span>
            </div>
            <div className="flex items-center gap-1">
              <div className="w-3 h-3 rounded-full bg-red-500"></div>
              <span className="text-stone-400">Declining</span>
            </div>
          </div>
        </div>

        <div className="absolute top-4 right-16 bg-stone-900/90 backdrop-blur-sm rounded-lg px-3 py-2 border border-stone-700">
          <div className="text-xs text-stone-400">
            <span className="text-violet-400 font-medium">{mapData.metadata.signal_count}</span> signals detected
          </div>
        </div>
      </div>
    </MapErrorBoundary>
  );
}
