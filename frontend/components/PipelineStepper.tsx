"use client";

const NODES = [
  { key: "retrieve", label: "Retrieve", icon: "🔍", color: "text-cyan-400 border-cyan-400/30 bg-cyan-400/5" },
  { key: "generate", label: "Generate", icon: "✍️", color: "text-blue-400 border-blue-400/30 bg-blue-400/5" },
  { key: "verify", label: "Verify", icon: "✅", color: "text-amber-400 border-amber-400/30 bg-amber-400/5" },
  { key: "bias_check", label: "Bias Check", icon: "⚖️", color: "text-purple-400 border-purple-400/30 bg-purple-400/5" },
  { key: "human_review", label: "Review", icon: "👤", color: "text-emerald-400 border-emerald-400/30 bg-emerald-400/5" },
];

interface PipelineStepperProps {
  completedNodes: string[];
  activeNode: string | null;
}

export default function PipelineStepper({ completedNodes, activeNode }: PipelineStepperProps) {
  return (
    <div className="flex items-center justify-between gap-2 w-full max-w-3xl mx-auto">
      {NODES.map((node, i) => {
        const isCompleted = completedNodes.includes(node.key);
        const isActive = activeNode === node.key;
        const isPending = !isCompleted && !isActive;

        return (
          <div key={node.key} className="flex items-center flex-1">
            <div
              className={`
                flex flex-col items-center gap-1.5 flex-1 py-3 px-2 rounded-xl border transition-all duration-500
                ${isActive ? `${node.color} animate-pulse-glow` : ""}
                ${isCompleted ? `${node.color} opacity-100` : ""}
                ${isPending ? "border-[var(--border)] bg-[var(--bg-card)] opacity-40" : ""}
              `}
            >
              <span className="text-xl">{node.icon}</span>
              <span className={`text-[11px] font-semibold tracking-wide uppercase font-mono ${isPending ? "text-[var(--text-dim)]" : ""}`}>
                {node.label}
              </span>
              {isCompleted && (
                <span className="text-[9px] font-mono text-emerald-400">Done</span>
              )}
              {isActive && (
                <span className="text-[9px] font-mono text-cyan-400">Running...</span>
              )}
            </div>
            {i < NODES.length - 1 && (
              <div className={`w-6 h-px mx-1 flex-shrink-0 ${isCompleted ? "bg-[var(--border-hover)]" : "bg-[var(--border)]"}`} />
            )}
          </div>
        );
      })}
    </div>
  );
}
