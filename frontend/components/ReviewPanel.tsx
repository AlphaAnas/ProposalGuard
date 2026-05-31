"use client";

import { useState } from "react";
import { InterruptData } from "@/types";

interface ReviewPanelProps {
  data: InterruptData;
  onApprove: () => void;
  onReject: (feedback: string) => void;
  isLoading: boolean;
}

export default function ReviewPanel({
  data,
  onApprove,
  onReject,
  isLoading,
}: ReviewPanelProps) {
  const [feedback, setFeedback] = useState("");
  const [showRejectForm, setShowRejectForm] = useState(false);

  const score = data.grounding_score;
  const scoreColor =
    score >= 0.7
      ? "text-emerald-400"
      : score >= 0.5
        ? "text-amber-400"
        : "text-red-400";

  return (
    <div className="rounded-xl border-2 border-emerald-400/30 bg-[var(--bg-card)] overflow-hidden animate-fade-in-up">
      {/* Header */}
      <div className="px-6 py-4 bg-emerald-400/5 border-b border-emerald-400/20">
        <div className="flex items-center gap-3">
          <span className="text-2xl">👤</span>
          <div>
            <h3 className="text-lg font-bold text-[var(--text-primary)]">
              Human Review Required
            </h3>
            <p className="text-xs text-[var(--text-secondary)]">
              The pipeline is paused. Review the proposal and approve or request
              changes.
            </p>
          </div>
          <div className="ml-auto flex items-center gap-3">
            <div className="text-right">
              <p className="text-[10px] font-mono text-[var(--text-dim)] uppercase">
                Grounding
              </p>
              <p className={`text-xl font-bold font-mono ${scoreColor}`}>
                {(score * 100).toFixed(0)}%
              </p>
            </div>
            {data.retry_count > 0 && (
              <div className="text-right">
                <p className="text-[10px] font-mono text-[var(--text-dim)] uppercase">
                  Attempt
                </p>
                <p className="text-xl font-bold font-mono text-[var(--text-secondary)]">
                  #{data.retry_count + 1}
                </p>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Proposal text */}
      <div className="px-6 py-5">
        <p className="text-xs font-mono text-[var(--text-dim)] uppercase tracking-wider mb-3">
          Generated Proposal
        </p>
        <div className="p-5 rounded-lg bg-[var(--bg-primary)] border border-[var(--border)] max-h-80 overflow-y-auto">
          <p className="text-sm text-[var(--text-primary)] leading-relaxed whitespace-pre-wrap">
            {data.proposal}
          </p>
        </div>
      </div>

      {/* Bias flags if any */}
      {data.bias_flags.length > 0 && (
        <div className="px-6 pb-4">
          <p className="text-xs font-mono text-purple-400 uppercase tracking-wider mb-2">
            Bias Flags
          </p>
          <div className="space-y-1">
            {data.bias_flags.map((flag, i) => (
              <p
                key={i}
                className="text-xs text-[var(--text-secondary)] p-2 rounded bg-purple-400/5 border border-purple-400/10"
              >
                {flag}
              </p>
            ))}
          </div>
        </div>
      )}

      {/* Actions */}
      <div className="px-6 py-5 border-t border-[var(--border)] bg-[var(--bg-elevated)]/50">
        {!showRejectForm ? (
          <div className="flex items-center gap-3">
            <button
              onClick={() => navigator.clipboard.writeText(data.proposal)}
              className="flex-1 py-3 px-6 rounded-lg bg-emerald-500 hover:bg-emerald-400 text-white font-semibold text-sm transition-all"
            >
              📋 Copy to Clipboard
            </button>
            <button
              onClick={() => setShowRejectForm(true)}
              disabled={isLoading}
              className="flex-1 py-3 px-6 rounded-lg border border-red-400/30 text-red-400 hover:bg-red-400/10 font-semibold text-sm transition-all disabled:opacity-50"
            >
              ✗ Request Changes
            </button>
          </div>
        ) : (
          <div className="space-y-3">
            <p className="text-xs font-mono text-[var(--text-dim)] uppercase">
              What should be changed?
            </p>
            <textarea
              value={feedback}
              onChange={(e) => setFeedback(e.target.value)}
              placeholder="e.g., Add specific technologies, mention the timeline, be more assertive..."
              rows={3}
              className="w-full p-3 rounded-lg bg-[var(--bg-primary)] border border-[var(--border)] text-sm text-[var(--text-primary)] placeholder:text-[var(--text-dim)] focus:outline-none focus:border-[var(--border-hover)] resize-none"
            />
            <div className="flex items-center gap-3">
              <button
                onClick={() => {
                  if (feedback.trim()) onReject(feedback.trim());
                }}
                disabled={isLoading || !feedback.trim()}
                className="flex-1 py-2.5 px-4 rounded-lg bg-red-500/20 border border-red-400/30 text-red-400 hover:bg-red-500/30 font-semibold text-sm transition-all disabled:opacity-50"
              >
                {isLoading ? "Regenerating..." : "Submit Feedback & Regenerate"}
              </button>
              <button
                onClick={() => {
                  setShowRejectForm(false);
                  setFeedback("");
                }}
                className="py-2.5 px-4 rounded-lg text-sm text-[var(--text-dim)] hover:text-[var(--text-secondary)] transition-colors"
              >
                Cancel
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
