import { useEffect, useRef, useState } from "react";

let apiPromise;
const loadApi = () => {
  if (window.YT?.Player) return Promise.resolve(window.YT);
  if (!apiPromise) {
    apiPromise = new Promise((resolve) => {
      const prev = window.onYouTubeIframeAPIReady;
      window.onYouTubeIframeAPIReady = () => { prev?.(); resolve(window.YT); };
      const s = document.createElement("script");
      s.src = "https://www.youtube.com/iframe_api";
      s.async = true;
      document.head.appendChild(s);
    });
  }
  return apiPromise;
};

export function youtubeId(url = "") {
  const m = url.match(/(?:youtube(?:-nocookie)?\.com\/(?:embed\/|shorts\/|live\/|watch\?(?:.*&)?v=)|youtu\.be\/)([\w-]{11})/);
  return m ? m[1] : null;
}

// Chrome-less YouTube player: exposes state + play/pause/seek, polls current time.
export function useYouTube(videoId, { onEnded } = {}) {
  const host = useRef(null);
  const player = useRef(null);
  const endedRef = useRef(onEnded);
  endedRef.current = onEnded;
  const [state, setState] = useState({ ready: false, playing: false, started: false, ended: false, time: 0, duration: 0 });

  useEffect(() => {
    if (!videoId) return undefined;
    let cancelled = false;
    setState({ ready: false, playing: false, started: false, ended: false, time: 0, duration: 0 });
    loadApi().then((YT) => {
      if (cancelled || !host.current) return;
      const el = document.createElement("div");
      host.current.replaceChildren(el);
      player.current = new YT.Player(el, {
        videoId, host: "https://www.youtube-nocookie.com", width: "100%", height: "100%",
        playerVars: { controls: 0, modestbranding: 1, rel: 0, disablekb: 1, fs: 0, iv_load_policy: 3, playsinline: 1, cc_load_policy: 0 },
        events: {
          onReady: (e) => setState((s) => ({ ...s, ready: true, duration: e.target.getDuration() || 0 })),
          onStateChange: (e) => {
            const S = YT.PlayerState;
            if (e.data === S.PLAYING) setState((s) => ({ ...s, playing: true, started: true, ended: false, duration: player.current.getDuration() }));
            else if (e.data === S.PAUSED) setState((s) => ({ ...s, playing: false }));
            else if (e.data === S.ENDED) { setState((s) => ({ ...s, playing: false, ended: true })); endedRef.current?.(); }
          },
        },
      });
    });
    return () => { cancelled = true; try { player.current?.destroy(); } catch { /* already gone */ } player.current = null; };
  }, [videoId]);

  useEffect(() => {
    if (!state.playing) return undefined;
    const t = setInterval(() => setState((s) => ({ ...s, time: player.current?.getCurrentTime?.() || 0 })), 500);
    return () => clearInterval(t);
  }, [state.playing]);

  const controls = {
    play: () => player.current?.playVideo(),
    pause: () => player.current?.pauseVideo(),
    toggle: () => (state.playing ? player.current?.pauseVideo() : player.current?.playVideo()),
    seek: (sec) => { player.current?.seekTo(sec, true); setState((s) => ({ ...s, time: sec, ended: false })); },
  };
  return { host, state, controls };
}
