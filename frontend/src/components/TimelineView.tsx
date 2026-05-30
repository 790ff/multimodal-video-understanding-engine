import { Clock3, ListVideo, Loader2, RefreshCw } from "lucide-react";

import type { TimelineResponse } from "../api/types";
import { formatRange } from "../utils/time";
import { EmptyState } from "./EmptyState";
import { EvidenceList } from "./EvidenceList";

type TimelineViewProps = {
  timeline: TimelineResponse | null;
  loading: boolean;
  analyzed: boolean;
  onReload: () => void;
};

export function TimelineView({ timeline, loading, analyzed, onReload }: TimelineViewProps) {
  return (
    <section className="timeline-section" aria-labelledby="timeline-title" aria-busy={loading}>
      <div className="section-heading">
        <div>
          <span className="eyebrow">Evidence</span>
          <h2 id="timeline-title">Timeline</h2>
        </div>
        {loading ? <Loader2 size={20} aria-hidden="true" className="spin" /> : <Clock3 size={20} />}
      </div>

      {loading ? (
        <EmptyState icon={Loader2} title="Loading timeline" message="Fetching stored events." />
      ) : !analyzed ? (
        <EmptyState icon={ListVideo} title="Not analyzed yet" message="Timeline appears after analysis." />
      ) : !timeline || timeline.events.length === 0 ? (
        <EmptyState
          icon={ListVideo}
          title="No events"
          message="No timeline events were loaded."
          actionLabel="Reload timeline"
          actionIcon={RefreshCw}
          actionDisabled={loading}
          onAction={onReload}
        />
      ) : (
        <ol className="timeline-list">
          {timeline.events.map((event, index) => (
            <li key={`${event.start_time}-${event.end_time}-${index}`} className="timeline-event">
              <div className="event-time">{formatRange(event.start_time, event.end_time)}</div>
              <div className="event-body">
                <p>{event.summary}</p>
                <EvidenceList evidence={event.evidence} />
              </div>
            </li>
          ))}
        </ol>
      )}
    </section>
  );
}
