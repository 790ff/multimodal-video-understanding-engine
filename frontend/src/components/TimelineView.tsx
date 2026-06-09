import { BookOpenText, Clock3, ListVideo, Loader2, RefreshCw, Target } from "lucide-react";
import { AnimatePresence, motion } from "motion/react";
import { useEffect, useMemo, useState } from "react";

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
  const events = useMemo(() => timeline?.events ?? [], [timeline]);
  const [activeIndex, setActiveIndex] = useState(0);
  const activeEvent = events[activeIndex] ?? events[0] ?? null;

  useEffect(() => {
    setActiveIndex(0);
  }, [events.length]);

  return (
    <motion.section
      className={`timeline-section${locked ? " timeline-section--locked" : ""}`}
      aria-labelledby="timeline-title"
      aria-busy={loading}
      layout
    >
      <div className="section-heading">
        <div>
          <span className="eyebrow">Moment board</span>
          <h2 id="timeline-title">Review board</h2>
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
        <div className="moment-board">
          <section className="moment-stage" aria-live="polite">
            <div className="moment-stage__top">
              <span className="event-kicker">Moment {activeIndex + 1}</span>
              <span className="event-time">
                <Clock3 size={15} aria-hidden="true" />
                {activeEvent ? formatRange(activeEvent.start_time, activeEvent.end_time) : "--"}
              </span>
            </div>
            <AnimatePresence mode="wait">
              {activeEvent ? (
                <motion.div
                  key={`${activeEvent.start_time}-${activeEvent.end_time}-${activeIndex}`}
                  initial={{ opacity: 0, y: 8 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, y: -8 }}
                  transition={{ duration: 0.22 }}
                >
                  <h3>{activeEvent.summary}</h3>
                  <EvidenceList evidence={activeEvent.evidence} />
                </motion.div>
              ) : null}
            </AnimatePresence>
          </section>

          <ol className="timeline-list" aria-label="Key moments">
            {events.map((event, index) => {
              const active = index === activeIndex;
              return (
                <li key={`${event.start_time}-${event.end_time}-${index}`}>
                  <button
                    type="button"
                    className={`timeline-event${active ? " timeline-event--active" : ""}`}
                    onClick={() => setActiveIndex(index)}
                    aria-pressed={active}
                  >
                    <span className="timeline-event__marker" aria-hidden="true">
                      {active ? <Target size={14} /> : index + 1}
                    </span>
                    <span className="event-body">
                      <span className="event-kicker">Moment {index + 1}</span>
                      <span>{event.summary}</span>
                    </span>
                    <span className="event-time">
                      <Clock3 size={14} aria-hidden="true" />
                      {formatRange(event.start_time, event.end_time)}
                    </span>
                  </button>
                </li>
              );
            })}
          </ol>
        </div>
      )}
    </motion.section>
  );
}

function timelineEmptyTitle(stage: WorkflowStage) {
  if (stage === "uploaded") {
    return "Deck armed";
  }
  if (stage === "processing") {
    return "Writing board";
  }
  if (stage === "failed") {
    return "Board stalled";
  }
  return "No clip yet";
}

function timelineEmptyMessage(stage: WorkflowStage) {
  if (stage === "uploaded") {
    return "Start review to unlock moments and sources.";
  }
  if (stage === "processing") {
    return "Moments will land here when the review finishes.";
  }
  if (stage === "failed") {
    return "Retry the deck from the review engine.";
  }
  return "Add a clip to build the review board.";
}
