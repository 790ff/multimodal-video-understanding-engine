import { Clock3, ListVideo, Loader2, RefreshCw } from "lucide-react";

import type { TimelineResponse } from "../api/types";
import { formatRange } from "../utils/time";
import type { WorkflowStage } from "../utils/workflowStage";
import { EmptyState } from "./EmptyState";
import { EvidenceList } from "./EvidenceList";

type TimelineViewProps = {
  timeline: TimelineResponse | null;
  loading: boolean;
  analyzed: boolean;
  stage: WorkflowStage;
  onReload: () => void;
};

export function TimelineView({ timeline, loading, analyzed, stage, onReload }: TimelineViewProps) {
  const locked = !analyzed && !loading;

  return (
    <section
      className={`timeline-section${locked ? " timeline-section--locked" : ""}`}
      aria-labelledby="timeline-title"
      aria-busy={loading}
    >
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
        <EmptyState
          icon={stage === "processing" ? Loader2 : ListVideo}
          title={timelineEmptyTitle(stage)}
          message={timelineEmptyMessage(stage)}
        />
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

function timelineEmptyTitle(stage: WorkflowStage) {
  if (stage === "uploaded") {
    return "Ready for analysis";
  }
  if (stage === "processing") {
    return "Building timeline";
  }
  if (stage === "failed") {
    return "Timeline unavailable";
  }
  return "No timeline yet";
}

function timelineEmptyMessage(stage: WorkflowStage) {
  if (stage === "uploaded") {
    return "Timeline events will appear after analysis completes.";
  }
  if (stage === "processing") {
    return "Events will appear here when processing finishes.";
  }
  if (stage === "failed") {
    return "Retry analysis to generate timestamped evidence.";
  }
  return "Upload a video to create timestamped evidence.";
}
