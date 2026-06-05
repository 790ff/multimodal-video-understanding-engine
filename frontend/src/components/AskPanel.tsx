import { MessageCircleQuestion, Send } from "lucide-react";
import { FormEvent, useState } from "react";

import type { AskVideoResponse } from "../api/types";
import { EmptyState } from "./EmptyState";
import { EvidenceList } from "./EvidenceList";

type AskPanelProps = {
  answer: AskVideoResponse | null;
  disabled: boolean;
  asking: boolean;
  onAsk: (question: string) => void;
};

export function AskPanel({ answer, disabled, asking, onAsk }: AskPanelProps) {
  const [question, setQuestion] = useState("");
  const showForm = !disabled || Boolean(answer);

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    onAsk(question);
  }

  return (
    <section className="tool-panel ask-panel" aria-labelledby="ask-title" aria-busy={asking}>
      <div className="panel-heading">
        <div>
          <span className="eyebrow">Question</span>
          <h2 id="ask-title">Ask the video</h2>
        </div>
        <MessageCircleQuestion size={22} aria-hidden="true" />
      </div>

      {showForm ? (
        <form className="ask-form" onSubmit={handleSubmit}>
          <label className="field-label" htmlFor="video-question">
            Question
          </label>
          <textarea
            id="video-question"
            value={question}
            onChange={(event) => setQuestion(event.target.value)}
            placeholder="What happened at the start?"
            rows={4}
            disabled={disabled || asking}
          />
          <button
            type="submit"
            className="primary-button"
            disabled={disabled || asking || question.trim().length === 0}
          >
            <Send size={17} aria-hidden="true" />
            {asking ? "Asking" : "Ask"}
          </button>
        </form>
      ) : null}

      {answer ? (
        <div className="answer-block">
          <h3>Answer</h3>
          <p>{answer.answer}</p>
          <EvidenceList evidence={answer.evidence} compact />
        </div>
      ) : (
        <EmptyState
          icon={MessageCircleQuestion}
          title={disabled ? "Questions locked" : "No answer yet"}
          message={disabled ? "Analyze a video before asking." : "Ask a question about this video."}
        />
      )}
    </section>
  );
}
