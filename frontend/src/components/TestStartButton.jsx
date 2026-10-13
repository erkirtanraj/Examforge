import React from "react";
import { Lock, Play, CalendarClock } from "lucide-react";
import { Button } from "./ui/button";
import { useNow, fmtCountdown } from "./Countdown";

export default function TestStartButton({ t, hasAccess, onStart }) {
  const now = useNow(1000);
  const opensAt = t.live_start_at ? new Date(t.live_start_at).getTime() : 0;
  if (opensAt > now) {
    return (
      <Button disabled data-testid={`start-test-${t.id}`} className="bg-gray-800 text-cyan-300 mono-font disabled:opacity-100">
        <CalendarClock className="w-4 h-4 mr-1" />Opens in {fmtCountdown(opensAt - now)}
      </Button>
    );
  }
  return (
    <Button onClick={onStart} data-testid={`start-test-${t.id}`} className={hasAccess ? "bg-blue-600 hover:bg-blue-700" : "bg-gray-700"}>
      {hasAccess ? <><Play className="w-4 h-4 mr-1" />Start</> : <><Lock className="w-4 h-4 mr-1" />Locked</>}
    </Button>
  );
}
