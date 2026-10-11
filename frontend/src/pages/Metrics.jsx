// AI metrics: classifier vs LLM accuracy, confusion matrix, time model error, LLM latency and cost.
import { useEffect, useState } from "react";
import { api } from "../api.js";
import { categoryLabel, formatDate } from "../constants.js";
import { ChartCard, CompareBars, StatTile } from "../components/charts.jsx";

const pct = (v) => (v == null ? null : Math.round(v * 1000) / 10);

// Sequential blue ramp (light -> dark) for the heatmap; text flips to white on dark cells.
const RAMP = ["#cde2fb", "#9ec5f4", "#6da7ec", "#3987e5", "#256abf", "#184f95", "#0d366b"];

function ConfusionMatrix({ labels, matrix }) {
  const max = Math.max(1, ...matrix.flat());
  return (
    <div className="table-scroll">
      <table className="matrix">
        <thead>
          <tr>
            <th className="corner">True ↓ / Predicted →</th>
            {/* Short column names keep the matrix narrow; the full name is in the tooltip. */}
            {labels.map((l) => <th key={l} title={categoryLabel(l)}>{l.slice(0, 5)}</th>)}
          </tr>
        </thead>
        <tbody>
          {matrix.map((row, i) => (
            <tr key={labels[i]}>
              <th title={categoryLabel(labels[i])}>{labels[i]}</th>
              {row.map((value, j) => {
                const step = value === 0 ? -1 : Math.min(RAMP.length - 1, Math.floor((value / max) * (RAMP.length - 1)));
                const style = step < 0 ? {} : { background: RAMP[step], color: step >= 3 ? "#ffffff" : "#0b0b0b" };
                return (
                  <td key={j} style={style} className={i === j ? "diagonal" : ""}
                      title={`True ${labels[i]}, predicted ${labels[j]}: ${value}`}>
                    {value || ""}
                  </td>
                );
              })}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export default function Metrics() {
  const [data, setData] = useState(null);
  const [error, setError] = useState("");

  useEffect(() => {
    api("/metrics/").then(setData).catch((err) => setError(err.message));
  }, []);

  if (error) return <div className="alert error">{error}</div>;
  if (!data) return <p className="muted">Loading…</p>;

  const clf = data.models.classifier?.metrics;
  const llm = data.models.llm_intake?.metrics;
  const time = data.models.time_model?.metrics;
  const comparison = ["accuracy", "precision", "recall", "f1"].map((m) => ({
    metric: m === "f1" ? "F1" : m[0].toUpperCase() + m.slice(1),
    classifier: pct(clf?.[m]),
    llm: pct(llm?.[m]),
  }));
  const calls = data.llm;

  return (
    <div>
      <div className="page-head">
        <h1>AI metrics</h1>
        {data.models.classifier && <span className="muted small">Last evaluation {formatDate(data.models.classifier.created_at)}</span>}
      </div>

      {!clf && <div className="alert warning">No evaluation yet. Run <code>python manage.py train_models</code>.</div>}

      {clf && (
        <ChartCard title="Classifier vs LLM" subtitle={`Same held-out test data · classifier on ${data.models.classifier.n_test} rows${llm ? `, LLM on ${data.models.llm_intake.n_test}` : ""}`}
                   rows={comparison.map((r) => ({ ...r, classifier: r.classifier ?? "—", llm: r.llm ?? "—" }))}
                   columns={[["metric", "Metric"], ["classifier", "Classifier %"], ["llm", "LLM %"]]}>
          <CompareBars data={comparison} series={llm ? [["classifier", "Classifier (TF-IDF + LR)"], ["llm", "LLM"]] : [["classifier", "Classifier (TF-IDF + LR)"]]} />
          {!llm && <p className="muted small">No LLM evaluation yet. With an API key, run <code>python manage.py train_models --llm-sample 40</code>.</p>}
        </ChartCard>
      )}

      <div className="grid-2">
        {clf && (
          <ChartCard title="Classifier confusion matrix" subtitle="Rows = true department, columns = predicted. The diagonal is correct."
                     rows={clf.labels.map((l, i) => ({ label: l, correct: clf.confusion_matrix[i][i], total: clf.confusion_matrix[i].reduce((a, b) => a + b, 0) }))}
                     columns={[["label", "Department"], ["correct", "Correct"], ["total", "Total"]]}>
            <ConfusionMatrix labels={clf.labels} matrix={clf.confusion_matrix} />
          </ChartCard>
        )}

        <section className="card">
          <h3>Resolution-time model</h3>
          {time ? (
            <div className="tiles">
              <StatTile label="Average error" value={`${time.mae_days} days`} hint={`Guessing the average: ${time.baseline_mae_days} days`} />
              <StatTile label="R²" value={time.r2} hint="1.0 = perfect" />
            </div>
          ) : <p className="muted">Not evaluated yet.</p>}

          <h3>LLM vs classifier on real submissions</h3>
          <div className="tiles">
            <StatTile label="Agreement" value={data.agreement.agreement_rate == null ? "—" : `${pct(data.agreement.agreement_rate)}%`}
                      hint={`${data.agreement.complaints_with_both} complaints with both answers`} />
            <StatTile label="Open, needs review" value={data.agreement.needs_review_open} />
          </div>
        </section>
      </div>

      <section className="card">
        <h3>LLM latency and cost</h3>
        {calls.calls ? (
          <>
            <div className="tiles">
              <StatTile label="Calls" value={calls.calls.toLocaleString()} hint={`${pct(calls.success_rate)}% succeeded`} />
              <StatTile label="Average latency" value={`${(calls.avg_latency_ms / 1000).toFixed(2)} s`} hint={`p95 ${(calls.p95_latency_ms / 1000).toFixed(2)} s`} />
              <StatTile label="Total cost" value={`$${calls.total_cost_usd.toFixed(4)}`} hint={`$${calls.avg_cost_usd.toFixed(5)} per call`} />
              <StatTile label="Tokens" value={(calls.input_tokens + calls.output_tokens).toLocaleString()} hint={`${calls.input_tokens.toLocaleString()} in · ${calls.output_tokens.toLocaleString()} out`} />
            </div>
            <table className="table compact">
              <thead><tr><th>Purpose</th><th className="num">Calls</th><th className="num">Cost (USD)</th></tr></thead>
              <tbody>
                {Object.entries(calls.by_purpose).map(([purpose, row]) => (
                  <tr key={purpose}><td>{purpose}</td><td className="num">{row.calls}</td><td className="num">{row.cost_usd.toFixed(5)}</td></tr>
                ))}
              </tbody>
            </table>
          </>
        ) : (
          <p className="muted">No LLM calls logged yet (the LLM may be turned off; the app is using the classifier).</p>
        )}
      </section>
    </div>
  );
}
