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

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    onAsk(question);
  }

  return (
    <section className="tool-panel ask-panel" aria-labelledby="ask-title">
      <div className="panel-heading">
        <div>
          <span className="eyebrow">Question</span>
          <h2 id="ask-title">Ask the video</h2>
        </div>
        <MessageCircleQuestion size={22} aria-hidden="true" />
      </div>

      <form className="ask-form" onSubmit={handleSubmit}>
        <textarea
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

      {answer ? (
        <div className="answer-block">
          <h3>Answer</h3>
          <p>{answer.answer}</p>
          <EvidenceList evidence={answer.evidence} compact />
        </div>
      ) : (
        <EmptyState
          icon={MessageCircleQuestion}
          title="No answer yet"
          message="Answers use stored timeline, transcript, frame, and scene evidence."
        />
      )}
    </section>
  );
}
