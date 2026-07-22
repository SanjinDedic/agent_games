import React from 'react';

const verdictColor = (verdict) => {
  switch (verdict) {
    case "organic":
    case "unlikely":
    case "low":
    case "none":
    case "normal":
      return "text-green-600";
    case "suspicious":
    case "possible":
    case "medium":
    case "probable_plagiarism":
      return "text-yellow-600";
    case "clearly_copied":
    case "likely":
    case "highly_likely":
    case "high":
    case "likely_plagiarism":
    case "highly_suspicious":
      return "text-red-600";
    case "not_applicable":
      return "text-gray-500";
    default:
      return "text-ui-dark";
  }
};

const formatConcernLabel = (level) => {
  if (level === "likely_plagiarism") return "most likely plagiarising";
  if (level === "probable_plagiarism") return "probably plagiarising";
  return "no concerns";
};

/**
 * A horizontal bar with colored zones and a dot marker showing the actual value.
 * zones: [{end: number, bg: string}] — cumulative thresholds left-to-right.
 */
const ContinuumBar = ({ value, max, zones, unit = "" }) => {
  const clamped = Math.min(Math.max(value ?? 0, 0), max);
  const pct = (clamped / max) * 100;

  return (
    <div className="flex items-center gap-2 mb-1">
      <div className="flex-1 h-3 rounded-full overflow-hidden relative flex border border-gray-300">
        {zones.map((zone, i) => {
          const prevEnd = i === 0 ? 0 : zones[i - 1].end;
          const width = ((zone.end - prevEnd) / max) * 100;
          return (
            <div key={i} className={`h-full ${zone.bg}`} style={{ width: `${width}%` }} />
          );
        })}
        {/* Marker dot */}
        {value != null && (
          <div
            className="absolute top-1/2 -translate-y-1/2 -translate-x-1/2 w-3.5 h-3.5 bg-gray-800 rounded-full border-2 border-white shadow"
            style={{ left: `${pct}%` }}
          />
        )}
      </div>
      <span className="text-xs font-mono w-20 text-right text-gray-700">
        {value != null ? `${value}${unit}` : "n/a"}
      </span>
    </div>
  );
};

// Zone definitions for each metric
const CPS_ZONES = [
  { end: 4, bg: "bg-green-200" },
  { end: 6, bg: "bg-yellow-200" },
  { end: 8, bg: "bg-red-300" },
];
const CPS_MAX = 8;

const AST_ZONES = [
  { end: 8, bg: "bg-green-200" },
  { end: 15, bg: "bg-yellow-200" },
  { end: 20, bg: "bg-red-300" },
];
const AST_MAX = 20;

// Template similarity is inverted (high = good): Red → Yellow → Green
const TEMPLATE_ZONES = [
  { end: 30, bg: "bg-red-300" },
  { end: 50, bg: "bg-yellow-200" },
  { end: 100, bg: "bg-green-200" },
];
const TEMPLATE_MAX = 100;

/** Modal rendering a PlagiarismReport from POST /ai/assess-plagiarism. */
const PlagiarismReportModal = ({ report, onClose }) => {
  if (!report) return null;

  return (
    <div
      className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-6"
      onClick={onClose}
    >
      <div
        className="bg-white rounded-lg shadow-xl max-w-3xl w-full max-h-[85vh] overflow-y-auto p-6"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex justify-between items-start mb-4">
          <div>
            <h3 className="text-xl font-bold text-ui-dark">
              Assessment: {report.team_name}
            </h3>
            <div className="text-sm text-ui mt-1">
              {report.submission_count_analyzed} of{" "}
              {report.submission_count_total} submissions analyzed
              {report.sampled && " (sampled)"} · model: {report.model_used}
            </div>
          </div>
          <button
            onClick={onClose}
            className="text-ui hover:text-ui-dark text-2xl leading-none"
            aria-label="Close"
          >
            ×
          </button>
        </div>

        {/* ===== TOP HALF: Deterministic Analysis ===== */}
        <div className="mb-5 pb-5 border-b border-gray-200">
          <div className="flex items-center gap-2 mb-3">
            <h4 className="font-bold text-gray-800">Deterministic Analysis</h4>
            <span
              className={`text-xs font-semibold px-2 py-0.5 rounded-full ${
                report.deterministic_concern_level === "likely_plagiarism"
                  ? "bg-red-100 text-red-700"
                  : report.deterministic_concern_level === "probable_plagiarism"
                  ? "bg-yellow-100 text-yellow-700"
                  : "bg-green-100 text-green-700"
              }`}
            >
              {formatConcernLabel(report.deterministic_concern_level)}
            </span>
          </div>

          {/* Template similarity (per-submission) */}
          {report.submission_metrics.some((s) => s.template_similarity != null) && (
            <div className="mb-4">
              <div className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-1">
                Template Similarity
              </div>
              {report.submission_metrics.map((sm) =>
                sm.template_similarity != null ? (
                  <div key={sm.index} className="flex items-center gap-2">
                    <span className="text-xs text-gray-500 w-24 shrink-0">
                      submission {sm.index + 1}
                    </span>
                    <div className="flex-1">
                      <ContinuumBar
                        value={Math.round(sm.template_similarity * 100)}
                        max={TEMPLATE_MAX}
                        zones={TEMPLATE_ZONES}
                      />
                    </div>
                  </div>
                ) : null
              )}
            </div>
          )}

          {/* Per-pair bars: chars/sec + AST constructs */}
          {report.pairwise_metrics.length > 0 && (
            <div className="space-y-3">
              {report.pairwise_metrics.map((pm) => (
                <div
                  key={`${pm.from_index}-${pm.to_index}`}
                  className="bg-gray-50 rounded p-3"
                >
                  <div className="text-xs font-semibold text-gray-600 mb-2">
                    submission {pm.from_index + 1} → submission {pm.to_index + 1}
                    <span className="font-normal text-gray-400 ml-2">
                      ({Math.round(pm.elapsed_seconds)}s elapsed ·{" "}
                      +{pm.chars_added} / −{pm.chars_removed} chars)
                    </span>
                  </div>

                  <div className="flex items-center gap-2 mb-1">
                    <span className="text-xs text-gray-500 w-24 shrink-0">
                      Chars / sec
                    </span>
                    <div className="flex-1">
                      <ContinuumBar
                        value={pm.chars_added_per_second}
                        max={CPS_MAX}
                        zones={CPS_ZONES}
                      />
                    </div>
                  </div>

                  <div className="flex items-center gap-2">
                    <span className="text-xs text-gray-500 w-24 shrink-0">
                      Complexity Δ
                    </span>
                    <div className="flex-1">
                      <ContinuumBar
                        value={pm.constructs_added}
                        max={AST_MAX}
                        zones={AST_ZONES}
                      />
                    </div>
                  </div>

                  {pm.new_construct_types && pm.new_construct_types.length > 0 && (
                    <div className="text-[11px] text-gray-400 mt-1 ml-26">
                      New: {pm.new_construct_types.join(", ")}
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}

          {/* Text summary of all deterministic flags */}
          {report.deterministic_flag_summary &&
            report.deterministic_flag_summary.length > 0 && (
              <div className="mt-3 text-xs text-gray-600">
                <div className="font-semibold mb-1">Summary:</div>
                <ul className="list-disc ml-5 space-y-0.5">
                  {report.deterministic_flag_summary.map((line, i) => (
                    <li key={i}>{line}</li>
                  ))}
                </ul>
              </div>
            )}
        </div>

        {/* ===== BOTTOM HALF: LLM Verdict ===== */}
        <div>
          <h4 className="font-bold text-gray-800 mb-3">AI Analysis</h4>

          <div className="mb-3">
            <div className="font-semibold text-ui-dark mb-1">
              Progression:{" "}
              <span className={verdictColor(report.verdict.progression_verdict)}>
                {report.verdict.progression_verdict}
              </span>
            </div>
            <p className="text-sm text-ui-dark whitespace-pre-wrap">
              {report.verdict.progression_reasoning}
            </p>
          </div>

          <div className="mb-3">
            <div className="font-semibold text-ui-dark mb-1">
              AI-generated:{" "}
              <span className={verdictColor(report.verdict.ai_generation_verdict)}>
                {report.verdict.ai_generation_verdict}
              </span>
            </div>
            <p className="text-sm text-ui-dark whitespace-pre-wrap">
              {report.verdict.ai_generation_reasoning}
            </p>
          </div>

          <div className="mb-3">
            <div className="font-semibold text-ui-dark">
              Overall concern:{" "}
              <span className={verdictColor(report.verdict.overall_concern_level)}>
                {report.verdict.overall_concern_level}
              </span>
            </div>
          </div>

          {report.verdict.specific_flags &&
            report.verdict.specific_flags.length > 0 && (
              <div className="mb-3">
                <div className="font-semibold text-ui-dark mb-1">Flags:</div>
                <ul className="list-disc ml-5 text-sm text-ui-dark">
                  {report.verdict.specific_flags.map((f, i) => (
                    <li key={i}>{f}</li>
                  ))}
                </ul>
              </div>
            )}
        </div>

        <details className="mt-4 text-xs border-t border-gray-200 pt-3">
          <summary className="cursor-pointer font-semibold text-ui-dark">
            Raw metrics
          </summary>
          <pre className="bg-gray-100 p-3 mt-2 rounded overflow-x-auto text-[11px]">
            {"Per-submission metrics:\n"}
            {JSON.stringify(report.submission_metrics, null, 2)}
            {"\n\nPairwise metrics:\n"}
            {JSON.stringify(report.pairwise_metrics, null, 2)}
          </pre>
        </details>

        <button
          onClick={onClose}
          className="mt-4 px-4 py-2 bg-primary text-white rounded hover:bg-primary-hover transition-colors"
        >
          Close
        </button>
      </div>
    </div>
  );
};

export default PlagiarismReportModal;
