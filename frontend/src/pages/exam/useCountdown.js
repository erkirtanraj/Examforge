import { useEffect, useRef, useState } from "react";

export const isAnswered = (a) => (Array.isArray(a) ? a.length > 0 : a !== undefined && a !== "");

export const hms = (s) =>
  [Math.floor(s / 3600), Math.floor((s % 3600) / 60), s % 60].map((n) => String(n).padStart(2, "0")).join(":");

// Counts down to an ISO deadline; fires onExpire once when it reaches zero
export function useCountdown(deadline, onExpire) {
  const [left, setLeft] = useState(0);
  const cb = useRef(onExpire);
  cb.current = onExpire;
  useEffect(() => {
    if (!deadline) return;
    const end = new Date(deadline).getTime();
    let fired = false;
    const tick = () => {
      const s = Math.max(0, Math.floor((end - Date.now()) / 1000));
      setLeft(s);
      if (s === 0 && !fired) { fired = true; cb.current(); }
    };
    tick();
    const t = setInterval(tick, 1000);
    return () => clearInterval(t);
  }, [deadline]);
  return left;
}
