import { fireEvent, render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import HamburgerMenu from '../components/messenger/HamburgerMenu';

describe('HamburgerMenu', () => {
  it('opens a section drawer and emits the selected section', () => {
    const onSelectSection = vi.fn();

    render(
      <HamburgerMenu
        sections={[
          { id: 'bot', title: 'Бот' },
          { id: 'anon', title: 'Анонимные' },
        ]}
        activeSection="bot"
        onSelectSection={onSelectSection}
      />
    );

    fireEvent.click(screen.getByRole('button', { name: 'Открыть меню' }));

    expect(screen.getByRole('button', { name: 'Анонимные' })).toBeInTheDocument();

    fireEvent.click(screen.getByRole('button', { name: 'Анонимные' }));
    expect(onSelectSection).toHaveBeenCalledWith('anon');
  });
});
