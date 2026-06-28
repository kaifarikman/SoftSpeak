import { render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { afterEach, describe, expect, it, vi } from 'vitest';
import App from '../App';

afterEach(() => {
  vi.restoreAllMocks();
  localStorage.clear();
});

function renderRoute(path) {
  return render(
    <MemoryRouter initialEntries={[path]}>
      <App />
    </MemoryRouter>
  );
}

describe('critical page smoke tests', () => {
  it('renders sign in page', () => {
    renderRoute('/signin');
    expect(screen.getByRole('heading', { name: 'Вход' })).toBeInTheDocument();
  });

  it('renders sign up page', () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({ ok: true, json: async () => [] }));
    renderRoute('/signup');
    expect(screen.getByRole('heading', { name: 'Регистрация' })).toBeInTheDocument();
  });

  it('renders admin login page', () => {
    renderRoute('/admin');
    expect(screen.getByRole('heading', { name: 'Админка SoftSpeak' })).toBeInTheDocument();
  });

  it('renders public profile page', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue({
        ok: true,
        json: async () => ({ nickname: 'tester', bio: 'hello' }),
      })
    );
    renderRoute('/u/tester');
    await waitFor(() => {
      expect(screen.getByRole('heading', { name: 'tester' })).toBeInTheDocument();
    });
  });
});
