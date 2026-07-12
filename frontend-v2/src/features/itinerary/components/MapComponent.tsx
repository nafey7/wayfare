import { useEffect, useRef } from 'react';
import { Box, Text } from '@mantine/core';
import { APIProvider, Map, Marker, useMap, useMapsLibrary } from '@vis.gl/react-google-maps';

export interface MapMarker {
  latitude: number;
  longitude: number;
  imageUrl?: string;
  label?: string;
}

export interface MapRoutePoint {
  latitude: number;
  longitude: number;
}

export interface MapComponentProps {
  centerLatitude: number;
  centerLongitude: number;
  zoomLevel?: number;
  markers: MapMarker[];
  /** Encoded polyline string for route display (e.g. from Directions API). */
  polyline?: string | null;
  /** Simple point-to-point route path for pages that only have coordinates. */
  routePath?: MapRoutePoint[];
}


/** Renders a route polyline from an encoded polyline string. */
function MapPolyline({ encodedPolyline }: { encodedPolyline: string }) {
  const map = useMap();
  const geometry = useMapsLibrary('geometry');
  const polylineRef = useRef<google.maps.Polyline | null>(null);

  useEffect(() => {
    if (!map || !geometry || !encodedPolyline?.trim()) return;

    try {
      const path = google.maps.geometry.encoding.decodePath(encodedPolyline);
      if (!path.length) return;

      const polyline = new google.maps.Polyline({
        path,
        geodesic: true,
        strokeColor: '#1976d2',
        strokeOpacity: 0.9,
        strokeWeight: 4,
      });
      polyline.setMap(map);
      polylineRef.current = polyline;

      const bounds = path.reduce(
        (acc, p) => (acc.extend(p), acc),
        new google.maps.LatLngBounds(),
      );
      map.fitBounds(bounds, { top: 40, right: 40, bottom: 40, left: 40 });

      return () => {
        polyline.setMap(null);
        polylineRef.current = null;
      };
    } catch {
      // Invalid encoded polyline (e.g. placeholder "abcd") – skip rendering
    }
  }, [map, geometry, encodedPolyline]);

  return null;
}

/** Renders a simple blue route between explicit map points. */
function MapRoutePath({ points }: { points: MapRoutePoint[] }) {
  const map = useMap();
  const polylineRef = useRef<google.maps.Polyline | null>(null);

  useEffect(() => {
    if (!map || points.length < 2) return;

    const path = points.map((point) => ({
      lat: point.latitude,
      lng: point.longitude,
    }));

    const polyline = new google.maps.Polyline({
      path,
      geodesic: true,
      strokeColor: '#1976d2',
      strokeOpacity: 0.9,
      strokeWeight: 4,
    });
    polyline.setMap(map);
    polylineRef.current = polyline;

    const bounds = path.reduce(
      (acc, point) => (acc.extend(point), acc),
      new google.maps.LatLngBounds(),
    );
    map.fitBounds(bounds, { top: 40, right: 40, bottom: 40, left: 40 });

    return () => {
      polyline.setMap(null);
      polylineRef.current = null;
    };
  }, [map, points]);

  return null;
}

/** Fit map to show all markers when there are multiple points and no route/polyline. */
function MapMarkersFitBounds({ markers }: { markers: MapMarker[] }) {
  const map = useMap();

  useEffect(() => {
    if (!map || markers.length < 2) return;

    const bounds = markers.reduce(
      (acc, m) => acc.extend({ lat: m.latitude, lng: m.longitude }),
      new google.maps.LatLngBounds(),
    );
    map.fitBounds(bounds, { top: 40, right: 40, bottom: 40, left: 40 });
  }, [map, markers]);

  return null;
}

function MapComponentInner({
  apiKey,
  centerLatitude,
  centerLongitude,
  zoomLevel = 10,
  markers,
  polyline,
  routePath,
}: MapComponentProps & { apiKey: string }) {
  // Filter out markers with invalid coordinates at the source so Google Maps
  // never receives non-finite lat/lng values (hotels without geocoding).
  const displayMarkers = markers.filter(
    (m) => Number.isFinite(m.latitude) && Number.isFinite(m.longitude)
  );

  return (
    <APIProvider apiKey={apiKey} libraries={['geometry']}>
      <Box
        style={{
          height: '100%',
          width: '100%',
          borderRadius: 8,
          border: '1px solid var(--mantine-color-default-border)',
          overflow: 'hidden',
        }}
      >
        <Map
          defaultCenter={{ lat: centerLatitude, lng: centerLongitude }}
          defaultZoom={zoomLevel}
          style={{ width: '100%', height: '100%' }}
          mapTypeControl
          streetViewControl
          fullscreenControl
        >
          {displayMarkers.map((m, i) => (
            <Marker
              key={`${m.latitude}-${m.longitude}-${i}`}
              position={{ lat: m.latitude, lng: m.longitude }}
              title={m.label}
            />
          ))}
          {!polyline && !routePath && displayMarkers.length >= 2 && (
            <MapMarkersFitBounds markers={displayMarkers} />
          )}
          {polyline && <MapPolyline encodedPolyline={polyline} />}
          {!polyline && routePath && <MapRoutePath points={routePath} />}
        </Map>
      </Box>
    </APIProvider>
  );
}

/**
 * Map panel – map view with markers for itinerary locations.
 * Uses Google Maps via @vis.gl/react-google-maps.
 */
export function MapComponent(props: MapComponentProps) {
  const apiKey = import.meta.env.VITE_GOOGLE_MAPS_API_KEY;

  if (!apiKey || apiKey.trim() === '') {
    return (
      <Box
        style={{
          height: '100%',
          borderRadius: 8,
          border: '1px solid var(--mantine-color-default-border)',
          backgroundColor: 'var(--mantine-color-gray-2)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          padding: 16,
        }}
      >
        <Text size="sm" c="dimmed" ta="center">
          Map view is not available (Google Maps API key not configured).
        </Text>
      </Box>
    );
  }

  return <MapComponentInner {...props} apiKey={apiKey} />;
}
