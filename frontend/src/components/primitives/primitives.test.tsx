import { render, screen } from '@testing-library/preact';
import { describe, expect, it } from 'vitest';
import { Lamp, Legend, Panel, Readout, Screw, Sticker } from '.';
import { turnFor } from './Screw';

describe('primitives', () => {
  it('Readout renders feed text literally, never as markup', () => {
    const { container } = render(<Readout kind="break">{'Previous <b>Song</b> <img src=x onerror=alert(1)>'}</Readout>);
    expect(container.querySelector('b')).toBeNull();
    expect(container.querySelector('img')).toBeNull();
    expect(container.textContent).toBe('Previous <b>Song</b> <img src=x onerror=alert(1)>');
    expect(container.firstElementChild).toHaveAttribute('data-kind', 'break');
  });

  it('Lamp exposes state as data attributes and is hidden from AT', () => {
    const { container } = render(<Lamp colour="cyan" on size="sm" />);
    const l = container.firstElementChild!;
    expect(l).toHaveAttribute('data-on', '1');
    expect(l).toHaveAttribute('data-c', 'cyan');
    expect(l).toHaveAttribute('aria-hidden', 'true');
  });

  it('Legend is a heading with trilingual sub-legend tagged by language', () => {
    render(<Legend en="Log" zh="记录" id="Catatan" ru="Журнал" note="last 15 plays" htmlId="l-log" />);
    const h = screen.getByRole('heading', { level: 2 });
    expect(h).toHaveAttribute('id', 'l-log');
    expect(h.querySelector('[lang="zh"]')).toHaveTextContent('记录');
    expect(h.querySelector('[lang="ru"]')).toHaveTextContent('Журнал');
    expect(h.querySelector('.tri')).toHaveAttribute('aria-hidden', 'true');
    expect(screen.getByText('last 15 plays')).toBeInTheDocument();
  });

  it('Panel is a screwed section and screws keep a stable turn', () => {
    const { container } = render(
      <Panel name="log" aria-label="Log">
        x
      </Panel>,
    );
    expect(container.querySelectorAll('.screw')).toHaveLength(4);
    expect(screen.getByRole('region', { name: 'Log' })).toHaveClass('module', 'log');
    expect(turnFor('a')).toBe(turnFor('a'));
    const s = render(<Screw seed="a" />).container.firstElementChild as HTMLElement;
    expect(s.style.getPropertyValue('--r')).toBe(`${turnFor('a')}deg`);
  });

  it('Stickers are decorative', () => {
    const { container } = render(<Sticker variant="cyr">ЭФИР</Sticker>);
    expect(container.firstElementChild).toHaveAttribute('aria-hidden', 'true');
    expect(container.firstElementChild).toHaveClass('sticker', 'cyr');
  });
});
