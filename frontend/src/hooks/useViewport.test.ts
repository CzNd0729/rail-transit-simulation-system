import { describe, it, expect } from 'vitest';
import { parseViewBox, clampPanX } from './useViewport';

describe('parseViewBox', () => {
  it('extracts panX and viewW from viewBox string', () => {
    expect(parseViewBox('1200 0 4500 80')).toEqual({ panX: 1200, viewW: 4500 });
  });

  it('handles zero values', () => {
    expect(parseViewBox('0 0 18600 80')).toEqual({ panX: 0, viewW: 18600 });
  });
});

describe('clampPanX', () => {
  it('clamps negative pan to 0', () => {
    expect(clampPanX(-500, 4500, 18600)).toBe(0);
  });

  it('clamps pan beyond line end', () => {
    expect(clampPanX(16000, 4500, 18600)).toBe(14100);
  });

  it('allows pan within valid range', () => {
    expect(clampPanX(3000, 4500, 18600)).toBe(3000);
  });
});
