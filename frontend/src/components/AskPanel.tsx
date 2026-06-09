import { MessageCircleQuestion, Send } from "lucide-react";
import { AnimatePresence, motion } from "motion/react";
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

const questionPrompts = [
  "What matters first?",
  "Where should I rewatch?",
  "What changed in the clip?",
];

export function AskPanel({ answer, disabled, asking, onAsk }: AskPanelProps) {
  const [question, setQuestion] = useState("");
  const showForm = !disabled || Boolean(answer);

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    onAsk(question);
  }

  return (
    <motion.section
      className="tool-panel ask-panel"
      aria-labelledby="ask-title"
      aria-busy={asking}
      whileHover={{ y: -1 }}
      transition={{ duration: 0.18 }}
    >
      <div className="panel-heading">
        <div>
          <span className="eyebrow">Question port</span>
          <h2 id="ask-title">Ask the clip</h2>
        </div>
        <MessageCircleQuestion size={22} aria-hidden="true" />
      </div>

      {showForm ? (
        <form className="ask-form" onSubmit={handleSubmit}>
          <div className="prompt-row" aria-label="Question prompts">
            {questionPrompts.map((prompt) => (
              <button
                key={prompt}
                type="button"
                className="prompt-chip"
                onClick={() => setQuestion(prompt)}
                disabled={disabled || asking}
              >
                {prompt}
              </button>
            ))}
          </div>
          <label className="field-label" htmlFor="video-question">
            Your question
          </label>
          <textarea
            id="video-question"
            value={question}
            onChange={(event) => setQuestion(event.target.value)}
            placeholder="What should I pay attention to first?"
            rows={4}
            disabled={disabled || asking}
          />
          <button
            type="submit"
            className="primary-button"
            disabled={disabled || asking || question.trim().length === 0}
          >
            <Send size={17} aria-hidden="true" />
            {asking ? "Reading" : "Ask question"}
          </button>
        </form>
      ) : null}

      <AnimatePresence mode="wait">
        {answer ? (
          <motion.div
            className="answer-block"
            key="answer"
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -8 }}
            transition={{ duration: 0.22 }}
          >
            <h3>Answer</h3>
            <p>{answer.answer}</p>
            <EvidenceList evidence={answer.evidence} compact />
          </motion.div>
        ) : (
          <motion.div
            key={disabled ? "locked" : "empty"}
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -8 }}
            transition={{ duration: 0.22 }}
          >
            <EmptyState
              icon={MessageCircleQuestion}
              title={disabled ? "Questions locked" : "No answer yet"}
              message={disabled ? "Finish the review to open the question port." : "Ask anything about the board."}
            />
          </motion.div>
        )}
      </AnimatePresence>
    </motion.section>
  );
}
