import { useEffect, useRef, useState, useCallback } from 'react'
import mapboxgl from 'mapbox-gl'
import MapboxDraw from '@mapbox/mapbox-gl-draw'
import 'mapbox-gl/dist/mapbox-gl.css'
import '@mapbox/mapbox-gl-draw/dist/mapbox-gl-draw.css'
import { Loader2, AlertCircle, TrendingUp, X, GripVertical, ChevronDown, ChevronUp, Map, Satellite, Moon, Pentagon } from 'lucide-react'
import type { LocationFinderState, LayerInstance, DerivedMetricValue, TrendSummary } from './types'
import TrendIndicators from './TrendIndicators'
import MapLegend from './MapLegend'
import { analyzePolygon, PolygonAnalysisResult } from './layerService'

const MAPBOX_TOKEN = (import.meta as any).env?.VITE_MAPBOX_ACCESS_TOKEN || ''

const MAP_STYLES = {
  light: 'mapbox://styles/mapbox/light-v11',
  satellite: 'mapbox://styles/mapbox/satellite-streets-v12',
  dark: 'mapbox://styles/mapbox/dark-v11'
}

const CATEGORY_LABELS: Record<string, string> = {
  market: 'Market',
  traffic: 'Traffic', 
  economic: 'Economic',
  demographics: 'Demographics'
}

const CATEGORY_COLORS: Record<string, string> = {
  market: 'bg-violet-500',
  traffic: 'bg-blue-500',
  economic: 'bg-emerald-500', 
  demographics: 'bg-amber-500'
}

function DerivedMetricsPanel({ metrics }: { metrics: Record<string, DerivedMetricValue> }) {
  const [expanded, setExpanded] = useState(false)
  const [activeCategory, setActiveCategory] = useState<string>('market')
  
  const categorizedMetrics = Object.entries(metrics).reduce((acc, [key, metric]) => {
    const cat = metric?.category || 'market'
    if (!acc[cat]) acc[cat] = []
    acc[cat].push({ key, ...metric })
    return acc
  }, {} as Record<string, Array<DerivedMetricValue & { key: string }>>)
  
  const categories = Object.keys(categorizedMetrics)
  
  return (
    <div className="mt-2 border-t border-stone-200 pt-2">
      <button
        onClick={() => setExpanded(!expanded)}
        className="flex items-center gap-1 text-[10px] text-violet-600 hover:text-violet-700 font-medium"
      >
        {expanded ? <ChevronUp className="w-3 h-3" /> : <ChevronDown className="w-3 h-3" />}
        {expanded ? 'Hide' : 'Show'} Derived Metrics
      </button>
      
      {expanded && (
        <div className="mt-2 space-y-2">
          <div className="flex gap-1">
            {categories.map(cat => (
              <button
                key={cat}
                onClick={() => setActiveCategory(cat)}
                className={`px-2 py-0.5 text-[10px] rounded-full transition-colors ${
                  activeCategory === cat 
                    ? 'bg-violet-600 text-white' 
                    : 'bg-stone-100 text-stone-600 hover:bg-stone-200'
                }`}
              >
                {CATEGORY_LABELS[cat] || cat}
              </button>
            ))}
          </div>
          
          <div className="space-y-1.5">
            {categorizedMetrics[activeCategory]?.map(metric => (
              <div key={metric.key} className="space-y-0.5">
                <div className="flex justify-between text-[10px]">
                  <span className="text-stone-500 truncate pr-2" title={metric.description}>
                    {metric.name}
                  </span>
                  <span className="font-medium text-stone-700 flex-shrink-0">
                    {formatMetricValue(metric.key, metric.raw_value)}
                  </span>
                </div>
                <div className="h-1 bg-stone-200 rounded-full overflow-hidden">
                  <div 
                    className={`h-full rounded-full transition-all ${
                      (metric.normalized_value ?? 0) >= 70 ? 'bg-emerald-500' :
                      (metric.normalized_value ?? 0) >= 50 ? 'bg-amber-500' : 'bg-red-400'
                    }`}
                    style={{ width: `${Math.min(metric.normalized_value ?? 0, 100)}%` }}
                  />
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}

function formatMetricValue(key: string, value: number): string {
  if (key.includes('revenue') || key.includes('income') || key.includes('purchasing')) {
    if (value >= 1000000) return `$${(value / 1000000).toFixed(1)}M`
    if (value >= 1000) return `$${(value / 1000).toFixed(0)}K`
    return `$${value.toFixed(0)}`
  }
  if (key.includes('ratio')) return value.toFixed(2)
  if (key.includes('score') || key.includes('index') || key.includes('momentum')) return value.toFixed(1)
  if (key.includes('traffic') && value >= 1000) return `${(value / 1000).toFixed(0)}K`
  if (key.includes('per_capita')) return value.toFixed(2)
  return value.toFixed(1)
}

export interface PolygonData {
  type: 'Polygon'
  coordinates: [number, number][]
}

interface LocationFinderMapProps {
  state: LocationFinderState
  onLayerDataUpdate?: (layerId: string, data: any, error?: string) => void
  onCenterChange?: (center: { lat: number; lng: number; address?: string }) => void
  clickToSetEnabled?: boolean
  onClearOptimalZones?: () => void
  onPolygonChange?: (polygon: PolygonData | null) => void
}

export function LocationFinderMap({ state, onCenterChange, clickToSetEnabled = false, onClearOptimalZones, onPolygonChange }: LocationFinderMapProps) {
  const mapContainerRef = useRef<HTMLDivElement>(null)
  const mapRef = useRef<mapboxgl.Map | null>(null)
  const drawRef = useRef<MapboxDraw | null>(null)
  const centerMarkerRef = useRef<mapboxgl.Marker | null>(null)
  const popupRef = useRef<mapboxgl.Popup | null>(null)
  const [mapLoaded, setMapLoaded] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [panelPosition, setPanelPosition] = useState({ x: 16, y: 16 })
  const [isDragging, setIsDragging] = useState(false)
  const [isDrawingMode, setIsDrawingMode] = useState(false)
  const [drawnPolygon, setDrawnPolygon] = useState<PolygonData | null>(null)
  const [polygonAnalysis, setPolygonAnalysis] = useState<PolygonAnalysisResult | null>(null)
  const [isAnalyzingPolygon, setIsAnalyzingPolygon] = useState(false)
  const [polygonError, setPolygonError] = useState<string | null>(null)
  const dragStartRef = useRef<{ x: number; y: number; panelX: number; panelY: number } | null>(null)
  const [expandedZones, setExpandedZones] = useState<Set<string>>(new Set())
  const [isPanelCollapsed, setIsPanelCollapsed] = useState(false)
  const [panelSize, setPanelSize] = useState({ width: 320, height: 400 })
  const [isResizing, setIsResizing] = useState(false)
  const [mapStyle, setMapStyle] = useState<'light' | 'satellite' | 'dark'>('light')
  const resizeStartRef = useRef<{ x: number; y: number; width: number; height: number } | null>(null)
  
  const handleResizeStart = useCallback((e: React.MouseEvent) => {
    e.preventDefault()
    e.stopPropagation()
    setIsResizing(true)
    resizeStartRef.current = {
      x: e.clientX,
      y: e.clientY,
      width: panelSize.width,
      height: panelSize.height
    }
  }, [panelSize])

  useEffect(() => {
    if (!isResizing) return

    const handleMouseMove = (e: MouseEvent) => {
      if (!resizeStartRef.current) return
      const dx = resizeStartRef.current.x - e.clientX
      const dy = resizeStartRef.current.y - e.clientY
      setPanelSize({
        width: Math.max(280, Math.min(window.innerWidth * 0.9, resizeStartRef.current.width + dx)),
        height: Math.max(200, Math.min(window.innerHeight * 0.85, resizeStartRef.current.height + dy))
      })
    }

    const handleMouseUp = () => {
      setIsResizing(false)
      resizeStartRef.current = null
    }

    window.addEventListener('mousemove', handleMouseMove)
    window.addEventListener('mouseup', handleMouseUp)
    return () => {
      window.removeEventListener('mousemove', handleMouseMove)
      window.removeEventListener('mouseup', handleMouseUp)
    }
  }, [isResizing])
  
  const toggleZoneExpand = useCallback((zoneId: string) => {
    setExpandedZones(prev => {
      const next = new Set(prev)
      if (next.has(zoneId)) {
        next.delete(zoneId)
      } else {
        next.add(zoneId)
      }
      return next
    })
  }, [])

  const handleDragStart = useCallback((e: React.MouseEvent) => {
    e.preventDefault()
    setIsDragging(true)
    dragStartRef.current = {
      x: e.clientX,
      y: e.clientY,
      panelX: panelPosition.x,
      panelY: panelPosition.y
    }
  }, [panelPosition])

  useEffect(() => {
    if (!isDragging) return

    const handleMouseMove = (e: MouseEvent) => {
      if (!dragStartRef.current) return
      const dx = e.clientX - dragStartRef.current.x
      const dy = e.clientY - dragStartRef.current.y
      setPanelPosition({
        x: Math.max(0, dragStartRef.current.panelX - dx),
        y: Math.max(0, dragStartRef.current.panelY - dy)
      })
    }

    const handleMouseUp = () => {
      setIsDragging(false)
      dragStartRef.current = null
    }

    window.addEventListener('mousemove', handleMouseMove)
    window.addEventListener('mouseup', handleMouseUp)
    return () => {
      window.removeEventListener('mousemove', handleMouseMove)
      window.removeEventListener('mouseup', handleMouseUp)
    }
  }, [isDragging])

  useEffect(() => {
    if (!mapContainerRef.current || mapRef.current) return

    if (!MAPBOX_TOKEN) {
      setError('Map access token not configured')
      return
    }

    mapboxgl.accessToken = MAPBOX_TOKEN

    try {
      mapRef.current = new mapboxgl.Map({
        container: mapContainerRef.current,
        style: MAP_STYLES[mapStyle],
        center: state.center ? [state.center.lng, state.center.lat] : [-98.5795, 39.8283],
        zoom: state.center ? 12 : 4
      })

      mapRef.current.addControl(new mapboxgl.NavigationControl(), 'top-right')

      const draw = new MapboxDraw({
        displayControlsDefault: false,
        controls: {
          polygon: false,
          trash: false
        },
        defaultMode: 'simple_select',
        styles: [
          {
            'id': 'gl-draw-polygon-fill',
            'type': 'fill',
            'filter': ['all', ['==', '$type', 'Polygon']],
            'paint': {
              'fill-color': '#7c3aed',
              'fill-opacity': 0.15
            }
          },
          {
            'id': 'gl-draw-polygon-stroke',
            'type': 'line',
            'filter': ['all', ['==', '$type', 'Polygon']],
            'paint': {
              'line-color': '#7c3aed',
              'line-width': 2,
              'line-dasharray': [2, 2]
            }
          },
          {
            'id': 'gl-draw-polygon-stroke-active',
            'type': 'line',
            'filter': ['all', ['==', '$type', 'Polygon'], ['==', 'active', 'true']],
            'paint': {
              'line-color': '#5b21b6',
              'line-width': 3
            }
          },
          {
            'id': 'gl-draw-point',
            'type': 'circle',
            'filter': ['all', ['==', '$type', 'Point']],
            'paint': {
              'circle-radius': 5,
              'circle-color': '#7c3aed'
            }
          }
        ]
      })
      
      mapRef.current.addControl(draw as any, 'top-left')
      drawRef.current = draw

      mapRef.current.on('load', () => {
        setMapLoaded(true)
      })

      mapRef.current.on('error', (e) => {
        console.error('Map error:', e)
        setError('Error loading map')
      })
    } catch (err) {
      setError('Failed to initialize map')
      console.error(err)
    }

    return () => {
      if (drawRef.current && mapRef.current) {
        mapRef.current.removeControl(drawRef.current as any)
        drawRef.current = null
      }
      if (mapRef.current) {
        mapRef.current.remove()
        mapRef.current = null
      }
    }
  }, [])

  useEffect(() => {
    if (!mapRef.current || !mapLoaded) return

    if (centerMarkerRef.current) {
      centerMarkerRef.current.remove()
      centerMarkerRef.current = null
    }

    if (state.center) {
      const el = document.createElement('div')
      el.className = 'center-marker'
      el.innerHTML = `
        <div style="
          width: 20px;
          height: 20px;
          background: #7c3aed;
          border: 3px solid white;
          border-radius: 50%;
          box-shadow: 0 2px 8px rgba(0,0,0,0.3);
        "></div>
      `

      centerMarkerRef.current = new mapboxgl.Marker({ element: el })
        .setLngLat([state.center.lng, state.center.lat])
        .addTo(mapRef.current)

      mapRef.current.flyTo({
        center: [state.center.lng, state.center.lat],
        zoom: getZoomForRadius(state.radius),
        duration: 1000
      })
    }
  }, [state.center, mapLoaded])

  useEffect(() => {
    if (!mapRef.current || !mapLoaded || !drawRef.current) return
    
    const map = mapRef.current
    const draw = drawRef.current
    
    const handleDrawCreate = async (e: any) => {
      const features = e.features
      if (features && features.length > 0) {
        const polygon = features[0]
        if (polygon.geometry.type === 'Polygon') {
          const coords = polygon.geometry.coordinates[0] as [number, number][]
          const polygonData: PolygonData = {
            type: 'Polygon',
            coordinates: coords
          }
          setDrawnPolygon(polygonData)
          onPolygonChange?.(polygonData)
          setIsDrawingMode(false)
          
          setIsAnalyzingPolygon(true)
          setPolygonError(null)
          try {
            const result = await analyzePolygon({ polygon: coords })
            if (result.data) {
              setPolygonAnalysis(result.data)
            } else if (result.error) {
              setPolygonError(result.error)
              setPolygonAnalysis(null)
            }
          } catch (err) {
            console.error('Polygon analysis failed:', err)
            setPolygonError('Analysis failed')
          } finally {
            setIsAnalyzingPolygon(false)
          }
        }
      }
    }
    
    const handleDrawUpdate = async (e: any) => {
      const features = e.features
      if (features && features.length > 0) {
        const polygon = features[0]
        if (polygon.geometry.type === 'Polygon') {
          const coords = polygon.geometry.coordinates[0] as [number, number][]
          const polygonData: PolygonData = {
            type: 'Polygon',
            coordinates: coords
          }
          setDrawnPolygon(polygonData)
          onPolygonChange?.(polygonData)
          
          setIsAnalyzingPolygon(true)
          setPolygonError(null)
          try {
            const result = await analyzePolygon({ polygon: coords })
            if (result.data) {
              setPolygonAnalysis(result.data)
            } else if (result.error) {
              setPolygonError(result.error)
              setPolygonAnalysis(null)
            }
          } catch (err) {
            console.error('Polygon analysis failed:', err)
            setPolygonError('Analysis failed')
          } finally {
            setIsAnalyzingPolygon(false)
          }
        }
      }
    }
    
    const handleDrawDelete = () => {
      setDrawnPolygon(null)
      setPolygonAnalysis(null)
      onPolygonChange?.(null)
    }
    
    map.on('draw.create', handleDrawCreate)
    map.on('draw.update', handleDrawUpdate)
    map.on('draw.delete', handleDrawDelete)
    
    return () => {
      map.off('draw.create', handleDrawCreate)
      map.off('draw.update', handleDrawUpdate)
      map.off('draw.delete', handleDrawDelete)
    }
  }, [mapLoaded, onPolygonChange])
  
  const toggleDrawingMode = useCallback(() => {
    if (!drawRef.current) return
    
    if (isDrawingMode) {
      drawRef.current.changeMode('simple_select')
      setIsDrawingMode(false)
    } else {
      drawRef.current.deleteAll()
      drawRef.current.changeMode('draw_polygon')
      setIsDrawingMode(true)
      setDrawnPolygon(null)
      onPolygonChange?.(null)
    }
  }, [isDrawingMode, onPolygonChange])
  
  const clearPolygon = useCallback(() => {
    if (!drawRef.current) return
    drawRef.current.deleteAll()
    drawRef.current.changeMode('simple_select')
    setDrawnPolygon(null)
    setPolygonAnalysis(null)
    setPolygonError(null)
    setIsDrawingMode(false)
    onPolygonChange?.(null)
  }, [onPolygonChange])

  // Handle map style changes
  useEffect(() => {
    if (!mapRef.current || !mapLoaded) return
    
    const map = mapRef.current
    
    // Store current camera position
    const center = map.getCenter()
    const zoom = map.getZoom()
    const bearing = map.getBearing()
    const pitch = map.getPitch()
    
    // Capture current state for re-rendering after style change
    const currentLayers = state.layers
    const currentOptimalZones = state.optimalZones
    const currentCenter = state.center
    const currentRadius = state.radius
    
    // Change style and re-add layers after load
    map.setStyle(MAP_STYLES[mapStyle])
    
    map.once('style.load', () => {
      // Restore camera position fully
      map.setCenter(center)
      map.setZoom(zoom)
      map.setBearing(bearing)
      map.setPitch(pitch)
      
      // Re-render radius circle if we have a center
      if (currentCenter) {
        const demoLayer = currentLayers.find(l => l.type === 'demographics')
        const hasDemoLayer = !!demoLayer
        const showDemoOverlay = demoLayer?.visible && demoLayer?.data
        const demoDisplayMode = demoLayer?.config?.displayMode || 'heatmap'
        updateRadiusCircle(map, currentCenter, currentRadius, hasDemoLayer, demoLayer?.visible, showDemoOverlay, demoDisplayMode)
      }
      
      // Re-render all layers after style change
      currentLayers.forEach(layer => {
        if (layer.visible) {
          renderLayerOnMap(map, layer)
        }
      })
      
      // Re-render optimal zones if present
      if (currentOptimalZones && currentOptimalZones.length > 0) {
        renderOptimalZones(map, currentOptimalZones)
      }
    })
  }, [mapStyle])

  useEffect(() => {
    if (!mapRef.current || !mapLoaded) return
    
    const map = mapRef.current
    
    const handleClick = async (e: mapboxgl.MapMouseEvent) => {
      if (!clickToSetEnabled || !onCenterChange) return
      
      const { lng, lat } = e.lngLat
      
      let address: string | undefined
      try {
        const response = await fetch(
          `https://api.mapbox.com/geocoding/v5/mapbox.places/${lng},${lat}.json?access_token=${MAPBOX_TOKEN}&types=address,place,locality`
        )
        const data = await response.json()
        if (data.features && data.features.length > 0) {
          address = data.features[0].place_name
        }
      } catch (err) {
        console.error('Reverse geocoding failed:', err)
      }
      
      onCenterChange({ lat, lng, address })
    }
    
    map.on('click', handleClick)
    
    const canvas = map.getCanvas()
    if (canvas) {
      canvas.style.cursor = clickToSetEnabled ? 'crosshair' : ''
    }
    
    return () => {
      map.off('click', handleClick)
      const canvas = map.getCanvas()
      if (canvas) {
        canvas.style.cursor = ''
      }
    }
  }, [clickToSetEnabled, mapLoaded, onCenterChange])

  const demographicsLayer = state.layers.find(l => l.type === 'demographics')
  const showDemographicsOverlay = demographicsLayer?.visible && demographicsLayer?.data
  const hasDemographicsLayer = !!demographicsLayer
  const demographicsDisplayMode = demographicsLayer?.config?.displayMode || 'heatmap'

  useEffect(() => {
    if (!mapRef.current || !mapLoaded || !state.center) return

    const map = mapRef.current

    if (!map.isStyleLoaded()) {
      map.once('style.load', () => {
        if (mapRef.current) {
          updateRadiusCircle(mapRef.current, state.center!, state.radius, hasDemographicsLayer, demographicsLayer?.visible, showDemographicsOverlay, demographicsDisplayMode)
        }
      })
      return
    }

    updateRadiusCircle(map, state.center, state.radius, hasDemographicsLayer, demographicsLayer?.visible, showDemographicsOverlay, demographicsDisplayMode)
  }, [state.radius, state.center, mapLoaded, hasDemographicsLayer, demographicsLayer?.visible, showDemographicsOverlay, demographicsDisplayMode])

  const updateRadiusCircle = (
    map: mapboxgl.Map, 
    center: { lat: number; lng: number }, 
    radiusMiles: number, 
    hasDemographicsLayer: boolean,
    demographicsVisible?: boolean,
    hasData?: boolean,
    displayMode?: string
  ) => {
    const sourceId = 'radius-circle'
    const shouldShow = hasDemographicsLayer ? demographicsVisible : true
    
    let fillColor = '#7c3aed'
    let fillOpacity = 0.1
    let lineColor = '#7c3aed'
    let lineStyle: number[] = [2, 2]
    
    if (hasData) {
      switch (displayMode) {
        case 'heatmap':
          fillColor = '#3b82f6'
          fillOpacity = 0.25
          lineColor = '#1d4ed8'
          lineStyle = []
          break
        case 'markers':
          fillColor = '#10b981'
          fillOpacity = 0.1
          lineColor = '#059669'
          lineStyle = [4, 4]
          break
        case 'choropleth':
          fillColor = '#8b5cf6'
          fillOpacity = 0.3
          lineColor = '#6d28d9'
          lineStyle = []
          break
        default:
          fillColor = '#3b82f6'
          fillOpacity = 0.2
          lineColor = '#3b82f6'
      }
    }

    try {
      if (map.getLayer('radius-circle-fill')) {
        map.removeLayer('radius-circle-fill')
      }
      if (map.getLayer('radius-circle-outline')) {
        map.removeLayer('radius-circle-outline')
      }
      if (map.getSource(sourceId)) {
        map.removeSource(sourceId)
      }
    } catch (e) {
    }

    if (!shouldShow) {
      map.flyTo({
        center: [center.lng, center.lat],
        zoom: getZoomForRadius(radiusMiles),
        duration: 500
      })
      return
    }

    const radiusInKm = radiusMiles * 1.60934
    const circleGeoJSON = createCircleGeoJSON(center.lng, center.lat, radiusInKm)

    map.addSource(sourceId, {
      type: 'geojson',
      data: circleGeoJSON
    })

    map.addLayer({
      id: 'radius-circle-fill',
      type: 'fill',
      source: sourceId,
      paint: {
        'fill-color': fillColor,
        'fill-opacity': fillOpacity
      }
    })

    const linePaint: any = {
      'line-color': lineColor,
      'line-width': 2
    }
    if (lineStyle.length > 0) {
      linePaint['line-dasharray'] = lineStyle
    }

    map.addLayer({
      id: 'radius-circle-outline',
      type: 'line',
      source: sourceId,
      paint: linePaint
    })

    map.flyTo({
      center: [center.lng, center.lat],
      zoom: getZoomForRadius(radiusMiles),
      duration: 500
    })
  }

  const layerDataKey = state.layers
    .map(l => `${l.id}:${l.visible}:${l.data ? 'y' : 'n'}:${l.loading ? 'l' : 's'}`)
    .join(',')

  useEffect(() => {
    if (!mapRef.current || !mapLoaded) return

    state.layers.forEach(layer => {
      renderLayerOnMap(mapRef.current!, layer)
    })
  }, [layerDataKey, mapLoaded])

  useEffect(() => {
    if (!mapRef.current || !mapLoaded) return

    const map = mapRef.current
    renderOptimalZones(map, state.optimalZones || [])
  }, [state.optimalZones, mapLoaded])

  const renderOptimalZones = (map: mapboxgl.Map, zones: any[]) => {
    if (!map.isStyleLoaded()) return

    for (let i = 1; i <= 5; i++) {
      const sourceId = `optimal-zone-${i}`
      const fillId = `${sourceId}-fill`
      const outlineId = `${sourceId}-outline`
      const labelId = `${sourceId}-label`
      const labelSourceId = `${sourceId}-label-source`

      if (map.getLayer(fillId)) map.removeLayer(fillId)
      if (map.getLayer(outlineId)) map.removeLayer(outlineId)
      if (map.getLayer(labelId)) map.removeLayer(labelId)
      if (map.getSource(sourceId)) map.removeSource(sourceId)
      if (map.getSource(labelSourceId)) map.removeSource(labelSourceId)
    }

    zones.forEach((zone, index) => {
      const sourceId = `optimal-zone-${index + 1}`
      const fillId = `${sourceId}-fill`
      const outlineId = `${sourceId}-outline`
      const labelId = `${sourceId}-label`

      const radiusInKm = zone.radius_miles * 1.60934
      const circleGeoJSON = createCircleGeoJSON(zone.center_lng, zone.center_lat, radiusInKm)

      map.addSource(sourceId, {
        type: 'geojson',
        data: circleGeoJSON
      })

      const opacity = 0.3 - (index * 0.08)
      const colors = ['#8b5cf6', '#a78bfa', '#c4b5fd']
      const color = colors[index] || colors[2]

      map.addLayer({
        id: fillId,
        type: 'fill',
        source: sourceId,
        paint: {
          'fill-color': color,
          'fill-opacity': opacity
        }
      })

      map.addLayer({
        id: outlineId,
        type: 'line',
        source: sourceId,
        paint: {
          'line-color': '#7c3aed',
          'line-width': 2
        }
      })

      const labelSource = `${sourceId}-label-source`
      if (map.getSource(labelSource)) map.removeSource(labelSource)

      map.addSource(labelSource, {
        type: 'geojson',
        data: {
          type: 'FeatureCollection',
          features: [{
            type: 'Feature',
            geometry: {
              type: 'Point',
              coordinates: [zone.center_lng, zone.center_lat]
            },
            properties: {
              rank: zone.rank,
              score: zone.total_score
            }
          }]
        }
      })

      map.addLayer({
        id: labelId,
        type: 'symbol',
        source: labelSource,
        layout: {
          'text-field': ['concat', '#', ['get', 'rank'], ' (', ['get', 'score'], ')'],
          'text-size': 14,
          'text-font': ['DIN Pro Bold', 'Arial Unicode MS Bold'],
          'text-anchor': 'center'
        },
        paint: {
          'text-color': '#5b21b6',
          'text-halo-color': '#ffffff',
          'text-halo-width': 2
        }
      })
    })
  }

  const getLayerColor = (layerType: string): string => {
    switch (layerType) {
      case 'competition': return '#ef4444'
      case 'deep_clone': return '#f97316'
      case 'demographics': return '#3b82f6'
      case 'traffic': return '#22c55e'
      default: return '#7c3aed'
    }
  }

  const renderLayerOnMap = (map: mapboxgl.Map, layer: LayerInstance) => {
    if (!map.isStyleLoaded()) return
    
    const sourceId = `layer-${layer.id}`
    const pointLayerId = `${sourceId}-points`
    const fillLayerId = `${sourceId}-fill`
    const heatmapLayerId = `${sourceId}-heatmap`
    const labelsLayerId = `${sourceId}-labels`
    const layerColor = getLayerColor(layer.type)

    const existingSource = map.getSource(sourceId) as mapboxgl.GeoJSONSource | undefined

    if (!layer.visible) {
      if (map.getLayer(pointLayerId)) {
        map.setLayoutProperty(pointLayerId, 'visibility', 'none')
      }
      if (map.getLayer(fillLayerId)) {
        map.setLayoutProperty(fillLayerId, 'visibility', 'none')
      }
      if (map.getLayer(heatmapLayerId)) {
        map.setLayoutProperty(heatmapLayerId, 'visibility', 'none')
      }
      if (map.getLayer(labelsLayerId)) {
        map.setLayoutProperty(labelsLayerId, 'visibility', 'none')
      }
      return
    }

    const geoJsonData = normalizeLayerData(layer)
    
    // For drive_by_traffic, we may have road segments even without hotspot points
    const hasRoadSegments = layer.type === 'drive_by_traffic' && layer.data?.roadGeoJSON?.features?.length > 0
    
    if (!geoJsonData || geoJsonData.features.length === 0) {
      if (existingSource) {
        existingSource.setData({ type: 'FeatureCollection', features: [] })
      }
      // Don't return early if we have road segments to render
      if (!hasRoadSegments) {
        return
      }
    }

    if (existingSource) {
      if (layer.type === 'foot_traffic' || layer.type === 'drive_by_traffic') {
        if (map.getLayer(pointLayerId)) map.removeLayer(pointLayerId)
        if (map.getLayer(heatmapLayerId)) map.removeLayer(heatmapLayerId)
        if (map.getLayer(labelsLayerId)) map.removeLayer(labelsLayerId)
        
        // Use empty FeatureCollection as fallback when only roads are present
        const safeGeoJsonData = geoJsonData || { type: 'FeatureCollection' as const, features: [] }
        existingSource.setData(safeGeoJsonData)
        
        const isHotspotData = safeGeoJsonData.features[0]?.properties?.vitalityScore !== undefined
        
        if (isHotspotData) {
          map.addLayer({
            id: pointLayerId,
            type: 'circle',
            source: sourceId,
            paint: {
              'circle-radius': [
                'interpolate', ['linear'], ['coalesce', ['get', 'vitalityScore'], 50],
                0, 15, 50, 25, 100, 40
              ],
              'circle-color': [
                'interpolate', ['linear'], ['coalesce', ['get', 'vitalityScore'], 50],
                0, '#22c55e', 30, '#84cc16', 50, '#eab308', 70, '#f97316', 100, '#ef4444'
              ],
              'circle-stroke-width': 3,
              'circle-stroke-color': '#ffffff',
              'circle-opacity': 0.8,
              'circle-blur': 0.3
            }
          })
          map.addLayer({
            id: labelsLayerId,
            type: 'symbol',
            source: sourceId,
            layout: {
              'text-field': ['concat', ['to-string', ['get', 'vitalityScore']], '%'],
              'text-font': ['DIN Pro Medium', 'Arial Unicode MS Bold'],
              'text-size': 12,
              'text-allow-overlap': true
            },
            paint: {
              'text-color': '#ffffff',
              'text-halo-color': 'rgba(0,0,0,0.5)',
              'text-halo-width': 1
            }
          })
        } else {
          map.addLayer({
            id: heatmapLayerId,
            type: 'heatmap',
            source: sourceId,
            paint: {
              'heatmap-weight': ['interpolate', ['linear'], ['coalesce', ['get', 'traffic_intensity'], 50], 0, 0, 100, 1],
              'heatmap-intensity': ['interpolate', ['linear'], ['zoom'], 0, 1, 15, 3],
              'heatmap-color': ['interpolate', ['linear'], ['heatmap-density'],
                0, 'rgba(0, 0, 255, 0)', 0.1, 'rgba(65, 105, 225, 0.4)', 0.3, 'rgba(0, 255, 255, 0.5)',
                0.5, 'rgba(0, 255, 0, 0.6)', 0.7, 'rgba(255, 255, 0, 0.7)', 1, 'rgba(255, 0, 0, 0.8)'],
              'heatmap-radius': ['interpolate', ['linear'], ['zoom'], 0, 2, 15, 30],
              'heatmap-opacity': 0.7
            }
          })
          map.addLayer({
            id: pointLayerId,
            type: 'circle',
            source: sourceId,
            minzoom: 14,
            paint: {
              'circle-radius': 8,
              'circle-color': '#f59e0b',
              'circle-stroke-width': 2,
              'circle-stroke-color': '#ffffff',
              'circle-opacity': 0.9
            }
          })
        }
        
        // Render road traffic lines for drive_by_traffic (inside existing source block)
        if (layer.type === 'drive_by_traffic' && layer.data?.roadGeoJSON?.features?.length > 0) {
          const roadSourceId = `${layer.id}-roads`
          const roadLayerId = `${layer.id}-road-lines`
          const roadLabelLayerId = `${layer.id}-road-labels`
          const trendLayerId = `${layer.id}-road-trends`
          
          // Remove existing road layers
          if (map.getLayer(trendLayerId)) map.removeLayer(trendLayerId)
          if (map.getLayer(roadLabelLayerId)) map.removeLayer(roadLabelLayerId)
          if (map.getLayer(roadLayerId)) map.removeLayer(roadLayerId)
          if (map.getSource(roadSourceId)) map.removeSource(roadSourceId)
          
          // Add road segments source
          map.addSource(roadSourceId, {
            type: 'geojson',
            data: layer.data.roadGeoJSON
          })
          
          // Add road lines colored by traffic intensity (Google Maps style)
          map.addLayer({
            id: roadLayerId,
            type: 'line',
            source: roadSourceId,
            layout: {
              'line-cap': 'round',
              'line-join': 'round'
            },
            paint: {
              'line-color': ['get', 'color'],
              'line-width': [
                'interpolate',
                ['linear'],
                ['zoom'],
                10, 5,
                12, 7,
                14, 9,
                18, 12
              ],
              'line-opacity': 0.85
            }
          })
          
          // Add trend indicators along roads
          map.addLayer({
            id: roadLabelLayerId,
            type: 'symbol',
            source: roadSourceId,
            minzoom: 11,
            layout: {
              'symbol-placement': 'line-center',
              'text-field': [
                'concat',
                ['get', 'trend_icon'],
                ' ',
                ['to-string', ['abs', ['get', 'trend_percent']]],
                '%'
              ],
              'text-font': ['DIN Pro Medium', 'Arial Unicode MS Bold'],
              'text-size': 13,
              'text-allow-overlap': false,
              'text-offset': [0, -1.2]
            },
            paint: {
              'text-color': [
                'case',
                ['==', ['get', 'trend_direction'], 'up'], '#16a34a',
                ['==', ['get', 'trend_direction'], 'down'], '#dc2626',
                '#d97706'
              ],
              'text-halo-color': '#ffffff',
              'text-halo-width': 2
            }
          })
          
          // Add AADT volume label below trend
          map.addLayer({
            id: trendLayerId,
            type: 'symbol',
            source: roadSourceId,
            minzoom: 12,
            layout: {
              'symbol-placement': 'line-center',
              'text-field': ['concat', ['to-string', ['/', ['get', 'aadt'], 1000]], 'K/day'],
              'text-font': ['DIN Pro Medium', 'Arial Unicode MS Bold'],
              'text-size': 11,
              'text-allow-overlap': false,
              'text-offset': [0, 0.8]
            },
            paint: {
              'text-color': '#374151',
              'text-halo-color': '#ffffff',
              'text-halo-width': 1.5
            }
          })
          
          // Add live traffic signal indicators (growth/decline markers)
          const signalLayerId = `${layer.id}-live-signals`
          if (!map.getLayer(signalLayerId)) {
            map.addLayer({
              id: signalLayerId,
              type: 'circle',
              source: roadSourceId,
              minzoom: 13,
              filter: ['has', 'traffic_signal'],
              paint: {
                'circle-radius': 8,
                'circle-color': [
                  'case',
                  ['==', ['get', 'traffic_signal'], 'growth'], '#22c55e',
                  ['==', ['get', 'traffic_signal'], 'decline'], '#ef4444',
                  '#3b82f6'
                ],
                'circle-stroke-width': 2,
                'circle-stroke-color': '#ffffff',
                'circle-opacity': 0.9
              }
            })
          }
          
        }
        
        return
      }
      
      existingSource.setData(geoJsonData || { type: 'FeatureCollection' as const, features: [] })
      if (map.getLayer(pointLayerId)) {
        map.setLayoutProperty(pointLayerId, 'visibility', 'visible')
      }
      if (map.getLayer(fillLayerId)) {
        map.setLayoutProperty(fillLayerId, 'visibility', 'visible')
      }
      return
    }

    // Use empty FeatureCollection as fallback when only roads are present
    const safeGeoJsonData = geoJsonData || { type: 'FeatureCollection' as const, features: [] }
    map.addSource(sourceId, {
      type: 'geojson',
      data: safeGeoJsonData
    })

    // Always render road traffic lines for drive_by_traffic if roadGeoJSON is available
    if (layer.type === 'drive_by_traffic' && layer.data?.roadGeoJSON?.features?.length > 0) {
      const roadSourceId = `${layer.id}-roads`
      const roadLayerId = `${layer.id}-road-lines`
      const roadLabelLayerId = `${layer.id}-road-labels`
      const trendLayerId = `${layer.id}-road-trends`
      
      // Remove existing road layers
      if (map.getLayer(trendLayerId)) map.removeLayer(trendLayerId)
      if (map.getLayer(roadLabelLayerId)) map.removeLayer(roadLabelLayerId)
      if (map.getLayer(roadLayerId)) map.removeLayer(roadLayerId)
      if (map.getSource(roadSourceId)) map.removeSource(roadSourceId)
      
      // Add road segments source
      map.addSource(roadSourceId, {
        type: 'geojson',
        data: layer.data.roadGeoJSON
      })
      
      // Add road lines colored by traffic intensity (Google Maps style)
      map.addLayer({
        id: roadLayerId,
        type: 'line',
        source: roadSourceId,
        layout: {
          'line-cap': 'round',
          'line-join': 'round'
        },
        paint: {
          'line-color': ['get', 'color'],
          'line-width': [
            'interpolate',
            ['linear'],
            ['zoom'],
            10, 5,
            12, 7,
            14, 9,
            18, 12
          ],
          'line-opacity': 0.85
        }
      })
      
      // Add trend indicators along roads
      map.addLayer({
        id: roadLabelLayerId,
        type: 'symbol',
        source: roadSourceId,
        minzoom: 11,
        layout: {
          'symbol-placement': 'line-center',
          'text-field': [
            'concat',
            ['get', 'trend_icon'],
            ' ',
            ['to-string', ['abs', ['get', 'trend_percent']]],
            '%'
          ],
          'text-font': ['DIN Pro Medium', 'Arial Unicode MS Bold'],
          'text-size': 13,
          'text-allow-overlap': false,
          'text-offset': [0, -1.2]
        },
        paint: {
          'text-color': [
            'case',
            ['==', ['get', 'trend_direction'], 'up'], '#16a34a',
            ['==', ['get', 'trend_direction'], 'down'], '#dc2626',
            '#d97706'
          ],
          'text-halo-color': '#ffffff',
          'text-halo-width': 2
        }
      })
      
      // Add AADT volume label below trend
      map.addLayer({
        id: trendLayerId,
        type: 'symbol',
        source: roadSourceId,
        minzoom: 12,
        layout: {
          'symbol-placement': 'line-center',
          'text-field': ['concat', ['to-string', ['/', ['get', 'aadt'], 1000]], 'K/day'],
          'text-font': ['DIN Pro Medium', 'Arial Unicode MS Bold'],
          'text-size': 11,
          'text-allow-overlap': false,
          'text-offset': [0, 0.8]
        },
        paint: {
          'text-color': '#374151',
          'text-halo-color': '#ffffff',
          'text-halo-width': 1.5
        }
      })
      
    }

    if ((layer.type === 'foot_traffic' || layer.type === 'drive_by_traffic') && safeGeoJsonData.features?.length > 0) {
      const isHotspotData = safeGeoJsonData.features[0]?.properties?.vitalityScore !== undefined
      
      if (isHotspotData) {
        map.addLayer({
          id: pointLayerId,
          type: 'circle',
          source: sourceId,
          paint: {
            'circle-radius': [
              'interpolate',
              ['linear'],
              ['coalesce', ['get', 'vitalityScore'], 50],
              0, 15,
              50, 25,
              100, 40
            ],
            'circle-color': [
              'interpolate',
              ['linear'],
              ['coalesce', ['get', 'vitalityScore'], 50],
              0, '#22c55e',
              30, '#84cc16',
              50, '#eab308',
              70, '#f97316',
              100, '#ef4444'
            ],
            'circle-stroke-width': 3,
            'circle-stroke-color': '#ffffff',
            'circle-opacity': 0.8,
            'circle-blur': 0.3
          }
        })

        map.addLayer({
          id: `${sourceId}-labels`,
          type: 'symbol',
          source: sourceId,
          layout: {
            'text-field': ['concat', ['to-string', ['get', 'vitalityScore']], '%'],
            'text-font': ['DIN Pro Medium', 'Arial Unicode MS Bold'],
            'text-size': 12,
            'text-allow-overlap': true
          },
          paint: {
            'text-color': '#ffffff',
            'text-halo-color': 'rgba(0,0,0,0.5)',
            'text-halo-width': 1
          }
        })
      } else {
        map.addLayer({
          id: heatmapLayerId,
          type: 'heatmap',
          source: sourceId,
          paint: {
            'heatmap-weight': [
              'interpolate',
              ['linear'],
              ['coalesce', ['get', 'traffic_intensity'], 50],
              0, 0,
              100, 1
            ],
            'heatmap-intensity': [
              'interpolate',
              ['linear'],
              ['zoom'],
              0, 1,
              15, 3
            ],
            'heatmap-color': [
              'interpolate',
              ['linear'],
              ['heatmap-density'],
              0, 'rgba(0, 0, 255, 0)',
              0.1, 'rgba(65, 105, 225, 0.4)',
              0.3, 'rgba(0, 255, 255, 0.5)',
              0.5, 'rgba(0, 255, 0, 0.6)',
              0.7, 'rgba(255, 255, 0, 0.7)',
              1, 'rgba(255, 0, 0, 0.8)'
            ],
            'heatmap-radius': [
              'interpolate',
              ['linear'],
              ['zoom'],
              0, 2,
              15, 30
            ],
            'heatmap-opacity': 0.7
          }
        })

        map.addLayer({
          id: pointLayerId,
          type: 'circle',
          source: sourceId,
          minzoom: 14,
          paint: {
            'circle-radius': 8,
            'circle-color': '#f59e0b',
            'circle-stroke-width': 2,
            'circle-stroke-color': '#ffffff',
            'circle-opacity': 0.9
          }
        })
      }
    } else if (safeGeoJsonData.features?.[0]?.geometry?.type === 'Point') {
      map.addLayer({
        id: pointLayerId,
        type: 'circle',
        source: sourceId,
        paint: {
          'circle-radius': 10,
          'circle-color': layerColor,
          'circle-stroke-width': 3,
          'circle-stroke-color': '#ffffff'
        }
      })

      map.on('mouseenter', pointLayerId, (e) => {
        map.getCanvas().style.cursor = 'pointer'
        
        if (e.features && e.features.length > 0) {
          const feature = e.features[0]
          const props = feature.properties || {}
          const coords = (feature.geometry as any).coordinates.slice()
          
          const name = props.name || 'Unknown Business'
          const rating = props.rating ? `${props.rating}/5` : ''
          const category = props.category || ''
          const address = props.address || ''
          
          let html = `<div style="padding: 8px; max-width: 200px;">
            <div style="font-weight: 600; color: #1f2937; margin-bottom: 4px;">${name}</div>`
          if (rating) {
            html += `<div style="font-size: 12px; color: #6b7280;">Rating: ${rating}</div>`
          }
          if (category) {
            html += `<div style="font-size: 12px; color: #6b7280;">${category}</div>`
          }
          if (address) {
            html += `<div style="font-size: 11px; color: #9ca3af; margin-top: 4px;">${address}</div>`
          }
          html += '</div>'
          
          if (popupRef.current) {
            popupRef.current.remove()
          }
          
          popupRef.current = new mapboxgl.Popup({
            closeButton: false,
            closeOnClick: false,
            offset: 15
          })
            .setLngLat(coords)
            .setHTML(html)
            .addTo(map)
        }
      })

      map.on('mouseleave', pointLayerId, () => {
        map.getCanvas().style.cursor = ''
        if (popupRef.current) {
          popupRef.current.remove()
          popupRef.current = null
        }
      })
    }
  }

  const normalizeLayerData = (layer: LayerInstance): GeoJSON.FeatureCollection | null => {
    if (!layer.data) return null

    if (layer.data.type === 'FeatureCollection') {
      return layer.data as GeoJSON.FeatureCollection
    }

    if (layer.type === 'competition' && Array.isArray(layer.data)) {
      const features: GeoJSON.Feature[] = layer.data
        .filter((place: any) => place.latitude && place.longitude)
        .map((place: any) => ({
          type: 'Feature' as const,
          geometry: {
            type: 'Point' as const,
            coordinates: [place.longitude, place.latitude]
          },
          properties: {
            name: place.name || 'Unknown Business',
            rating: place.rating || 0,
            category: layer.config?.searchQuery || '',
            address: place.address || '',
            reviews: place.reviews_count || place.reviews || 0,
            layerType: 'competition'
          }
        }))
      
      return { type: 'FeatureCollection', features }
    }

    if (layer.type === 'demographics' && layer.data && state.center) {
      return {
        type: 'FeatureCollection',
        features: []
      }
    }

    if (layer.type === 'deep_clone') {
      const analysisResult = layer.config?.analysisResult
      if (analysisResult?.competitors && Array.isArray(analysisResult.competitors)) {
        const features: GeoJSON.Feature[] = analysisResult.competitors
          .filter((c: any) => c.latitude && c.longitude)
          .map((c: any) => ({
            type: 'Feature' as const,
            geometry: {
              type: 'Point' as const,
              coordinates: [c.longitude, c.latitude]
            },
            properties: {
              name: c.name || 'Competitor',
              rating: c.rating || 0,
              category: layer.config?.businessType || '',
              address: c.address || '',
              layerType: 'deep_clone'
            }
          }))
        return { type: 'FeatureCollection', features }
      }
      return { type: 'FeatureCollection', features: [] }
    }

    if (layer.data.type === 'foot_traffic' || layer.data.type === 'drive_by_traffic') {
      if (layer.data.hotspots && layer.data.hotspots.length > 0) {
        const features = layer.data.hotspots.map((hotspot: any, index: number) => ({
          type: 'Feature' as const,
          properties: {
            id: `hotspot-${index}`,
            vitalityScore: hotspot.vitalityScore,
            businessDensityScore: hotspot.businessDensityScore,
            totalLocationsSampled: hotspot.totalLocationsSampled,
            peakDay: hotspot.peakDay,
            peakHour: hotspot.peakHour,
            intensity: hotspot.intensity || hotspot.vitalityScore,
            label: `Vitality: ${hotspot.vitalityScore}`,
            avgDailyTraffic: hotspot.avgDailyTraffic,
            driveByTrafficMonthly: hotspot.driveByTrafficMonthly || 0,
            driveByTrafficDaily: hotspot.driveByTrafficDaily || 0,
            driveBySource: hotspot.driveBySource || 'unavailable'
          },
          geometry: {
            type: 'Point' as const,
            coordinates: [hotspot.lng, hotspot.lat]
          }
        }))
        return { type: 'FeatureCollection' as const, features }
      }
      if (layer.data.heatmap && layer.data.heatmap.features?.length > 0) {
        return layer.data.heatmap as GeoJSON.FeatureCollection
      }
      return { type: 'FeatureCollection', features: [] }
    }

    return null
  }

  if (error) {
    return (
      <div className="absolute inset-0 flex items-center justify-center bg-stone-100">
        <div className="text-center">
          <AlertCircle className="w-12 h-12 text-red-500 mx-auto mb-3" />
          <p className="text-stone-600">{error}</p>
        </div>
      </div>
    )
  }

  return (
    <div className="absolute inset-0">
      <div ref={mapContainerRef} className="w-full h-full" />
      {!mapLoaded && (
        <div className="absolute inset-0 flex items-center justify-center bg-stone-100/80">
          <Loader2 className="w-8 h-8 animate-spin text-violet-600" />
        </div>
      )}
      {state.layers.some(l => l.loading) && (
        <div className="absolute top-4 left-4 bg-white px-3 py-2 rounded-lg shadow-md flex items-center gap-2">
          <Loader2 className="w-4 h-4 animate-spin text-violet-600" />
          <span className="text-sm text-stone-600">Loading layer data...</span>
        </div>
      )}

      {/* Comprehensive Map Legend */}
      <MapLegend 
        layers={state.layers}
        showOptimalZones={!!(state.optimalZones && state.optimalZones.length > 0)}
        showTrends={!!(state.optimalZones && state.optimalZones.some((z: any) => z.trends))}
      />

      {/* Map Style Toggle */}
      <div className="absolute top-[120px] right-2.5 z-10 flex flex-col gap-1 bg-white rounded-lg shadow-md border border-stone-200 p-1">
        <button
          onClick={() => setMapStyle('light')}
          className={`p-1.5 rounded transition-colors ${mapStyle === 'light' ? 'bg-violet-100 text-violet-700' : 'text-stone-500 hover:bg-stone-100'}`}
          title="Light map"
        >
          <Map className="w-4 h-4" />
        </button>
        <button
          onClick={() => setMapStyle('satellite')}
          className={`p-1.5 rounded transition-colors ${mapStyle === 'satellite' ? 'bg-violet-100 text-violet-700' : 'text-stone-500 hover:bg-stone-100'}`}
          title="Satellite view"
        >
          <Satellite className="w-4 h-4" />
        </button>
        <button
          onClick={() => setMapStyle('dark')}
          className={`p-1.5 rounded transition-colors ${mapStyle === 'dark' ? 'bg-violet-100 text-violet-700' : 'text-stone-500 hover:bg-stone-100'}`}
          title="Dark map"
        >
          <Moon className="w-4 h-4" />
        </button>
      </div>

      {/* Polygon Drawing Controls */}
      <div className="absolute top-[220px] right-2.5 z-10 flex flex-col gap-1 bg-white rounded-lg shadow-md border border-stone-200 p-1">
        <button
          onClick={toggleDrawingMode}
          className={`p-1.5 rounded transition-colors ${isDrawingMode ? 'bg-violet-600 text-white' : drawnPolygon ? 'bg-violet-100 text-violet-700' : 'text-stone-500 hover:bg-stone-100'}`}
          title={isDrawingMode ? 'Cancel drawing' : drawnPolygon ? 'Redraw polygon' : 'Draw analysis area'}
        >
          <Pentagon className="w-4 h-4" />
        </button>
        {drawnPolygon && (
          <button
            onClick={clearPolygon}
            className="p-1.5 rounded transition-colors text-red-500 hover:bg-red-50"
            title="Clear polygon"
          >
            <X className="w-4 h-4" />
          </button>
        )}
      </div>
      
      {/* Drawing Mode Instructions */}
      {isDrawingMode && (
        <div className="absolute top-4 left-1/2 transform -translate-x-1/2 z-30 bg-violet-600 text-white px-4 py-2 rounded-lg shadow-lg text-sm font-medium">
          Click to place points, double-click to finish polygon
        </div>
      )}
      
      {/* Polygon Analysis Results Panel */}
      {(drawnPolygon || isAnalyzingPolygon) && (
        <div className="absolute top-4 left-4 z-20 bg-white rounded-lg shadow-lg border border-stone-200 p-3 w-72">
          <div className="flex items-center justify-between mb-2">
            <h3 className="text-sm font-semibold text-stone-800 flex items-center gap-2">
              <Pentagon className="w-4 h-4 text-violet-600" />
              Polygon Analysis
            </h3>
            <button
              onClick={clearPolygon}
              className="p-1 hover:bg-stone-100 rounded text-stone-400 hover:text-stone-600"
            >
              <X className="w-4 h-4" />
            </button>
          </div>
          
          {isAnalyzingPolygon ? (
            <div className="flex items-center gap-2 text-stone-500 text-sm py-4 justify-center">
              <Loader2 className="w-4 h-4 animate-spin" />
              Analyzing area...
            </div>
          ) : polygonError ? (
            <div className="flex items-center gap-2 text-red-500 text-sm py-4 justify-center">
              <AlertCircle className="w-4 h-4" />
              {polygonError}
            </div>
          ) : polygonAnalysis ? (
            <div className="space-y-3">
              <div className="grid grid-cols-2 gap-2 text-xs">
                <div className="bg-stone-50 rounded p-2">
                  <div className="text-stone-500">Area</div>
                  <div className="font-semibold text-stone-800">{polygonAnalysis.area_sq_miles.toFixed(2)} sq mi</div>
                </div>
                <div className="bg-violet-50 rounded p-2">
                  <div className="text-violet-600">Score</div>
                  <div className="font-semibold text-violet-800">{polygonAnalysis.overall_score}/100</div>
                </div>
              </div>
              
              {polygonAnalysis.traffic_data && polygonAnalysis.traffic_data.road_count > 0 && (
                <div className="border-t border-stone-100 pt-2">
                  <div className="text-xs font-medium text-stone-600 mb-1">Traffic Data</div>
                  <div className="grid grid-cols-2 gap-1 text-xs">
                    <div>
                      <span className="text-stone-500">Roads: </span>
                      <span className="font-medium">{polygonAnalysis.traffic_data.road_count}</span>
                    </div>
                    <div>
                      <span className="text-stone-500">Avg AADT: </span>
                      <span className="font-medium">{polygonAnalysis.traffic_data.avg_daily_traffic.toLocaleString()}</span>
                    </div>
                    <div className="col-span-2">
                      <span className="text-stone-500">Monthly Traffic: </span>
                      <span className="font-medium">{polygonAnalysis.traffic_data.monthly_traffic.toLocaleString()}</span>
                    </div>
                  </div>
                </div>
              )}
              
              {polygonAnalysis.insights && polygonAnalysis.insights.length > 0 && (
                <div className="border-t border-stone-100 pt-2">
                  <div className="text-xs font-medium text-stone-600 mb-1">Insights</div>
                  <div className="space-y-1">
                    {polygonAnalysis.insights.map((insight, i) => (
                      <div key={i} className="text-xs text-stone-600 flex items-start gap-1">
                        <span className="text-violet-500 mt-0.5">•</span>
                        <span>{insight}</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          ) : (
            <div className="text-xs text-stone-500 py-2">
              Drawing polygon on map...
            </div>
          )}
        </div>
      )}

      {/* Optimal Zones Floating Panel */}
      {(state.optimalZones && state.optimalZones.length > 0) || state.zoneSummary ? (
        <div 
          className="absolute bg-white rounded-lg shadow-lg border border-stone-200 overflow-hidden z-20 pointer-events-auto flex flex-col"
          style={{ 
            bottom: panelPosition.y, 
            right: panelPosition.x,
            width: isPanelCollapsed ? 'auto' : panelSize.width,
            height: isPanelCollapsed ? 'auto' : panelSize.height
          }}
        >
          {/* Resize handle - top-left corner */}
          {!isPanelCollapsed && (
            <div
              onMouseDown={handleResizeStart}
              className="absolute top-0 left-0 w-4 h-4 cursor-nw-resize z-30 group"
              title="Drag to resize"
            >
              <div className="absolute top-1 left-1 w-2 h-2 border-l-2 border-t-2 border-violet-400 group-hover:border-violet-600 transition-colors" />
            </div>
          )}
          
          <div 
            className={`flex items-center justify-between px-3 py-2 bg-violet-50 border-b border-violet-100 ${isDragging ? 'cursor-grabbing' : 'cursor-grab'}`}
            onMouseDown={handleDragStart}
          >
            <div className="flex items-center gap-2">
              <GripVertical className="w-4 h-4 text-violet-400" />
              <div className="w-5 h-5 rounded-full bg-violet-600 flex items-center justify-center">
                <TrendingUp className="w-3 h-3 text-white" />
              </div>
              <span className="text-sm font-medium text-violet-800 select-none">
                {state.optimalZones?.length || 0} Optimal Zones
              </span>
            </div>
            <div className="flex items-center gap-1">
              <button
                onClick={(e) => { e.stopPropagation(); setIsPanelCollapsed(!isPanelCollapsed) }}
                className="p-1 hover:bg-violet-100 rounded transition-colors"
                title={isPanelCollapsed ? "Expand" : "Collapse"}
              >
                {isPanelCollapsed ? (
                  <ChevronUp className="w-4 h-4 text-violet-600" />
                ) : (
                  <ChevronDown className="w-4 h-4 text-violet-600" />
                )}
              </button>
              <button
                onClick={(e) => { e.stopPropagation(); onClearOptimalZones?.() }}
                className="p-1 hover:bg-violet-100 rounded transition-colors"
                title="Close"
              >
                <X className="w-4 h-4 text-violet-600" />
              </button>
            </div>
          </div>
          
          {!isPanelCollapsed && (
          <div className="flex-1 overflow-y-auto p-3 space-y-2">
            {state.optimalZones?.map((zone) => {
              const isExpanded = expandedZones.has(zone.id)
              return (
                <div 
                  key={zone.id}
                  className="bg-stone-50 rounded-lg border border-stone-100 overflow-hidden transition-all"
                >
                  <button 
                    onClick={() => toggleZoneExpand(zone.id)}
                    className="w-full flex items-center gap-3 p-2.5 hover:bg-stone-100 transition-colors text-left"
                  >
                    <div className="w-7 h-7 rounded-full bg-violet-600 text-white text-sm font-bold flex items-center justify-center flex-shrink-0">
                      {zone.rank}
                    </div>
                    <div className="flex-1 min-w-0 flex items-center justify-between">
                      <span className="text-sm font-semibold text-stone-800">
                        Score: {zone.total_score}/100
                      </span>
                      <div className="flex items-center gap-2">
                        {zone.category_scores && !isExpanded && (
                          <div className="flex gap-1">
                            {Object.entries(zone.category_scores).slice(0, 3).map(([cat, score]) => (
                              <div key={cat} className="w-6 h-1.5 bg-stone-200 rounded-full overflow-hidden">
                                <div 
                                  className={`h-full rounded-full ${
                                    (score ?? 0) >= 70 ? 'bg-emerald-500' : 
                                    (score ?? 0) >= 50 ? 'bg-amber-500' : 'bg-red-400'
                                  }`}
                                  style={{ width: `${Math.min(score ?? 0, 100)}%` }}
                                />
                              </div>
                            ))}
                          </div>
                        )}
                        {isExpanded ? (
                          <ChevronUp className="w-4 h-4 text-stone-400" />
                        ) : (
                          <ChevronDown className="w-4 h-4 text-stone-400" />
                        )}
                      </div>
                    </div>
                  </button>
                  
                  {isExpanded && (
                    <div className="px-2.5 pb-2.5 pt-0">
                      {zone.metrics ? (
                        <div className="space-y-2 text-xs">
                          {zone.category_scores && (
                            <div className="flex gap-1.5 mb-2">
                              {Object.entries(zone.category_scores).map(([cat, score]) => (
                                <div key={cat} className="flex-1 text-center">
                                  <div className="text-[10px] text-stone-400 capitalize">{cat}</div>
                                  <div className="h-1.5 bg-stone-200 rounded-full overflow-hidden mt-0.5">
                                    <div 
                                      className={`h-full rounded-full transition-all ${
                                        (score ?? 0) >= 70 ? 'bg-emerald-500' : 
                                        (score ?? 0) >= 50 ? 'bg-amber-500' : 'bg-red-400'
                                      }`}
                                      style={{ width: `${Math.min(score ?? 0, 100)}%` }}
                                    />
                                  </div>
                                  <div className="text-[10px] font-medium mt-0.5">{Math.round(score ?? 0)}</div>
                                </div>
                              ))}
                            </div>
                          )}
                          <div className="grid grid-cols-2 gap-x-3 gap-y-1 text-stone-600">
                            <div className="flex justify-between">
                              <span className="text-stone-400">Population:</span>
                              <span className="font-medium">{(zone.metrics.total_population ?? 0).toLocaleString()}</span>
                            </div>
                            <div className="flex justify-between">
                              <span className="text-stone-400">Growth:</span>
                              <span className={`font-medium ${(zone.metrics.population_growth ?? 0) >= 0 ? 'text-emerald-600' : 'text-red-500'}`}>
                                {(zone.metrics.population_growth ?? 0) >= 0 ? '+' : ''}{(zone.metrics.population_growth ?? 0).toFixed(1)}%
                              </span>
                            </div>
                            <div className="flex justify-between">
                              <span className="text-stone-400">Income:</span>
                              <span className="font-medium">${(zone.metrics.median_income ?? 0).toLocaleString()}</span>
                            </div>
                            <div className="flex justify-between">
                              <span className="text-stone-400">Med. Age:</span>
                              <span className="font-medium">{(zone.metrics.median_age ?? 0).toFixed(1)}</span>
                            </div>
                            <div className="flex justify-between">
                              <span className="text-stone-400">Competitors:</span>
                              <span className={`font-medium ${(zone.metrics.total_competitors ?? 0) <= 3 ? 'text-emerald-600' : (zone.metrics.total_competitors ?? 0) >= 10 ? 'text-red-500' : 'text-stone-700'}`}>
                                {zone.metrics.total_competitors ?? 0}
                              </span>
                            </div>
                            <div className="flex justify-between">
                              <span className="text-stone-400">Foot Traffic:</span>
                              <span className="font-medium">{((zone.metrics.foot_traffic_monthly ?? 0) / 1000).toFixed(0)}K/mo</span>
                            </div>
                            <div className="col-span-2 flex justify-between">
                              <span className="text-stone-400">Drive-By Traffic:</span>
                              <span className="font-medium">{((zone.metrics.drive_by_traffic_monthly ?? 0) / 1000).toFixed(0)}K/mo</span>
                            </div>
                          </div>
                          {zone.derived_metrics?.metrics && (
                            <DerivedMetricsPanel metrics={zone.derived_metrics.metrics} />
                          )}
                          {(zone as any).trends && (
                            <TrendIndicators trends={(zone as any).trends} />
                          )}
                        </div>
                      ) : (
                        <>
                          <div className="text-xs text-stone-500 space-y-0.5">
                            {zone.insights.slice(0, 2).map((insight, i) => (
                              <div key={i} className="flex items-start gap-1">
                                <span className="text-violet-400 mt-0.5">•</span>
                                <span>{insight}</span>
                              </div>
                            ))}
                          </div>
                          {zone.scores && (
                            <div className="flex gap-2 mt-1.5 text-xs text-stone-400">
                              <span>Demo: {zone.scores.demographics}</span>
                              <span>•</span>
                              <span>Comp: {zone.scores.competition}</span>
                              <span>•</span>
                              <span>Mkt: {zone.scores.market_signals}</span>
                            </div>
                          )}
                        </>
                      )}
                    </div>
                  )}
                </div>
              )
            })}
            
            {state.zoneSummary && (
              <div className="pt-2 border-t border-stone-100">
                <p className="text-xs text-stone-500">{state.zoneSummary}</p>
              </div>
            )}
          </div>
          )}
        </div>
      ) : null}
    </div>
  )
}

function getZoomForRadius(radiusMiles: number): number {
  if (radiusMiles <= 0.25) return 15
  if (radiusMiles <= 0.5) return 14
  if (radiusMiles <= 1) return 13
  if (radiusMiles <= 2) return 12
  if (radiusMiles <= 5) return 11
  return 10
}

function createCircleGeoJSON(lng: number, lat: number, radiusKm: number): GeoJSON.Feature {
  const points = 64
  const coords: [number, number][] = []

  for (let i = 0; i < points; i++) {
    const angle = (i / points) * 2 * Math.PI
    const dx = radiusKm * Math.cos(angle)
    const dy = radiusKm * Math.sin(angle)

    const deltaLng = dx / (111.32 * Math.cos((lat * Math.PI) / 180))
    const deltaLat = dy / 110.574

    coords.push([lng + deltaLng, lat + deltaLat])
  }
  coords.push(coords[0])

  return {
    type: 'Feature',
    properties: {},
    geometry: {
      type: 'Polygon',
      coordinates: [coords]
    }
  }
}
