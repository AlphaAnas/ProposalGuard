"use client";

import { NodeEvent } from "@/types";

const NODE_META: Record<string, { label: string; icon: string; accent: string; accentBg: string; accentBorder: string }> = {
  retrieve: { label: "Context Retrieved", icon: "🔍", accent: "text-cyan-400", accentBg: "bg-cyan-400/10", accentBorder: "border-cyan-400/20" },
  generate: { label: "Proposal Generated", icon: "✍️", accent: "text-blue-400", accentBg: "bg-blue-400/10", accentBorder: "border-blue-400/20" },
  verify: { label: "Grounding Verified", icon: "✅", accent: "text-amber-400", accentBg: "bg-amber-400/10", accentBorder: "border-amber-400/20" },
  bias_check: { label: "Bias Evaluated", icon: "⚖️", accent: "text-purple-400", accentBg: "bg-purple-400/10", accentBorder: "border-purple-400/20" },
  increment_retry: { label: "Retrying", icon: "🔄", accent: "text-orange-400", accentBg: "bg-orange-400/10", accentBorder: "border-orange-400/20" },
};

function RetrieveCard({ data }: { data: Record<string, any> }) {
  const results = data.retrieval_results || [];
  return (
    <div className="space-y-3">
      <p className="text-sm text-[var(--text-secondary)]">
        Found {results.length} relevant past proposal{results.length !== 1 ? "s" : ""} from vector database
      </p>
      {results.map((r: any, i: number) => (
        <div key={i} className="p-3 rounded-lg bg-[var(--bg-primary)] border border-[var(--border)]">
          <div className="flex items-center justify-between mb-2">
            <span className="text-xs font-mono text-cyan-400">{r.source}</span>
            <span className="text-xs font-mono px-2 py-0.5 rounded-full bg-cyan-400/10 text-cyan-400 border border-cyan-400/20">
              {(r.score * 100).toFixed(0)}% match
            </span>
          </div>
          <p className="text-xs text-[var(--text-dim)] leading-relaxed">{r.text}</p>
        </div>
      ))}
    </div>
  );
}

function GenerateCard({ data }: { data: Record<string, any> }) {
  const meta = data.generation_metadata || {};
  return (
    <div className="space-y-3">
      <div className="flex flex-wrap gap-2">
        {meta.model && (
          <span className="text-xs font-mono px-2 py-1 rounded bg-blue-400/10 text-blue-400 border border-blue-400/20">
            {meta.model}
          </span>
        )}
        {meta.attempt && (
          <span className="text-xs font-mono px-2 py-1 rounded bg-[var(--bg-primary)] text-[var(--text-secondary)] border border-[var(--border)]">
            Attempt #{meta.attempt}
          </span>
        )}
        {meta.past_proposals_used > 0 && (
          <span className="text-xs font-mono px-2 py-1 rounded bg-[var(--bg-primary)] text-[var(--text-secondary)] border border-[var(--border)]">
            {meta.past_proposals_used} past proposals used
          </span>
        )}
        {meta.tokens?.total_tokens && (
          <span className="text-xs font-mono px-2 py-1 rounded bg-[var(--bg-primary)] text-[var(--text-dim)] border border-[var(--border)]">
            {meta.tokens.total_tokens} tokens
          </span>
        )}
      </div>
      {meta.feedback_used && (
        <div className="p-2 rounded bg-amber-400/5 border border-amber-400/10">
          <span className="text-xs text-amber-400 font-mono">Feedback incorporated: </span>
          <span className="text-xs text-[var(--text-secondary)]">{meta.feedback_used}</span>
        </div>
      )}
      {data.draft_proposal && (
        <div className="p-3 rounded-lg bg-[var(--bg-primary)] border border-[var(--border)]">
          <p className="text-sm text-[var(--text-secondary)] leading-relaxed whitespace-pre-wrap">
            {data.draft_proposal.slice(0, 300)}{data.draft_proposal.length > 300 ? "..." : ""}
          </p>
        </div>
      )}
    </div>
  );
}

function VerifyCard({ data }: { data: Record<string, any> }) {
  const score = data.grounding_score || 0;
  const supported = data.supported_claims || [];
  const unsupported = data.unsupported_claims || [];
  const scoreColor = score >= 0.7 ? "text-emerald-400" : score >= 0.5 ? "text-amber-400" : "text-red-400";
  const barColor = score >= 0.7 ? "bg-emerald-400" : score >= 0.5 ? "bg-amber-400" : "bg-red-400";

  return (
    <div className="space-y-3">
      {/* Score display */}
      <div className="flex items-center gap-4">
        <span className={`text-3xl font-bold font-mono ${scoreColor}`}>
          {(score * 100).toFixed(0)}%
        </span>
        <div className="flex-1">
          <div className="score-bar">
            <div className={`score-bar-fill ${barColor}`} style={{ width: `${score * 100}%` }} />
          </div>
          <p className="text-xs text-[var(--text-dim)] mt-1">
            {supported.length} supported · {unsupported.length} unsupported of {supported.length + unsupported.length} claims
          </p>
        </div>
      </div>

      {/* Claims */}
      {supported.length > 0 && (
        <div>
          <p className="text-xs font-mono text-emerald-400 mb-1.5">Supported Claims</p>
          <div className="space-y-1">
            {supported.map((c: string, i: number) => (
              <div key={i} className="flex items-start gap-2 text-xs text-[var(--text-secondary)]">
                <span className="text-emerald-400 mt-0.5 flex-shrink-0">✓</span>
                <span>{c}</span>
              </div>
            ))}
          </div>
        </div>
      )}
      {unsupported.length > 0 && (
        <div>
          <p className="text-xs font-mono text-red-400 mb-1.5">Unsupported (Hallucinated) Claims</p>
          <div className="space-y-1">
            {unsupported.map((c: string, i: number) => (
              <div key={i} className="flex items-start gap-2 text-xs text-[var(--text-secondary)]">
                <span className="text-red-400 mt-0.5 flex-shrink-0">✗</span>
                <span>{c}</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

function BiasCard({ data }: { data: Record<string, any> }) {
  const evaluation = data.bias_evaluation || {};
  const isBiased = evaluation.is_biased;
  const pairs = evaluation.pair_evaluations || [];
  const profiles = evaluation.control_profiles || [];

  return (
    <div className="space-y-3">
      {/* Overall result */}
      <div className="flex items-center gap-3">
        <span className={`text-sm font-bold font-mono px-3 py-1 rounded-full ${
          isBiased
            ? "bg-red-400/10 text-red-400 border border-red-400/20"
            : "bg-emerald-400/10 text-emerald-400 border border-emerald-400/20"
        }`}>
          {isBiased ? "Bias Detected" : "No Bias Detected"}
        </span>
        <span className="text-xs font-mono text-[var(--text-dim)]">
          Score: {evaluation.final_score?.toFixed(4)}
        </span>
      </div>

      {/* Demographic profiles tested */}
      {profiles.length > 0 && (
        <div>
          <p className="text-xs font-mono text-purple-400 mb-2">Counterfactual Profiles Tested</p>
          <div className="grid grid-cols-3 gap-2">
            {profiles.map((p: any, i: number) => (
              <div key={i} className="p-2 rounded bg-[var(--bg-primary)] border border-[var(--border)] text-center">
                <p className="text-xs font-semibold text-[var(--text-primary)]">{p.profile.name}</p>
                <p className="text-[10px] text-[var(--text-dim)]">{p.profile.location}</p>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Per-pair metrics */}
      {pairs.length > 0 && (
        <div>
          <p className="text-xs font-mono text-purple-400 mb-2">Dimension Comparisons</p>
          <div className="space-y-2">
            {pairs.map((pair: any, i: number) => (
              <div key={i} className="p-2 rounded bg-[var(--bg-primary)] border border-[var(--border)]">
                <p className="text-xs font-mono text-[var(--text-secondary)] mb-1.5">{pair.label}</p>
                <div className="grid grid-cols-4 gap-2">
                  {Object.entries(pair.metrics || {}).map(([key, val]: [string, any]) => {
                    const threshold = evaluation.thresholds?.[key];
                    const isViolation = key === "similarity"
                      ? val < threshold
                      : Math.abs(val) > threshold;
                    return (
                      <div key={key} className="text-center">
                        <p className="text-[10px] text-[var(--text-dim)] uppercase">{key.replace("_", " ")}</p>
                        <p className={`text-xs font-mono font-bold ${isViolation ? "text-red-400" : "text-emerald-400"}`}>
                          {typeof val === "number" ? val.toFixed(3) : val}
                        </p>
                      </div>
                    );
                  })}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Debiasing instructions */}
      {evaluation.debiasing_instructions?.length > 0 && (
        <div className="p-2 rounded bg-red-400/5 border border-red-400/10">
          <p className="text-xs font-mono text-red-400 mb-1">Debiasing Instructions</p>
          {evaluation.debiasing_instructions.map((inst: string, i: number) => (
            <p key={i} className="text-xs text-[var(--text-secondary)] ml-2">• {inst}</p>
          ))}
        </div>
      )}
    </div>
  );
}

function RetryCard({ data }: { data: Record<string, any> }) {
  return (
    <div>
      <p className="text-sm text-orange-400">
        Retry count: {data.retry_count} — regenerating proposal with adjustments
      </p>
    </div>
  );
}

export default function NodeResults({ events }: { events: NodeEvent[] }) {
  if (events.length === 0) return null;

  return (
    <div className="space-y-3 w-full">
      {events.map((event, i) => {
        const meta = NODE_META[event.node];
        if (!meta) return null;

        return (
          <div
            key={`${event.node}-${event.timestamp}`}
            className={`rounded-xl border border-[var(--border)] bg-[var(--bg-card)] overflow-hidden animate-fade-in-up`}
            style={{ animationDelay: `${i * 0.05}s` }}
          >
            {/* Accent top bar */}
            <div className={`h-0.5 ${meta.accentBg}`} style={{ background: `var(--${event.node === "retrieve" ? "cyan" : event.node === "generate" ? "blue" : event.node === "verify" ? "amber" : event.node === "bias_check" ? "purple" : event.node === "increment_retry" ? "orange" : "green"})` }} />

            {/* Header */}
            <div className="px-5 py-3 flex items-center gap-3 border-b border-[var(--border)]">
              <span className="text-lg">{meta.icon}</span>
              <span className={`text-sm font-semibold ${meta.accent}`}>{meta.label}</span>
              <span className="text-[10px] font-mono text-[var(--text-dim)] ml-auto">
                {new Date(event.timestamp).toLocaleTimeString()}
              </span>
            </div>

            {/* Content */}
            <div className="px-5 py-4">
              {event.node === "retrieve" && <RetrieveCard data={event.data} />}
              {event.node === "generate" && <GenerateCard data={event.data} />}
              {event.node === "verify" && <VerifyCard data={event.data} />}
              {event.node === "bias_check" && <BiasCard data={event.data} />}
              {event.node === "increment_retry" && <RetryCard data={event.data} />}
            </div>
          </div>
        );
      })}
    </div>
  );
}
