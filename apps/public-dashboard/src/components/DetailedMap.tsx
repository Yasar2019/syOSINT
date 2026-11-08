'use client';

import { useEffect, useRef, useState, type ReactNode } from 'react';
import type { Map as VectorMap, Marker as VectorMarker } from 'maplibre-gl';
import type { PublicIncident } from '@syosint/schemas';
import type { Dictionary, Locale } from '../i18n/types';
import { isMarkerEligible } from '../lib/map';

const SYRIA_BOUNDS: [[number, number], [number, number]] = [[35, 32], [42.5, 37.5]];
const STYLES = { dark: 'https://tiles.openfreemap.org/styles/dark', streets: 'https://tiles.openfreemap.org/styles/liberty' };
type Status = 'loading' | 'ready' | 'unavailable';

export function DetailedMap({ incidents, locale, dictionary, onSelect, fallback }: {
  incidents: PublicIncident[]; locale: Locale; dictionary: Dictionary;
  onSelect: (id: string) => void; fallback: ReactNode;
}) {
  const host = useRef<HTMLDivElement>(null);
  const map = useRef<VectorMap | null>(null);
  const [status, setStatus] = useState<Status>('loading');
  const [attempt, setAttempt] = useState(0);
  const [style, setStyle] = useState<keyof typeof STYLES>('dark');
  const select = useRef(onSelect);
  const messages = dictionary.map;
  useEffect(() => { select.current = onSelect; }, [onSelect]);

  useEffect(() => {
    let cancelled = false;
    let instance: VectorMap | null = null;
    let observer: ResizeObserver | undefined;
    let timer: ReturnType<typeof setTimeout> | undefined;
    const fail = () => {
      if (cancelled) return;
      if (timer) clearTimeout(timer);
      setStatus('unavailable');
      observer?.disconnect();
      instance?.remove();
      instance = null;
      map.current = null;
    };
    if (!window.WebGL2RenderingContext) {
      queueMicrotask(() => { if (!cancelled) setStatus('unavailable'); });
      return () => { cancelled = true; };
    }
    void import('maplibre-gl').then(({ Map }) => {
      if (cancelled || !host.current) return;
      setStatus('loading');
      instance = new Map({
        container: host.current,
        style: STYLES[style],
        center: [38.5, 35], zoom: 5.5, minZoom: 3, maxZoom: 16,
        bounds: SYRIA_BOUNDS, fitBoundsOptions: { padding: 30 },
        renderWorldCopies: false, attributionControl: { compact: false },
        cooperativeGestures: true,
        pixelRatio: Math.min(window.devicePixelRatio || 1, 2),
      });
      map.current = instance;
      instance.on('load', () => {
        if (cancelled || !instance) return;
        if (timer) clearTimeout(timer);
        setStatus('ready');
      });
      instance.on('error', fail);
      timer = setTimeout(fail, 15000);
      if (typeof ResizeObserver !== 'undefined') {
        observer = new ResizeObserver(() => instance?.resize());
        observer.observe(host.current);
      }
    }).catch(fail);
    return () => {
      cancelled = true;
      if (timer) clearTimeout(timer);
      observer?.disconnect();
      instance?.remove();
      map.current = null;
    };
  }, [attempt, style]);

  useEffect(() => {
    let cancelled = false;
    const markers: VectorMarker[] = [];
    if (status !== 'ready' || !map.current) return;
    const instance = map.current;
    void import('maplibre-gl').then(({ Marker }) => {
      if (cancelled || map.current !== instance) return;
      for (const incident of incidents.filter(isMarkerEligible)) {
        const button = document.createElement('button');
        button.type = 'button';
        button.className = `detailed-map-marker confidence-${incident.confidence}`;
        button.setAttribute('aria-label', `${dictionary.accessibility.openIncident}: ${incident.title[locale]}; ${dictionary.status[incident.status]}; ${dictionary.confidence[incident.confidence]}`);
        button.title = `${incident.location[locale]} · ${incident.title[locale]}`;
        button.addEventListener('click', () => select.current(incident.id));
        markers.push(new Marker({ element: button }).setLngLat([incident.location.longitude!, incident.location.latitude!]).addTo(instance));
      }
    }).catch(() => { /* The accessible list remains available. */ });
    return () => { cancelled = true; markers.forEach(marker => marker.remove()); };
  }, [incidents, locale, dictionary, status, style]);

  return <div className="detailed-map" data-map-status={status}>
    <div className="map-toolbar" role="group" aria-label={messages.controls}>
      <label>{messages.style}<select value={style} onChange={event => setStyle(event.target.value as keyof typeof STYLES)}>
        <option value="dark">{messages.dark}</option><option value="streets">{messages.streets}</option>
      </select></label>
      <button type="button" disabled={status !== 'ready'} aria-label={messages.zoomIn} onClick={() => map.current?.zoomIn({ duration: 0 })}>+</button>
      <button type="button" disabled={status !== 'ready'} aria-label={messages.zoomOut} onClick={() => map.current?.zoomOut({ duration: 0 })}>−</button>
      <button type="button" disabled={status !== 'ready'} onClick={() => map.current?.fitBounds(SYRIA_BOUNDS, { padding: 30, duration: 0 })}>{messages.reset}</button>
    </div>
    <div className="detailed-map-frame">
      <div ref={host} className="vector-map-host" aria-label={messages.title} aria-hidden={status !== 'ready'} />
      {status !== 'ready' && <div className="map-overview">{fallback}</div>}
    </div>
    <p className="map-service-status" role="status">{status === 'ready' ? messages.interaction : status === 'loading' ? messages.loading : messages.unavailable}</p>
    {status === 'unavailable' && <button type="button" className="map-retry" onClick={() => setAttempt(value => value + 1)}>{messages.retry}</button>}
    <small className="map-attribution"><a href="https://openfreemap.org/" target="_blank" rel="noopener noreferrer">OpenFreeMap</a> · © <a href="https://openmaptiles.org/" target="_blank" rel="noopener noreferrer">OpenMapTiles</a> · <a href="https://www.openstreetmap.org/copyright" target="_blank" rel="noopener noreferrer">OpenStreetMap</a></small>
  </div>;
}
