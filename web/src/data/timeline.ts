/**
 * Display time: real run time with idle stretches squeezed, so that a multi-hour run plays
 * in minutes without distorting the pace of experiments (gaps up to GAP seconds are kept).
 */
export const GAP = 20;
export const SQUEEZE = 2;

export interface Timeline {
  real: number[];
  disp: number[];
  duration: number;
}

export function buildTimeline(ts: number[]): Timeline {
  const real: number[] = [];
  const disp: number[] = [];
  let d = 0;
  for (const t of ts) {
    if (!real.length) {
      real.push(t);
      disp.push(0);
      continue;
    }
    const prev = real[real.length - 1];
    if (t <= prev) continue;
    const dt = t - prev;
    d += dt > GAP ? SQUEEZE : dt;
    real.push(t);
    disp.push(d);
  }
  return { real, disp, duration: d };
}

function interp(xs: number[], ys: number[], x: number): number {
  const n = xs.length;
  if (!n) return 0;
  if (x <= xs[0]) return ys[0];
  if (x >= xs[n - 1]) return ys[n - 1];
  let lo = 0;
  let hi = n - 1;
  while (hi - lo > 1) {
    const mid = (lo + hi) >> 1;
    if (xs[mid] <= x) lo = mid;
    else hi = mid;
  }
  const f = (x - xs[lo]) / (xs[hi] - xs[lo] || 1);
  return ys[lo] + f * (ys[hi] - ys[lo]);
}

export function toDisplay(tl: Timeline, real: number): number {
  return interp(tl.real, tl.disp, real);
}

export function toReal(tl: Timeline, disp: number): number {
  return interp(tl.disp, tl.real, disp);
}
