import { BookOpenText, Clock3, ListVideo, Loader2, RefreshCw } from "lucide-react";

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
          <span className="eyebrow">Notes</span>
          <h2 id="timeline-title">Review notes</h2>
        </div>
        {loading ? <Loader2 size={20} aria-hidden="true" className="spin" /> : <BookOpenText size={20} />}
      </div>

      {loading ? (
        <EmptyState icon={Loader2} title="Preparing notes" message="Getting the review ready." />
      ) : !analyzed ? (
        <EmptyState
          icon={stage === "processing" ? Loader2 : ListVideo}
          title={timelineEmptyTitle(stage)}
          message={timelineEmptyMessage(stage)}
        />
      ) : !timeline || timeline.events.length === 0 ? (
        <EmptyState
          icon={ListVideo}
          title="No notes found"
          message="Try reloading the review notes."
          actionLabel="Reload notes"
          actionIcon={RefreshCw}
          actionDisabled={loading}
          onAction={onReload}
        />
      ) : (
        <div className="review-notes">
          <section className="quick-note" aria-labelledby="quick-note-title">
            <span className="eyebrow">Quick read</span>
            <h3 id="quick-note-title">First thing to know</h3>
            <p>{timeline.events[0].summary}</p>
          </section>

          <ol className="timeline-list" aria-label="Key moments">
            {timeline.events.map((event, index) => (
              <li key={`${event.start_time}-${event.end_time}-${index}`} className="timeline-event">
                <div className="event-time">
                  <Clock3 size={15} aria-hidden="true" />
                  {formatRange(event.start_time, event.end_time)}
                </div>
                <div className="event-body">
                  <span className="event-kicker">Moment {index + 1}</span>
                  <p>{event.summary}</p>
                  <details className="source-details">
                    <summary>Show sources</summary>
                    <EvidenceList evidence={event.evidence} />
                  </details>
                </div>
              </li>
            ))}
          </ol>
        </div>
      )}
    </section>
  );
}

function timelineEmptyTitle(stage: WorkflowStage) {
  if (stage === "uploaded") {
    return "Ready to review";
  }
  if (stage === "processing") {
    return "Writing notes";
  }
  if (stage === "failed") {
    return "Notes unavailable";
  }
  return "No video yet";
}

function timelineEmptyMessage(stage: WorkflowStage) {
  if (stage === "uploaded") {
    return "Start the review to see the important moments.";
  }
  if (stage === "processing") {
    return "The notes will appear here when the review finishes.";
  }
  if (stage === "failed") {
    return "Try the review again from the progress panel.";
  }
  return "Add a video to create review notes.";
}
