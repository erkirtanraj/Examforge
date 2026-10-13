import { useEffect, useRef, useState } from "react";

let apiPromise;
const loadApi = () => {
  if (window.YT?.Player) return Promise.resolve(window.YT);
  if (!apiPromise) {
    apiPromise = new Promise((resolve, reject) => {
      let settled = false;
      let timeout;
      const finish = (error, YT) => {
        if (settled) return;
        settled = true;
        window.clearTimeout(timeout);
        if (error) {
          apiPromise = null;
          document.querySelector('script[src="https://www.youtube.com/iframe_api"]')?.remove();
          reject(error);
        } else {
          resolve(YT);
        }
      };

      const previousReady = window.onYouTubeIframeAPIReady;
      window.onYouTubeIframeAPIReady = () => {
        try {
          previousReady?.();
        } finally {
          if (window.YT?.Player) finish(null, window.YT);
          else finish(new Error("YouTube player API did not initialize."));
        }
      };

      let script = document.querySelector('script[src="https://www.youtube.com/iframe_api"]');
      if (!script) {
        script = document.createElement("script");
        script.src = "https://www.youtube.com/iframe_api";
        script.async = true;
        document.head.appendChild(script);
      }
      script.addEventListener("error", () => finish(new Error("Could not load the YouTube player API.")), { once: true });
      timeout = window.setTimeout(() => finish(new Error("Timed out while loading the YouTube player API.")), 15000);
    });
  }
  return apiPromise;
};

const YOUTUBE_HOSTS = new Set([
  "youtube.com",
  "www.youtube.com",
  "m.youtube.com",
  "music.youtube.com",
  "youtube-nocookie.com",
  "www.youtube-nocookie.com",
  "youtu.be",
  "www.youtu.be",
]);

export function youtubeId(value = "") {
  if (typeof value !== "string" || !value.trim()) return null;
  let parsed;
  try {
    const candidate = /^[a-z][a-z\d+.-]*:\/\//i.test(value.trim())
      ? value.trim()
      : `https://${value.trim()}`;
    parsed = new URL(candidate);
  } catch {
    return null;
  }

  if (!["https:", "http:"].includes(parsed.protocol) || !YOUTUBE_HOSTS.has(parsed.hostname.toLowerCase())) return null;

  let id = parsed.searchParams.get("v");
  const parts = parsed.pathname.split("/").filter(Boolean);
  if (!id && ["embed", "shorts", "live", "v"].includes(parts[0])) id = parts[1];
  if (!id && ["youtu.be", "www.youtu.be"].includes(parsed.hostname.toLowerCase())) id = parts[0];

  return id && /^[\w-]{11}$/.test(id) ? id : null;
}

// YouTube IFrame API wrapper. Keeps the existing player controls and state contract.
export function useYouTube(videoId, { onEnded, rate = 1 } = {}) {
  const host = useRef(null);
  const player = useRef(null);
  const endedRef = useRef(onEnded);
  endedRef.current = onEnded;
  const rateRef = useRef(rate);
  rateRef.current = rate;
  const [retryKey, setRetryKey] = useState(0);
  const [state, setState] = useState({
    ready: false, playing: false, started: false, ended: false, time: 0, duration: 0, error: null,
  });

  useEffect(() => {
    if (!videoId) return undefined;
    let cancelled = false;
    setState({ ready: false, playing: false, started: false, ended: false, time: 0, duration: 0, error: null });

    loadApi().then((YT) => {
      if (cancelled || !host.current) return;
      const el = document.createElement("div");
      host.current.replaceChildren(el);
      try {
        player.current = new YT.Player(el, {
          videoId,
          host: "https://www.youtube-nocookie.com",
          width: "100%",
          height: "100%",
          playerVars: {
            controls: 0, modestbranding: 1, rel: 0, disablekb: 1, fs: 0,
            iv_load_policy: 3, playsinline: 1, cc_load_policy: 0,
            enablejsapi: 1, origin: window.location.origin,
          },
          events: {
            onReady: (e) => {
              if (cancelled) return;
              e.target.setPlaybackRate(rateRef.current);
              setState((s) => ({ ...s, ready: true, error: null, duration: e.target.getDuration() || 0 }));
            },
            onStateChange: (e) => {
              if (cancelled) return;
              const S = YT.PlayerState;
              if (e.data === S.PLAYING) {
                setState((s) => ({ ...s, playing: true, started: true, ended: false, error: null, duration: player.current?.getDuration?.() || s.duration }));
              } else if (e.data === S.PAUSED) {
                setState((s) => ({ ...s, playing: false }));
              } else if (e.data === S.ENDED) {
                setState((s) => ({ ...s, playing: false, ended: true }));
                endedRef.current?.();
              }
            },
            onError: (e) => {
              if (cancelled) return;
              setState((s) => ({ ...s, ready: false, playing: false, error: e.data || "unavailable" }));
            },
          },
        });
      } catch {
        setState((s) => ({ ...s, error: "unavailable" }));
      }
    }).catch((error) => {
      if (!cancelled) setState((s) => ({ ...s, ready: false, playing: false, error: error?.message || "unavailable" }));
    });

    return () => {
      cancelled = true;
      try { player.current?.destroy(); } catch { /* already gone */ }
      player.current = null;
    };
  }, [videoId, retryKey]);

  useEffect(() => {
    if (!state.playing) return undefined;
    const t = window.setInterval(() => setState((s) => ({
      ...s, time: player.current?.getCurrentTime?.() || 0,
      duration: player.current?.getDuration?.() || s.duration,
    })), 500);
    return () => window.clearInterval(t);
  }, [state.playing]);

  const controls = {
    play: () => player.current?.playVideo(),
    pause: () => player.current?.pauseVideo(),
    toggle: () => (state.playing ? player.current?.pauseVideo() : player.current?.playVideo()),
    setRate: (r) => player.current?.setPlaybackRate?.(r),
    current: () => ({ time: player.current?.getCurrentTime?.() || 0, duration: player.current?.getDuration?.() || 0 }),
    seek: (sec) => { player.current?.seekTo(sec, true); setState((s) => ({ ...s, time: sec, ended: false })); },
    retry: () => setRetryKey((key) => key + 1),
  };
  return { host, state, controls };
}
