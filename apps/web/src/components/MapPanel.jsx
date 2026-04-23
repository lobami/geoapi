import { useEffect, useMemo, useRef } from 'react'
import maplibregl from 'maplibre-gl'

const EMPTY_COLLECTION = {
  type: 'FeatureCollection',
  features: [],
}

function getBounds(features) {
  const bounds = new maplibregl.LngLatBounds()
  let hasPoints = false

  for (const feature of features) {
    if (feature.geometry.type === 'Point') {
      bounds.extend(feature.geometry.coordinates)
      hasPoints = true
      continue
    }

    if (feature.geometry.type === 'Polygon') {
      for (const ring of feature.geometry.coordinates) {
        for (const coordinate of ring) {
          bounds.extend(coordinate)
          hasPoints = true
        }
      }
    }
  }

  return hasPoints ? bounds : null
}

export default function MapPanel({ interventions, areas, highlightedIds }) {
  const mapRef = useRef(null)
  const mapInstanceRef = useRef(null)
  const didFitRef = useRef(false)

  const areaGeoJson = useMemo(
    () => ({
      type: 'FeatureCollection',
      features: areas.map((area) => ({
        type: 'Feature',
        properties: {
          area_id: area.area_id,
          name: area.name,
        },
        geometry: area.geometry,
      })),
    }),
    [areas],
  )

  const pointGeoJson = useMemo(
    () => ({
      type: 'FeatureCollection',
      features: interventions.map((item) => ({
        type: 'Feature',
        properties: {
          id: item.id,
          subtype: item.subtype,
          status: item.status,
          project_id: item.project_id,
          highlight: highlightedIds.includes(item.id) ? 1 : 0,
        },
        geometry: {
          type: 'Point',
          coordinates: [item.lon, item.lat],
        },
      })),
    }),
    [highlightedIds, interventions],
  )

  useEffect(() => {
    if (!mapRef.current || mapInstanceRef.current) {
      return
    }

    const map = new maplibregl.Map({
      container: mapRef.current,
      style: 'https://basemaps.cartocdn.com/gl/positron-gl-style/style.json',
      center: [-103.39, 20.73],
      zoom: 9,
      attributionControl: false,
    })

    map.addControl(new maplibregl.NavigationControl({ visualizePitch: true }), 'top-right')
    map.addControl(new maplibregl.AttributionControl({ compact: true }))

    map.on('load', () => {
      map.addSource('areas', {
        type: 'geojson',
        data: areaGeoJson,
      })
      map.addSource('interventions', {
        type: 'geojson',
        data: pointGeoJson,
      })

      map.addLayer({
        id: 'areas-fill',
        type: 'fill',
        source: 'areas',
        paint: {
          'fill-color': '#7dbb8c',
          'fill-opacity': 0.16,
        },
      })
      map.addLayer({
        id: 'areas-line',
        type: 'line',
        source: 'areas',
        paint: {
          'line-color': '#285548',
          'line-width': 2,
        },
      })
      map.addLayer({
        id: 'interventions-circle',
        type: 'circle',
        source: 'interventions',
        paint: {
          'circle-radius': [
            'case',
            ['==', ['get', 'highlight'], 1],
            8,
            5,
          ],
          'circle-color': [
            'match',
            ['get', 'status'],
            'validated',
            '#173d34',
            'completed',
            '#5f8f6b',
            'in_progress',
            '#bc8c4a',
            '#7c7f92',
          ],
          'circle-stroke-color': '#f7f5ee',
          'circle-stroke-width': [
            'case',
            ['==', ['get', 'highlight'], 1],
            2.5,
            1.2,
          ],
          'circle-opacity': 0.92,
        },
      })
    })

    mapInstanceRef.current = map

    return () => {
      map.remove()
      mapInstanceRef.current = null
    }
  }, [areaGeoJson, pointGeoJson])

  useEffect(() => {
    const map = mapInstanceRef.current
    if (!map || !map.isStyleLoaded()) {
      return
    }

    const areaSource = map.getSource('areas')
    if (areaSource) {
      areaSource.setData(areaGeoJson)
    }
    const pointSource = map.getSource('interventions')
    if (pointSource) {
      pointSource.setData(pointGeoJson)
    }

    if (!didFitRef.current) {
      const bounds = getBounds([...areaGeoJson.features, ...pointGeoJson.features])
      if (bounds) {
        map.fitBounds(bounds, { padding: 42, duration: 900 })
        didFitRef.current = true
      }
    }
  }, [areaGeoJson, pointGeoJson])

  // Fly to highlighted results when a query returns
  useEffect(() => {
    const map = mapInstanceRef.current
    if (!map || highlightedIds.length === 0) return

    const highlighted = pointGeoJson.features.filter((f) => highlightedIds.includes(f.properties.id))
    if (highlighted.length === 0) return

    if (highlighted.length === 1) {
      const [lon, lat] = highlighted[0].geometry.coordinates
      map.flyTo({ center: [lon, lat], zoom: 10, duration: 1000 })
    } else {
      const bounds = getBounds(highlighted)
      if (bounds) map.fitBounds(bounds, { padding: 80, duration: 1000, maxZoom: 12 })
    }
  }, [highlightedIds, pointGeoJson])

  return <div className="live-map" ref={mapRef} />
}
