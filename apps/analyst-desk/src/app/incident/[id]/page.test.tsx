import { render, screen } from '@testing-library/react';
import { beforeEach, expect, it, vi } from 'vitest';
const { apiMock } = vi.hoisted(() => ({ apiMock: vi.fn() }));
vi.mock('../../../lib/api', () => ({ api: apiMock }));
vi.mock('../../actions', () => ({ addEvidence: vi.fn(), editIncident: vi.fn(), exportIncident: vi.fn(), review: vi.fn(), transition: vi.fn() }));
vi.mock('next/link', () => ({ default: ({ children, href }: React.PropsWithChildren<{ href: string }>) => <a href={href}>{children}</a> }));
import Case from './page';
let matches: unknown[];
beforeEach(() => {
  matches = [{ id: 2, state: 'triage', title_en: 'Related synthetic case', title_ar: 'حالة تجريبية', occurred_at: '2026-10-12T11:00:00Z', private_governorate: 'aleppo', time_difference_seconds: 3600 }];
  apiMock.mockImplementation((path: string) => {
    if (path === '/incidents/1') return Promise.resolve({ id: 1, state: 'triage', title_en: 'Current', title_ar: 'حالي', category: 'infrastructure', private_governorate: 'aleppo', occurred_at: '2026-10-12T10:00:00Z' });
    if (path === '/incidents/1/related') return Promise.resolve(matches);
    return Promise.resolve([]);
  });
});
const page = () => Case({ params: Promise.resolve({ id: '1' }), searchParams: Promise.resolve({}) });
it('preserves private governorate and links possible related cases without merging', async () => {
  render(await page());
  expect((screen.getByLabelText('Private governorate for grouping') as HTMLSelectElement).value).toBe('aleppo');
  expect(screen.getByRole('link', { name: 'Related synthetic case' }).getAttribute('href')).toBe('/incident/2');
  expect(screen.getByText(/60 minutes apart/)).toBeTruthy();
  expect(screen.getByText(/Suggestions do not establish/)).toBeTruthy();
  expect(screen.queryByRole('button', { name: /merge/i })).toBeNull();
});
it('shows an empty result separately from API failure', async () => {
  matches = [];
  render(await page());
  expect(screen.getByText(/No related cases/)).toBeTruthy();
});
it('handles a related endpoint failure without exposing the error', async () => {
  const implementation = apiMock.getMockImplementation()!;
  apiMock.mockImplementation((path: string) => path.endsWith('/related') ? Promise.reject(new Error('private-secret')) : implementation(path));
  render(await page());
  expect(screen.getByText(/Related-case suggestions unavailable/)).toBeTruthy();
  expect(screen.queryByText('private-secret')).toBeNull();
});
it('shows returned matches for timezone-aware historical offsets without a colon', async () => {
  const implementation = apiMock.getMockImplementation()!;
  apiMock.mockImplementation(async (path: string) => {
    const result = await implementation(path);
    return path === '/incidents/1' ? { ...result, occurred_at: '2026-10-12T10:00:00+0000' } : result;
  });
  render(await page());
  expect(screen.getByRole('link', { name: 'Related synthetic case' })).toBeTruthy();
});
