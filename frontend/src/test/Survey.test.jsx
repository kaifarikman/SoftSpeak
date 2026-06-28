import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';
import Survey from '../components/messenger/Survey';

class FakeWebSocket {
  static instances = [];

  static OPEN = 1;
  static CONNECTING = 0;
  static CLOSED = 3;

  constructor(url) {
    this.url = url;
    this.readyState = FakeWebSocket.CONNECTING;
    this.send = vi.fn();
    FakeWebSocket.instances.push(this);
    queueMicrotask(() => {
      this.readyState = FakeWebSocket.OPEN;
      if (this.onopen) {
        this.onopen();
      }
    });
  }

  close(code = 1000, reason = '') {
    this.readyState = FakeWebSocket.CLOSED;
    if (this.onclose) {
      this.onclose({ code, reason });
    }
  }
}

afterEach(() => {
  vi.restoreAllMocks();
  vi.unstubAllGlobals();
  FakeWebSocket.instances = [];
  localStorage.clear();
});

describe('Survey interest step', () => {
  it('shows tag selection after survey completion and saves selected tags', async () => {
    const onComplete = vi.fn();
    const fetchMock = vi.fn();
    fetchMock.mockResolvedValueOnce({
      ok: true,
      json: async () => [
        { id: 1, name: 'Психология', emoji: '🧠' },
        { id: 2, name: 'Кино', emoji: '🎬' },
      ],
    });
    fetchMock.mockResolvedValueOnce({
      ok: true,
      json: async () => ({ ok: true }),
    });

    vi.stubGlobal('fetch', fetchMock);
    vi.stubGlobal('WebSocket', FakeWebSocket);

    render(<Survey email="tester@example.com" onComplete={onComplete} />);

    await waitFor(() => {
      expect(FakeWebSocket.instances).toHaveLength(1);
    });

    const ws = FakeWebSocket.instances[0];
    ws.onmessage?.({
      data: JSON.stringify({
        type: 'question',
        question: { id: 1, category: { name: 'Психология' }, text: 'Как дела?' },
        current_question_number: 1,
        total_questions: 10,
      }),
    });

    await waitFor(() => {
      expect(screen.getByText('Как дела?')).toBeInTheDocument();
    });

    ws.onmessage?.({
      data: JSON.stringify({
        type: 'survey_completed',
        message: 'Опрос завершен',
      }),
    });

    expect(await screen.findByRole('heading', { name: 'Выберите интересы' })).toBeInTheDocument();

    await waitFor(() => {
      expect(screen.getByRole('button', { name: /Психология/ })).toBeInTheDocument();
    });

    fireEvent.click(screen.getByRole('button', { name: /Психология/ }));
    fireEvent.click(screen.getByRole('button', { name: 'Продолжить' }));

    await waitFor(() => {
      expect(onComplete).toHaveBeenCalledTimes(1);
    });

    expect(fetchMock).toHaveBeenNthCalledWith(
      1,
      expect.stringContaining('/tags'),
      expect.anything()
    );
    expect(fetchMock).toHaveBeenNthCalledWith(
      2,
      expect.stringContaining('/tags/user/tester@example.com'),
      expect.objectContaining({
        method: 'POST',
      })
    );
  });
});
