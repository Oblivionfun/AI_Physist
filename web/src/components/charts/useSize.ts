import { useLayoutEffect, useRef, useState } from "react";

export function useSize<T extends HTMLElement>(fallback = { width: 400, height: 240 }) {
  const ref = useRef<T>(null);
  const [size, setSize] = useState(fallback);
  useLayoutEffect(() => {
    if (!ref.current) return;
    const ro = new ResizeObserver(([e]) => {
      const { width, height } = e.contentRect;
      setSize({ width: Math.max(120, width), height: Math.max(80, height) });
    });
    ro.observe(ref.current);
    return () => ro.disconnect();
  }, []);
  return [ref, size] as const;
}
