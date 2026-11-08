import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { afterEach, expect, it, vi } from 'vitest';
import { DetailedMap } from './DetailedMap';
import { loadPublicDataset } from '../lib/load-public-dataset';
import { en } from '../i18n/en';
const fixture = vi.hoisted(() => ({ maps: [] as Array<{ events: Record<string, () => void>; remove: ReturnType<typeof vi.fn>; zoomIn: ReturnType<typeof vi.fn>; zoomOut: ReturnType<typeof vi.fn>; fitBounds: ReturnType<typeof vi.fn>; setStyle: ReturnType<typeof vi.fn>; resize: ReturnType<typeof vi.fn> }>, markers: [] as HTMLElement[] }));
vi.mock('maplibre-gl', () => ({
  Map: class { events: Record<string,()=>void> = {}; remove=vi.fn(); zoomIn=vi.fn(); zoomOut=vi.fn(); fitBounds=vi.fn(); setStyle=vi.fn(); resize=vi.fn(); scrollZoom={disable:vi.fn(),enable:vi.fn()}; constructor(){fixture.maps.push(this)} on(name:string,cb:()=>void){this.events[name]=cb;return this} },
  Marker: class { element:HTMLElement; constructor({element}:{element:HTMLElement}){this.element=element;fixture.markers.push(element)} setLngLat(){return this} addTo(){document.body.append(this.element);return this} remove(){this.element.remove()} }
}));
afterEach(() => {cleanup(); fixture.maps.length=0; fixture.markers.length=0;vi.unstubAllGlobals()});
const props = {incidents:loadPublicDataset().incidents,locale:'en' as const,dictionary:en,onSelect:vi.fn(),fallback:<p>Bundled overview</p>};
it('keeps the overview and incident list usable when WebGL is unavailable', async () => {
 vi.stubGlobal('WebGL2RenderingContext',undefined);render(<DetailedMap {...props}/>);expect(screen.getByText('Bundled overview')).toBeTruthy();await waitFor(()=>expect(screen.getByText(/Detailed map unavailable/)).toBeTruthy());
});
it('loads lazily, updates only eligible markers, handles controls and cleans up',async()=>{
 vi.stubGlobal('WebGL2RenderingContext',class {});const selected=vi.fn();const {rerender,unmount}=render(<DetailedMap {...props} onSelect={selected}/>);
 await waitFor(()=>expect(fixture.maps.length).toBe(1));const map=fixture.maps[0];map.events.load();
 await waitFor(()=>expect(document.querySelectorAll('.detailed-map-marker').length).toBeGreaterThan(0));
 fireEvent.click(fixture.markers[0]);expect(selected).toHaveBeenCalled();fireEvent.click(screen.getByRole('button',{name:'Zoom in'}));expect(map.zoomIn).toHaveBeenCalled();
 rerender(<DetailedMap {...props} incidents={[]} onSelect={selected}/>);await waitFor(()=>expect(document.querySelectorAll('.detailed-map-marker')).toHaveLength(0));
 unmount();expect(map.remove).toHaveBeenCalledOnce();
});
it('falls back safely on map service errors without exposing error details',async()=>{
 vi.stubGlobal('WebGL2RenderingContext',class {});render(<DetailedMap {...props}/>);await waitFor(()=>expect(fixture.maps.length).toBe(1));fixture.maps[0].events.error();await waitFor(()=>expect(screen.getByText(/Detailed map unavailable/)).toBeTruthy());expect(screen.getByText('Bundled overview')).toBeTruthy();
});

it('removes the previous map on style changes and recovers from a failed attempt',async()=>{
 vi.stubGlobal('WebGL2RenderingContext',class {});render(<DetailedMap {...props}/>);
 await waitFor(()=>expect(fixture.maps.length).toBe(1));fixture.maps[0].events.load();
 await waitFor(()=>expect(screen.getByRole('button',{name:'Zoom in'})).toBeEnabled());
 fireEvent.change(screen.getByLabelText('Basemap'),{target:{value:'streets'}});
 await waitFor(()=>expect(fixture.maps.length).toBe(2));expect(fixture.maps[0].remove).toHaveBeenCalledOnce();
 fixture.maps[1].events.error();await waitFor(()=>expect(screen.getByRole('button',{name:'Retry detailed map'})).toBeVisible());
 fireEvent.click(screen.getByRole('button',{name:'Retry detailed map'}));await waitFor(()=>expect(fixture.maps.length).toBe(3));fixture.maps[2].events.load();
 await waitFor(()=>expect(screen.getByRole('button',{name:'Zoom in'})).toBeEnabled());
});
