export type PipelineStatus = "idle" | "streaming" | "reviewing" | "resuming" | "complete" | "error";

export type NodeName = "retrieve" | "generate" | "verify" | "bias_check" | "human_review" | "increment_retry";

export interface NodeEvent {
  node: NodeName;
  data: Record<string, any>;
  timestamp: number;
}

export interface RetrievalResult {
  text: string;
  full_text: string;
  score: number;
  source: string;
  metadata: Record<string, any>;
}

export interface GenerationMetadata {
  model: string;
  attempt: number;
  feedback_used: string | null;
  prompt_length: number;
  proposal_length: number;
  past_proposals_used: number;
  tokens: {
    prompt_tokens?: number;
    completion_tokens?: number;
    total_tokens?: number;
  };
}

export interface BiasEvaluation {
  is_biased: boolean;
  final_score: number;
  baseline_profile: Record<string, string>;
  control_profiles: Array<{
    label: string;
    profile: Record<string, string>;
    proposal_preview: string;
  }>;
  pair_evaluations: Array<{
    label: string;
    bias_score: number;
    violations: number;
    metrics: {
      price_diff: number;
      tone_diff: number;
      similarity: number;
      length_diff: number;
    };
    baseline_stats: Record<string, any>;
    control_stats: Record<string, any>;
    flags: string[];
  }>;
  thresholds: {
    price_diff: number;
    tone_diff: number;
    similarity: number;
    length_diff: number;
  };
  debiasing_instructions: string[];
  total_flags: number;
}

export interface InterruptData {
  thread_id: string;
  proposal: string;
  grounding_score: number;
  extracted_claims: string[];
  supported_claims: string[];
  unsupported_claims: string[];
  bias_flags: string[];
  bias_evaluation: BiasEvaluation;
  retrieval_results: RetrievalResult[];
  generation_metadata: GenerationMetadata;
  retry_count: number;
  status: string;
}
