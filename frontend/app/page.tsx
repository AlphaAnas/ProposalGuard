"use client";

import { useState, useRef } from "react";
import {
  startPipeline,
  resumePipeline,
  uploadResume,
  uploadProposal,
} from "@/lib/api";
import { PipelineStatus, NodeEvent, InterruptData } from "@/types";
import PipelineStepper from "@/components/PipelineStepper";
import NodeResults from "@/components/NodeResults";
import ReviewPanel from "@/components/ReviewPanel";

export default function Home() {
  const [status, setStatus] = useState<PipelineStatus>("idle");
  const [jobDescription, setJobDescription] = useState("");
  const [threadId, setThreadId] = useState<string | null>(null);
  const [nodeEvents, setNodeEvents] = useState<NodeEvent[]>([]);
  const [completedNodes, setCompletedNodes] = useState<string[]>([]);
  const [activeNode, setActiveNode] = useState<string | null>(null);
  const [interruptData, setInterruptData] = useState<InterruptData | null>(
    null,
  );
  const [finalResult, setFinalResult] = useState<any>(null);
  const [error, setError] = useState<string | null>(null);
  const scrollRef = useRef<HTMLDivElement>(null);

  // Upload state
  const [resumeFile, setResumeFile] = useState<File | null>(null);
  const [resumeStatus, setResumeStatus] = useState<
    "idle" | "uploading" | "done" | "error"
  >("idle");
  const [proposalFiles, setProposalFiles] = useState<File[]>([]);
  const [proposalStatus, setProposalStatus] = useState<
    "idle" | "uploading" | "done" | "error"
  >("idle");
  const [uploadedProposalCount, setUploadedProposalCount] = useState(0);

  const scrollToBottom = () => {
    setTimeout(() => {
      scrollRef.current?.scrollIntoView({ behavior: "smooth" });
    }, 100);
  };

  const handleResumeUpload = async () => {
    if (!resumeFile) return;
    setResumeStatus("uploading");
    try {
      await uploadResume(resumeFile);
      setResumeStatus("done");
    } catch (e: any) {
      setError(e.message);
      setResumeStatus("error");
    }
  };

  const handleProposalUpload = async () => {
    if (proposalFiles.length === 0) return;
    setProposalStatus("uploading");
    try {
      let count = 0;
      for (const file of proposalFiles) {
        await uploadProposal(file);
        count++;
      }
      setUploadedProposalCount(count);
      setProposalStatus("done");
    } catch (e: any) {
      setError(e.message);
      setProposalStatus("error");
    }
  };

  const handleGenerate = async () => {
    if (!jobDescription.trim()) return;

    setStatus("streaming");
    setNodeEvents([]);
    setCompletedNodes([]);
    setActiveNode("retrieve");
    setInterruptData(null);
    setFinalResult(null);
    setError(null);

    const nodeOrder = [
      "retrieve",
      "generate",
      "verify",
      "bias_check",
      "human_review",
    ];

    await startPipeline(jobDescription, {
      onThreadId: (id) => setThreadId(id),

      onNodeComplete: (node, data) => {
        const event: NodeEvent = {
          node: node as any,
          data,
          timestamp: Date.now(),
        };
        setNodeEvents((prev) => [...prev, event]);
        setCompletedNodes((prev) => [...new Set([...prev, node])]);

        const currentIndex = nodeOrder.indexOf(node);
        if (currentIndex < nodeOrder.length - 1) {
          setActiveNode(nodeOrder[currentIndex + 1]);
        } else {
          setActiveNode(null);
        }
        scrollToBottom();
      },

      onInterrupt: (data) => {
        setInterruptData(data);
        setStatus("reviewing");
        setActiveNode("human_review");
        scrollToBottom();
      },

      onComplete: (data) => {
        setFinalResult(data);
        setStatus("complete");
        setActiveNode(null);
        scrollToBottom();
      },

      onError: (err) => {
        setError(err);
        setStatus("error");
      },
    });
  };

  const handleApprove = async () => {
    if (!threadId) return;
    setStatus("resuming");
    try {
      const result = await resumePipeline(threadId, "approve");
      setFinalResult(result);
      setStatus("complete");
      setCompletedNodes((prev) => [...new Set([...prev, "human_review"])]);
      scrollToBottom();
    } catch (e: any) {
      setError(e.message);
      setStatus("error");
    }
  };

  const handleReject = async (feedback: string) => {
    if (!threadId) return;
    setStatus("resuming");
    try {
      const result = await resumePipeline(threadId, "reject", feedback);
      setFinalResult(result);
      setStatus("complete");
      scrollToBottom();
    } catch (e: any) {
      setError(e.message);
      setStatus("error");
    }
  };

  const handleReset = () => {
    setStatus("idle");
    setJobDescription("");
    setThreadId(null);
    setNodeEvents([]);
    setCompletedNodes([]);
    setActiveNode(null);
    setInterruptData(null);
    setFinalResult(null);
    setError(null);
  };

  return (
    <main className="min-h-screen">
      {/* Header */}
      <header className="border-b border-[var(--border)] bg-[var(--bg-card)]/50 backdrop-blur-sm sticky top-0 z-50">
        <div className="max-w-5xl mx-auto px-6 py-4 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-2 h-2 rounded-full bg-cyan-400" />
            <h1 className="text-lg font-bold tracking-tight">
              Proposal<span className="text-cyan-400">Guard</span>
            </h1>
          </div>
          {status !== "idle" && (
            <button
              onClick={handleReset}
              className="text-xs font-mono text-[var(--text-dim)] hover:text-[var(--text-secondary)] transition-colors px-3 py-1.5 rounded border border-[var(--border)] hover:border-[var(--border-hover)]"
            >
              New Proposal
            </button>
          )}
        </div>
      </header>

      <div className="max-w-5xl mx-auto px-6 py-8">
        {/* ============================================ */}
        {/* IDLE: Input Form */}
        {/* ============================================ */}
        {status === "idle" && (
          <div className="animate-fade-in-up max-w-2xl mx-auto">
            <div className="text-center mb-10">
              <p className="text-xs font-mono text-cyan-400 tracking-widest uppercase mb-3">
                AI-Powered Proposal Generator
              </p>
              <h2 className="text-4xl font-extrabold tracking-tight mb-4">
                Proposal<span className="text-cyan-400">Guard</span>
              </h2>
              <p className="text-[var(--text-secondary)] max-w-md mx-auto leading-relaxed">
                Generate personalized proposals grounded in your real
                experience. Every claim verified. Bias detected. Human approved.
              </p>
            </div>

            {/* Upload Section */}
            <div className="rounded-xl border border-[var(--border)] bg-[var(--bg-card)] p-6 mb-4">
              <p className="text-xs font-mono text-[var(--text-dim)] uppercase tracking-wider mb-4">
                Upload Your Data
              </p>

              <div className="grid grid-cols-2 gap-4">
                {/* Resume Upload */}
                <div className="p-4 rounded-lg bg-[var(--bg-primary)] border border-[var(--border)]">
                  <div className="flex items-center gap-2 mb-3">
                    <span className="text-lg">📄</span>
                    <span className="text-sm font-semibold">Resume</span>
                    {resumeStatus === "done" && (
                      <span className="text-[10px] font-mono text-emerald-400 ml-auto px-2 py-0.5 rounded-full bg-emerald-400/10 border border-emerald-400/20">
                        Uploaded
                      </span>
                    )}
                  </div>
                  <input
                    type="file"
                    accept=".txt"
                    onChange={(e) => setResumeFile(e.target.files?.[0] || null)}
                    className="block w-full text-xs text-[var(--text-dim)] file:mr-3 file:py-1.5 file:px-3 file:rounded file:border file:border-[var(--border)] file:text-xs file:font-mono file:text-[var(--text-secondary)] file:bg-[var(--bg-elevated)] file:cursor-pointer hover:file:border-[var(--border-hover)]"
                  />
                  {resumeFile && resumeStatus !== "done" && (
                    <button
                      onClick={handleResumeUpload}
                      disabled={resumeStatus === "uploading"}
                      className="mt-2 w-full py-1.5 text-xs font-mono rounded bg-cyan-500/20 text-cyan-400 border border-cyan-400/20 hover:bg-cyan-500/30 transition-colors disabled:opacity-50"
                    >
                      {resumeStatus === "uploading"
                        ? "Uploading..."
                        : "Upload Resume"}
                    </button>
                  )}
                  {resumeStatus === "error" && (
                    <p className="text-[10px] text-red-400 mt-1">
                      Upload failed. Try again.
                    </p>
                  )}
                </div>

                {/* Proposals Upload */}
                <div className="p-4 rounded-lg bg-[var(--bg-primary)] border border-[var(--border)]">
                  <div className="flex items-center gap-2 mb-3">
                    <span className="text-lg">📝</span>
                    <span className="text-sm font-semibold">
                      Past Proposals
                    </span>
                    {proposalStatus === "done" && (
                      <span className="text-[10px] font-mono text-emerald-400 ml-auto px-2 py-0.5 rounded-full bg-emerald-400/10 border border-emerald-400/20">
                        {uploadedProposalCount} uploaded
                      </span>
                    )}
                  </div>
                  <input
                    type="file"
                    accept=".txt"
                    multiple
                    onChange={(e) =>
                      setProposalFiles(Array.from(e.target.files || []))
                    }
                    className="block w-full text-xs text-[var(--text-dim)] file:mr-3 file:py-1.5 file:px-3 file:rounded file:border file:border-[var(--border)] file:text-xs file:font-mono file:text-[var(--text-secondary)] file:bg-[var(--bg-elevated)] file:cursor-pointer hover:file:border-[var(--border-hover)]"
                  />
                  {proposalFiles.length > 0 && proposalStatus !== "done" && (
                    <button
                      onClick={handleProposalUpload}
                      disabled={proposalStatus === "uploading"}
                      className="mt-2 w-full py-1.5 text-xs font-mono rounded bg-purple-500/20 text-purple-400 border border-purple-400/20 hover:bg-purple-500/30 transition-colors disabled:opacity-50"
                    >
                      {proposalStatus === "uploading"
                        ? "Uploading..."
                        : `Upload ${proposalFiles.length} Proposal${proposalFiles.length > 1 ? "s" : ""}`}
                    </button>
                  )}
                  {proposalStatus === "error" && (
                    <p className="text-[10px] text-red-400 mt-1">
                      Upload failed. Try again.
                    </p>
                  )}
                </div>
              </div>

              <p className="text-[10px] text-[var(--text-dim)] mt-3 text-center">
                .txt files only · Resume is saved on the server · Proposals are
                added to the vector database
              </p>
            </div>

            {/* Job Description Input */}
            <div className="rounded-xl border border-[var(--border)] bg-[var(--bg-card)] p-6">
              <label className="block text-xs font-mono text-[var(--text-dim)] uppercase tracking-wider mb-3">
                Paste the job posting
              </label>
              <textarea
                value={jobDescription}
                onChange={(e) => setJobDescription(e.target.value)}
                placeholder="Looking for a senior full-stack developer to build an AI-powered customer support dashboard..."
                rows={8}
                className="w-full p-4 rounded-lg bg-[var(--bg-primary)] border border-[var(--border)] text-sm text-[var(--text-primary)] placeholder:text-[var(--text-dim)] focus:outline-none focus:border-cyan-400/30 resize-none leading-relaxed"
              />

              <button
                onClick={handleGenerate}
                disabled={!jobDescription.trim()}
                className="w-full mt-4 py-3.5 rounded-lg bg-cyan-500 hover:bg-cyan-400 text-white font-semibold text-sm transition-all disabled:opacity-30 disabled:cursor-not-allowed"
              >
                Generate Proposal →
              </button>

              {/* Pipeline preview */}
              <div className="mt-6 pt-5 border-t border-[var(--border)]">
                <p className="text-[10px] font-mono text-[var(--text-dim)] uppercase tracking-wider mb-3 text-center">
                  Pipeline Steps
                </p>
                <div className="flex justify-center gap-3 text-center">
                  {[
                    "🔍 Retrieve",
                    "✍️ Generate",
                    "✅ Verify",
                    "⚖️ Bias Check",
                    "👤 Review",
                  ].map((step) => (
                    <span
                      key={step}
                      className="text-[10px] font-mono text-[var(--text-dim)] px-2 py-1 rounded bg-[var(--bg-elevated)] border border-[var(--border)]"
                    >
                      {step}
                    </span>
                  ))}
                </div>
              </div>
            </div>
          </div>
        )}

        {/* ============================================ */}
        {/* STREAMING / REVIEWING / RESUMING */}
        {/* ============================================ */}
        {(status === "streaming" ||
          status === "reviewing" ||
          status === "resuming") && (
          <div className="space-y-6 animate-fade-in-up">
            <PipelineStepper
              completedNodes={completedNodes}
              activeNode={activeNode}
            />

            {status === "streaming" && activeNode && (
              <div className="rounded-xl border border-[var(--border)] bg-[var(--bg-card)] p-5">
                <div className="flex items-center gap-3 mb-3">
                  <div className="w-2 h-2 rounded-full bg-cyan-400 animate-pulse" />
                  <span className="text-sm text-[var(--text-secondary)]">
                    Running{" "}
                    <span className="font-mono text-cyan-400">
                      {activeNode}
                    </span>
                    ...
                  </span>
                </div>
                <div className="h-3 w-2/3 rounded shimmer" />
              </div>
            )}

            <NodeResults events={nodeEvents} />

            {status === "reviewing" && interruptData && (
              <ReviewPanel
                data={interruptData}
                onApprove={handleApprove}
                onReject={handleReject}
                isLoading={false}
              />
            )}

            {status === "resuming" && (
              <div className="rounded-xl border border-[var(--border)] bg-[var(--bg-card)] p-6 text-center">
                <div className="w-3 h-3 rounded-full bg-cyan-400 animate-pulse mx-auto mb-3" />
                <p className="text-sm text-[var(--text-secondary)]">
                  Processing your decision...
                </p>
              </div>
            )}

            <div ref={scrollRef} />
          </div>
        )}

        {/* ============================================ */}
        {/* COMPLETE */}
        {/* ============================================ */}
        {status === "complete" && finalResult && (
          <div className="space-y-6 animate-fade-in-up max-w-3xl mx-auto">
            <div className="text-center py-6">
              <div className="w-16 h-16 rounded-full bg-emerald-400/10 border border-emerald-400/20 flex items-center justify-center mx-auto mb-4">
                <span className="text-3xl">✓</span>
              </div>
              <h2 className="text-2xl font-bold mb-2">Proposal Approved</h2>
              <p className="text-sm text-[var(--text-secondary)]">
                Grounding score:{" "}
                <span className="font-mono text-emerald-400">
                  {((finalResult.grounding_score || 0) * 100).toFixed(0)}%
                </span>
                {" · "}Retries:{" "}
                <span className="font-mono">
                  {finalResult.retry_count || 0}
                </span>
              </p>
            </div>

            <div className="rounded-xl border border-emerald-400/20 bg-[var(--bg-card)] overflow-hidden">
              <div className="px-6 py-3 bg-emerald-400/5 border-b border-emerald-400/20">
                <p className="text-xs font-mono text-emerald-400 uppercase tracking-wider">
                  Final Proposal
                </p>
              </div>
              <div className="px-6 py-5">
                <p className="text-sm text-[var(--text-primary)] leading-relaxed whitespace-pre-wrap">
                  {finalResult.proposal}
                </p>
              </div>
              <div className="px-6 py-3 border-t border-[var(--border)] flex items-center gap-3">
                <button
                  onClick={() =>
                    navigator.clipboard.writeText(finalResult.proposal)
                  }
                  className="text-xs font-mono text-[var(--text-dim)] hover:text-cyan-400 transition-colors px-3 py-1.5 rounded border border-[var(--border)] hover:border-cyan-400/30"
                >
                  Copy to Clipboard
                </button>
                <button
                  onClick={handleReset}
                  className="text-xs font-mono text-[var(--text-dim)] hover:text-[var(--text-secondary)] transition-colors px-3 py-1.5 rounded border border-[var(--border)] hover:border-[var(--border-hover)]"
                >
                  Generate Another
                </button>
              </div>
            </div>

            {nodeEvents.length > 0 && (
              <details className="rounded-xl border border-[var(--border)] bg-[var(--bg-card)] overflow-hidden">
                <summary className="px-6 py-3 cursor-pointer text-xs font-mono text-[var(--text-dim)] uppercase tracking-wider hover:text-[var(--text-secondary)] transition-colors">
                  View Pipeline Details ({nodeEvents.length} steps)
                </summary>
                <div className="px-6 pb-5">
                  <NodeResults events={nodeEvents} />
                </div>
              </details>
            )}
          </div>
        )}

        {/* ============================================ */}
        {/* ERROR */}
        {/* ============================================ */}
        {status === "error" && (
          <div className="max-w-2xl mx-auto animate-fade-in-up">
            <div className="rounded-xl border border-red-400/20 bg-red-400/5 p-6 text-center">
              <span className="text-3xl mb-3 block">⚠️</span>
              <h3 className="text-lg font-bold text-red-400 mb-2">
                Pipeline Error
              </h3>
              <p className="text-sm text-[var(--text-secondary)] mb-4">
                {error}
              </p>
              <button
                onClick={handleReset}
                className="text-xs font-mono text-red-400 px-4 py-2 rounded border border-red-400/30 hover:bg-red-400/10 transition-colors"
              >
                Try Again
              </button>
            </div>
          </div>
        )}
      </div>
    </main>
  );
}
