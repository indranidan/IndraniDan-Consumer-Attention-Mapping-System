import React, { useMemo } from 'react';
import { useUnifiedJobContext } from '../../../context/UnifiedJobContext';
import { EventTypeBadge, DirectionBadge } from './SharedComponents';

export default function LogsTab() {
  const {
    eventsList,
    eventsLoading,
    eventSearch,
    setEventSearch,
    eventFilterType,
    setEventFilterType
  } = useUnifiedJobContext();

  const filteredEvents = useMemo(() => {
    return eventsList.filter((e) => {
      if (eventFilterType !== "ALL") {
        if (eventFilterType === "ATTENTION" && e.sourceCategory !== "ATTENTION") return false;
        if (eventFilterType === "INTERACTION" && e.sourceCategory !== "INTERACTION") return false;
        if (eventFilterType === "GAZE" && !e.attention_direction) return false;
      }
      if (eventSearch) {
        const q = eventSearch.toLowerCase();
        const matchId = String(e.track_id).includes(q);
        const matchTarget = String(e.target_name || e.product_name || e.target_id || "").toLowerCase().includes(q);
        const matchType = String(e.attention_type || e.event_type || "").toLowerCase().includes(q);
        if (!matchId && !matchTarget && !matchType) return false;
      }
      return true;
    });
  }, [eventsList, eventFilterType, eventSearch]);

  return (
    <div className="space-y-4 animate-fade-in">
      <div className="bg-gray-900/60 backdrop-blur-xl border border-gray-800/80 rounded-2xl p-5 shadow-xl">
        {/* Filters */}
        <div className="flex flex-wrap items-center justify-between gap-3 mb-4">
          <div className="flex items-center gap-2">
            {["ALL", "ATTENTION", "INTERACTION", "GAZE"].map((f) => (
              <button
                key={f}
                onClick={() => setEventFilterType(f)}
                className={`px-3 py-1 rounded-lg text-xs font-medium transition-all ${
                  eventFilterType === f
                    ? "bg-violet-600 text-white"
                    : "bg-gray-800/60 text-gray-400 hover:text-white"
                }`}
              >
                {f}
              </button>
            ))}
          </div>

          <input
            type="text"
            value={eventSearch}
            onChange={(e) => setEventSearch(e.target.value)}
            placeholder="Search track ID or target..."
            className="bg-gray-950/80 border border-gray-800 rounded-xl px-3 py-1.5 text-xs text-white placeholder-gray-500 focus:outline-none focus:border-violet-500 w-52"
          />
        </div>

        {eventsLoading ? (
          <div className="py-12 text-center text-xs text-gray-400">Loading structured events stream...</div>
        ) : filteredEvents.length === 0 ? (
          <div className="py-12 text-center text-xs text-gray-500">No events found matching filters.</div>
        ) : (
          <div className="overflow-x-auto max-h-[500px]">
            <table className="w-full text-left text-xs">
              <thead className="sticky top-0 bg-gray-900/90 backdrop-blur-md">
                <tr className="border-b border-gray-800 text-[11px] text-gray-400 uppercase tracking-wider">
                  <th className="py-2.5 px-3">Time</th>
                  <th className="py-2.5 px-3">Shopper</th>
                  <th className="py-2.5 px-3">Event Type</th>
                  <th className="py-2.5 px-3">Target Object</th>
                  <th className="py-2.5 px-3 text-center">Direction</th>
                  <th className="py-2.5 px-3 text-right">Duration</th>
                  <th className="py-2.5 px-3 text-right">Confidence</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-800/30 text-gray-300">
                {filteredEvents.map((ev, i) => (
                  <tr key={i} className="hover:bg-gray-800/20 transition-colors font-mono text-[11px]">
                    <td className="py-2.5 px-3 text-gray-400">
                      {(ev.start_time || ev.timestamp || 0).toFixed(1)}s
                    </td>
                    <td className="py-2.5 px-3 font-semibold text-white">
                      Shopper #{ev.track_id}
                    </td>
                    <td className="py-2.5 px-3">
                      <EventTypeBadge type={ev.attention_type || ev.event_type} />
                    </td>
                    <td className="py-2.5 px-3 text-gray-200 font-sans">
                      {ev.target_name || ev.product_name || ev.target_id || "Shelf Target"}
                    </td>
                    <td className="py-2.5 px-3 text-center">
                      <DirectionBadge direction={ev.attention_direction} />
                    </td>
                    <td className="py-2.5 px-3 text-right text-cyan-400">
                      {(ev.duration_seconds || 1.0).toFixed(1)}s
                    </td>
                    <td className="py-2.5 px-3 text-right text-gray-400">
                      {((ev.confidence || 0.85) * 100).toFixed(0)}%
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
