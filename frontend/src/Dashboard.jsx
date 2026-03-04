import { useState, useEffect, useRef, useCallback } from "react";

const API_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";

// --- AI-ASSISTED ---
// Tool: Claude Sonnet 4.6
// Prompt: "Redesign dashboard with dual upload zones (base + modified CCF),
//          side-by-side diff view showing score changes, auto-refresh after upload."
// Modifications: Added dual upload zones with distinct visual states,
//                diff highlighting for changed carriers, upload result summary panel,
//                animated score delta indicators, auto-reload after each upload.
// --- END AI-ASSISTED ---

// ─── Service Layer ────────────────────────────────────────────────────────────
const CarrierService = {
  async fetchAll(filters = {}) {
    const params = new URLSearchParams();
    if (filters.minScore) params.set("min_score", filters.minScore);
    if (filters.status) params.set("authority_status", filters.status);
    const res = await fetch(`${API_URL}/api/carriers/?${params}`);
    if (!res.ok) throw new Error("Failed to fetch carriers");
    return res.json();
  },
  async fetchHistory(id) {
    const res = await fetch(`${API_URL}/api/carriers/${id}/history/`);
    if (!res.ok) throw new Error("Failed to fetch history");
    return res.json();
  },
};

const UploadService = {
  async upload(file) {
    const form = new FormData();
    form.append("file", file);
    const res = await fetch(`${API_URL}/api/ccf/upload/`, {
      method: "POST",
      body: form,
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.error || "Upload failed");
    return data;
  },
};

// ─── Hooks ────────────────────────────────────────────────────────────────────
function useCarriers() {
  const [carriers, setCarriers] = useState([]);
  const [meta, setMeta] = useState({ total: 0, at_risk_count: 0 });
  const [loading, setLoading] = useState(false);
  const [prevScores, setPrevScores] = useState({});

  const load = useCallback(async (filters = {}) => {
    setLoading(true);
    try {
      const data = await CarrierService.fetchAll(filters);
      const results = data.results || [];
      // Store previous scores before updating
      setCarriers(prev => {
        const prev_map = {};
        prev.forEach(c => { prev_map[c.carrier_id] = c.score; });
        setPrevScores(prev_map);
        return results;
      });
      setMeta({ total: data.total || 0, at_risk_count: data.at_risk_count || 0 });
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { load(); }, [load]);
  return { carriers, meta, loading, load, prevScores };
}

function useToast() {
  const [toasts, setToasts] = useState([]);
  const add = (msg, type = "success") => {
    const id = Date.now();
    setToasts(t => [...t, { id, msg, type }]);
    setTimeout(() => setToasts(t => t.filter(x => x.id !== id)), 5000);
  };
  return { toasts, success: m => add(m, "success"), error: m => add(m, "error"), info: m => add(m, "info") };
}

// ─── Helpers ──────────────────────────────────────────────────────────────────
const scoreColor = s => s > 70 ? "#00ff9d" : s >= 40 ? "#f5c518" : "#ff3b5c";
const scoreTier  = s => s > 70 ? "SAFE" : s >= 40 ? "CAUTION" : "RISK";

// ─── Score Ring ───────────────────────────────────────────────────────────────
function ScoreRing({ score, size = 52, prevScore = null }) {
  const r = size / 2 - 5;
  const circ = 2 * Math.PI * r;
  const fill = (score / 100) * circ;
  const delta = prevScore !== null ? score - prevScore : null;

  return (
    <div style={{ position: "relative", width: size, height: size }}>
      <svg width={size} height={size} style={{ transform: "rotate(-90deg)" }}>
        <circle cx={size/2} cy={size/2} r={r} fill="none" stroke="#151520" strokeWidth="4.5" />
        <circle cx={size/2} cy={size/2} r={r} fill="none"
          stroke={scoreColor(score)} strokeWidth="4.5"
          strokeDasharray={`${fill} ${circ}`} strokeLinecap="round"
          style={{ transition: "stroke-dasharray 1s cubic-bezier(.4,0,.2,1)" }}
        />
        <text x={size/2} y={size/2} textAnchor="middle" dominantBaseline="central"
          fill={scoreColor(score)} fontSize={size * 0.21}
          fontFamily="'JetBrains Mono', monospace" fontWeight="700"
          style={{ transform: `rotate(90deg)`, transformOrigin: `${size/2}px ${size/2}px` }}>
          {score?.toFixed(0)}
        </text>
      </svg>
      {delta !== null && Math.abs(delta) > 0.1 && (
        <div style={{
          position: "absolute", top: -6, right: -8,
          fontSize: 8, fontFamily: "'JetBrains Mono', monospace",
          color: delta > 0 ? "#00ff9d" : "#ff3b5c",
          background: delta > 0 ? "#00ff9d15" : "#ff3b5c15",
          border: `1px solid ${delta > 0 ? "#00ff9d33" : "#ff3b5c33"}`,
          padding: "1px 4px", borderRadius: 2, letterSpacing: 0.5,
          animation: "popIn 0.4s cubic-bezier(.17,.67,.35,1.4)",
        }}>
          {delta > 0 ? "+" : ""}{delta.toFixed(1)}
        </div>
      )}
    </div>
  );
}

// ─── Dual Upload Zone ─────────────────────────────────────────────────────────
function UploadZone({ label, description, accent, onUpload, result, uploading, fileName }) {
  const [dragging, setDragging] = useState(false);
  const inputRef = useRef();

  const handleFile = f => {
    if (f && f.name.endsWith(".json")) onUpload(f);
  };

  return (
    <div style={{
      flex: 1, border: `1px solid ${dragging ? accent : "#1c1c2e"}`,
      borderRadius: 2, overflow: "hidden",
      background: dragging ? `${accent}06` : "#0a0a15",
      transition: "all 0.2s",
    }}>
      {/* Zone header */}
      <div style={{
        borderBottom: `1px solid #1c1c2e`,
        padding: "12px 16px",
        display: "flex", alignItems: "center", gap: 10,
      }}>
        <div style={{ width: 6, height: 6, borderRadius: "50%", background: accent }} />
        <div>
          <div style={{ fontSize: 10, color: accent, letterSpacing: 2, fontFamily: "'JetBrains Mono', monospace" }}>
            {label}
          </div>
          <div style={{ fontSize: 9, color: "#333", marginTop: 1, fontFamily: "'JetBrains Mono', monospace" }}>
            {description}
          </div>
        </div>
      </div>

      {/* Drop area */}
      <div
        onClick={() => inputRef.current.click()}
        onDragOver={e => { e.preventDefault(); setDragging(true); }}
        onDragLeave={() => setDragging(false)}
        onDrop={e => { e.preventDefault(); setDragging(false); handleFile(e.dataTransfer.files[0]); }}
        style={{
          padding: "20px 16px", cursor: "pointer",
          display: "flex", flexDirection: "column", alignItems: "center", gap: 8,
        }}
      >
        {uploading ? (
          <div style={{ fontSize: 9, color: accent, letterSpacing: 2, fontFamily: "'JetBrains Mono', monospace", animation: "pulse 1s infinite" }}>
            PROCESSING...
          </div>
        ) : fileName ? (
          <div style={{ textAlign: "center" }}>
            <div style={{ fontSize: 9, color: "#444", letterSpacing: 1, fontFamily: "'JetBrains Mono', monospace", marginBottom: 4 }}>
              UPLOADED
            </div>
            <div style={{ fontSize: 10, color: accent, fontFamily: "'JetBrains Mono', monospace" }}>
              {fileName}
            </div>
          </div>
        ) : (
          <>
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none"
              stroke={dragging ? accent : "#2a2a3e"} strokeWidth="1.5">
              <path d="M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4M17 8l-5-5-5 5M12 3v12"
                strokeLinecap="round" strokeLinejoin="round"/>
            </svg>
            <div style={{ fontSize: 9, color: "#2a2a3e", letterSpacing: 1, fontFamily: "'JetBrains Mono', monospace", textAlign: "center" }}>
              DROP .JSON OR CLICK TO SELECT
            </div>
          </>
        )}
        <input ref={inputRef} type="file" accept=".json" style={{ display: "none" }}
          onChange={e => handleFile(e.target.files[0])} />
      </div>

      {/* Result summary */}
      {result && (
        <div style={{ borderTop: "1px solid #1c1c2e", padding: "12px 16px" }}>
          <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 6 }}>
            {[
              { k: "NEW",       v: result.new_count,       c: "#00ff9d" },
              { k: "UPDATED",   v: result.updated_count,   c: "#f5c518" },
              { k: "UNCHANGED", v: result.unchanged_count, c: "#555" },
              { k: "ERRORS",    v: result.error_count,     c: "#ff3b5c" },
            ].map(({ k, v, c }) => (
              <div key={k} style={{ textAlign: "center" }}>
                <div style={{ fontSize: 16, fontFamily: "'Bebas Neue', sans-serif", color: v > 0 ? c : "#222", letterSpacing: 1 }}>
                  {v}
                </div>
                <div style={{ fontSize: 8, color: "#333", letterSpacing: 1, fontFamily: "'JetBrains Mono', monospace" }}>
                  {k}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

// ─── Detail Panel ─────────────────────────────────────────────────────────────
function DetailPanel({ carrier, prevScore, onClose }) {
  const [history, setHistory] = useState([]);
  const bd = carrier.score_breakdown || {};
  const delta = prevScore !== null && prevScore !== undefined ? carrier.score - prevScore : null;

  useEffect(() => {
    CarrierService.fetchHistory(carrier.id)
      .then(d => setHistory(d.history || []))
      .catch(() => {});
  }, [carrier.id]);

  const bars = [
    { label: "Safety Rating",  value: bd.safety_rating_score,     max: 25 },
    { label: "OOS %",          value: bd.oos_pct_score,           max: 20 },
    { label: "Crash Total",    value: bd.crash_total_score,       max: 20 },
    { label: "Driver OOS %",   value: bd.driver_oos_pct_score,    max: 15 },
    { label: "Insurance",      value: bd.insurance_score,         max: 10 },
    { label: "Authority",      value: bd.authority_status_score,  max: 10 },
  ];

  return (
    <div style={{
      position: "fixed", inset: 0, background: "rgba(0,0,0,0.88)",
      display: "flex", alignItems: "center", justifyContent: "center",
      zIndex: 100, backdropFilter: "blur(6px)",
      animation: "fadeIn 0.15s ease",
    }} onClick={onClose}>
      <div style={{
        background: "#08080f", border: "1px solid #1c1c2e",
        width: 460, maxWidth: "92vw", maxHeight: "88vh",
        overflowY: "auto", animation: "slideUp 0.2s cubic-bezier(.4,0,.2,1)",
      }} onClick={e => e.stopPropagation()}>

        {/* Header */}
        <div style={{ padding: "20px 24px", borderBottom: "1px solid #111", display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
          <div>
            <div style={{ fontSize: 9, color: "#333", letterSpacing: 2, fontFamily: "'JetBrains Mono', monospace", marginBottom: 4 }}>
              {carrier.carrier_id} · DOT {carrier.dot_number}
            </div>
            <div style={{ fontSize: 20, fontFamily: "'Bebas Neue', sans-serif", color: "#fff", letterSpacing: 1, lineHeight: 1.1 }}>
              {carrier.legal_name}
            </div>
          </div>
          <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: 4 }}>
            <ScoreRing score={carrier.score} size={60} prevScore={prevScore} />
            <span style={{ fontSize: 8, letterSpacing: 2, color: scoreColor(carrier.score), fontFamily: "'JetBrains Mono', monospace" }}>
              {scoreTier(carrier.score)}
            </span>
          </div>
        </div>

        {/* Delta banner */}
        {delta !== null && Math.abs(delta) > 0.1 && (
          <div style={{
            padding: "8px 24px",
            background: delta > 0 ? "#00ff9d08" : "#ff3b5c08",
            borderBottom: `1px solid ${delta > 0 ? "#00ff9d22" : "#ff3b5c22"}`,
            display: "flex", alignItems: "center", gap: 8,
          }}>
            <span style={{ fontSize: 9, color: "#444", fontFamily: "'JetBrains Mono', monospace", letterSpacing: 1 }}>
              SCORE CHANGED
            </span>
            <span style={{ fontSize: 12, fontFamily: "'JetBrains Mono', monospace", color: delta > 0 ? "#00ff9d" : "#ff3b5c" }}>
              {prevScore?.toFixed(1)} → {carrier.score?.toFixed(1)}
              <span style={{ marginLeft: 6, fontSize: 10 }}>({delta > 0 ? "+" : ""}{delta.toFixed(1)})</span>
            </span>
          </div>
        )}

        <div style={{ padding: "20px 24px" }}>
          {/* Score breakdown */}
          <div style={{ marginBottom: 20 }}>
            <div style={{ fontSize: 9, color: "#333", letterSpacing: 2, marginBottom: 10, fontFamily: "'JetBrains Mono', monospace" }}>
              SCORE BREAKDOWN
            </div>
            {bars.map(({ label, value, max }) => (
              <div key={label} style={{ marginBottom: 7 }}>
                <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 3 }}>
                  <span style={{ fontSize: 9, color: "#555", fontFamily: "'JetBrains Mono', monospace", letterSpacing: 1 }}>
                    {label.toUpperCase()}
                  </span>
                  <span style={{ fontSize: 9, color: "#888", fontFamily: "'JetBrains Mono', monospace" }}>
                    {value?.toFixed(2)} / {max}
                  </span>
                </div>
                <div style={{ height: 3, background: "#111", borderRadius: 1 }}>
                  <div style={{
                    height: "100%", borderRadius: 1,
                    width: `${(value / max) * 100}%`,
                    background: scoreColor((value / max) * 100),
                    transition: "width 0.7s ease",
                  }} />
                </div>
              </div>
            ))}
          </div>

          {/* Meta grid */}
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 6, marginBottom: 20 }}>
            {[
              ["AUTHORITY", carrier.authority_status],
              ["SAFETY",    carrier.safety_rating],
              ["FLEET",     `${carrier.fleet_size || "—"} units`],
              ["INSPECTED", carrier.last_inspection_date || "—"],
            ].map(([k, v]) => (
              <div key={k} style={{ background: "#0d0d1a", padding: "10px 12px" }}>
                <div style={{ fontSize: 8, color: "#333", letterSpacing: 2, fontFamily: "'JetBrains Mono', monospace", marginBottom: 3 }}>{k}</div>
                <div style={{ fontSize: 11, color: "#bbb", fontFamily: "'JetBrains Mono', monospace" }}>{v}</div>
              </div>
            ))}
          </div>

          {/* History */}
          {history.length > 0 && (
            <div>
              <div style={{ fontSize: 9, color: "#333", letterSpacing: 2, marginBottom: 10, fontFamily: "'JetBrains Mono', monospace" }}>
                SCORE HISTORY
              </div>
              {history.slice(0, 6).map((h, i) => (
                <div key={i} style={{
                  display: "flex", justifyContent: "space-between", alignItems: "center",
                  padding: "7px 0", borderBottom: "1px solid #0d0d1a",
                }}>
                  <span style={{ fontSize: 9, color: "#444", fontFamily: "'JetBrains Mono', monospace" }}>
                    #{history.length - i} · {new Date(h.computed_at).toLocaleString()}
                  </span>
                  <span style={{ fontSize: 12, fontFamily: "'JetBrains Mono', monospace", color: scoreColor(h.score) }}>
                    {h.score?.toFixed(1)}
                  </span>
                </div>
              ))}
            </div>
          )}
        </div>

        <div style={{ padding: "0 24px 20px" }}>
          <button onClick={onClose} style={{
            width: "100%", padding: 10, background: "transparent",
            border: "1px solid #1c1c2e", color: "#333", cursor: "pointer",
            fontFamily: "'JetBrains Mono', monospace", fontSize: 9, letterSpacing: 2,
            transition: "all 0.15s",
          }}
            onMouseEnter={e => { e.target.style.borderColor = "#444"; e.target.style.color = "#888"; }}
            onMouseLeave={e => { e.target.style.borderColor = "#1c1c2e"; e.target.style.color = "#333"; }}
          >CLOSE</button>
        </div>
      </div>
    </div>
  );
}

// ─── Toast Stack ──────────────────────────────────────────────────────────────
function ToastStack({ toasts }) {
  const colors = { success: "#00ff9d", error: "#ff3b5c", info: "#f5c518" };
  const bgs    = { success: "#001a0d", error: "#1a0008", info: "#1a1500" };
  return (
    <div style={{ position: "fixed", bottom: 24, right: 24, zIndex: 200, display: "flex", flexDirection: "column", gap: 8 }}>
      {toasts.map(t => (
        <div key={t.id} style={{
          background: bgs[t.type], border: `1px solid ${colors[t.type]}33`,
          color: colors[t.type], padding: "10px 16px",
          fontFamily: "'JetBrains Mono', monospace", fontSize: 10, letterSpacing: 1,
          animation: "slideUp 0.2s ease", maxWidth: 360, lineHeight: 1.5,
        }}>
          {t.msg}
        </div>
      ))}
    </div>
  );
}

// ─── Main Dashboard ───────────────────────────────────────────────────────────
export default function Dashboard() {
  const { carriers, meta, loading, load, prevScores } = useCarriers();
  const { toasts, success, error } = useToast();
  const [selected, setSelected] = useState(null);
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState("");

  const [baseState,     setBaseState]     = useState({ uploading: false, result: null, fileName: null });
  const [modifiedState, setModifiedState] = useState({ uploading: false, result: null, fileName: null });

  const handleUpload = async (file, isModified) => {
    const setter = isModified ? setModifiedState : setBaseState;
    setter(s => ({ ...s, uploading: true, fileName: file.name }));
    try {
      const result = await UploadService.upload(file);
      setter(s => ({ ...s, uploading: false, result }));
      await load({ status: statusFilter });
      const parts = [];
      if (result.new_count)       parts.push(`${result.new_count} new`);
      if (result.updated_count)   parts.push(`${result.updated_count} updated`);
      if (result.unchanged_count) parts.push(`${result.unchanged_count} unchanged`);
      success(`${isModified ? "MODIFIED" : "BASE"} FILE · ${parts.join(" · ")}`);
    } catch (e) {
      setter(s => ({ ...s, uploading: false }));
      error(`Upload failed: ${e.message}`);
    }
  };

  const filtered = carriers.filter(c =>
    (c.legal_name?.toLowerCase().includes(search.toLowerCase()) ||
     c.carrier_id?.toLowerCase().includes(search.toLowerCase())) &&
    (!statusFilter || c.authority_status === statusFilter)
  );

  const avgScore = carriers.length
    ? (carriers.reduce((a, c) => a + c.score, 0) / carriers.length).toFixed(1)
    : "—";

  const changedCarriers = carriers.filter(c =>
    prevScores[c.carrier_id] !== undefined &&
    Math.abs(c.score - prevScores[c.carrier_id]) > 0.1
  );

  return (
    <>
      <style>{`
        @import url('https://fonts.googleapis.com/css2?family=Bebas+Neue&family=JetBrains+Mono:wght@300;400;700&display=swap');
        *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
        html, body { background: #06060e; height: 100%; }
        ::-webkit-scrollbar { width: 3px; }
        ::-webkit-scrollbar-thumb { background: #1c1c2e; }
        @keyframes fadeIn  { from { opacity: 0 } to { opacity: 1 } }
        @keyframes slideUp { from { opacity: 0; transform: translateY(10px) } to { opacity: 1; transform: translateY(0) } }
        @keyframes popIn   { from { opacity: 0; transform: scale(0.6) } to { opacity: 1; transform: scale(1) } }
        @keyframes pulse   { 0%,100% { opacity: 1 } 50% { opacity: 0.3 } }
        .carrier-row { transition: background 0.12s; cursor: pointer; }
        .carrier-row:hover { background: #0d0d1e !important; }
      `}</style>

      <div style={{
        minHeight: "100vh", background: "#06060e",
        fontFamily: "'JetBrains Mono', monospace", color: "#ccc",
        padding: "28px 36px",
      }}>

        {/* ── Header ── */}
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-end", marginBottom: 32 }}>
          <div>
            <div style={{ fontSize: 9, letterSpacing: 4, color: "#2a2a3e", marginBottom: 5 }}>
              CARRIER ASSURE · COMPLIANCE INTELLIGENCE PLATFORM
            </div>
            <h1 style={{ fontFamily: "'Bebas Neue', sans-serif", fontSize: 38, letterSpacing: 3, color: "#fff", lineHeight: 1 }}>
              FLEET SCORING<br />
              <span style={{ color: "#00ff9d" }}>DASHBOARD</span>
            </h1>
          </div>
          <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
            <div style={{ width: 5, height: 5, borderRadius: "50%", background: "#00ff9d", animation: "pulse 2s infinite" }} />
            <span style={{ fontSize: 9, color: "#00ff9d", letterSpacing: 2 }}>LIVE</span>
          </div>
        </div>

        {/* ── Upload Zones ── */}
        <div style={{ display: "flex", gap: 8, marginBottom: 24 }}>
          <UploadZone
            label="BASE CCF FILE"
            description="INITIAL CARRIER DATA · ESTABLISHES BASELINE"
            accent="#00ff9d"
            onUpload={f => handleUpload(f, false)}
            result={baseState.result}
            uploading={baseState.uploading}
            fileName={baseState.fileName}
          />
          <UploadZone
            label="MODIFIED CCF FILE"
            description="UPDATED CARRIER DATA · DETECTS CHANGES VIA HASH"
            accent="#f5c518"
            onUpload={f => handleUpload(f, true)}
            result={modifiedState.result}
            uploading={modifiedState.uploading}
            fileName={modifiedState.fileName}
          />
        </div>

        {/* ── Changed carriers alert ── */}
        {changedCarriers.length > 0 && (
          <div style={{
            background: "#0d0a00", border: "1px solid #f5c51822",
            padding: "10px 16px", marginBottom: 12,
            display: "flex", alignItems: "center", gap: 12,
            animation: "slideUp 0.3s ease",
          }}>
            <div style={{ width: 4, height: 4, borderRadius: "50%", background: "#f5c518" }} />
            <span style={{ fontSize: 9, color: "#f5c518", letterSpacing: 2 }}>
              {changedCarriers.length} CARRIER{changedCarriers.length > 1 ? "S" : ""} RESCORED
            </span>
            <span style={{ fontSize: 9, color: "#555", letterSpacing: 1 }}>
              {changedCarriers.map(c => c.legal_name).join(" · ")}
            </span>
          </div>
        )}

        {/* ── Stats ── */}
        <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 1, marginBottom: 1 }}>
          {[
            { label: "TOTAL CARRIERS", value: meta.total,       accent: "#ffffff" },
            { label: "AVG SCORE",      value: avgScore,          accent: "#00ff9d" },
            { label: "AT RISK",        value: meta.at_risk_count, accent: "#ff3b5c" },
            { label: "SAFE (>70)",     value: carriers.filter(c => c.score > 70).length, accent: "#00ff9d" },
          ].map(({ label, value, accent }) => (
            <div key={label} style={{
              background: "#09091a", padding: "18px 20px",
              borderTop: `2px solid ${accent}18`,
            }}>
              <div style={{ fontSize: 8, color: "#333", letterSpacing: 2, marginBottom: 6 }}>{label}</div>
              <div style={{ fontSize: 28, fontFamily: "'Bebas Neue', sans-serif", color: loading ? "#1a1a2e" : accent, letterSpacing: 2, transition: "color 0.3s" }}>
                {loading ? "···" : value}
              </div>
            </div>
          ))}
        </div>

        {/* ── Toolbar ── */}
        <div style={{
          display: "flex", gap: 8, alignItems: "center",
          padding: "12px 0", margin: "1px 0",
          borderBottom: "1px solid #0d0d1a",
        }}>
          <div style={{ position: "relative", flex: 1, maxWidth: 280 }}>
            <svg style={{ position: "absolute", left: 10, top: "50%", transform: "translateY(-50%)" }}
              width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="#2a2a3e" strokeWidth="2">
              <circle cx="11" cy="11" r="8"/><path d="M21 21l-4.35-4.35"/>
            </svg>
            <input value={search} onChange={e => setSearch(e.target.value)}
              placeholder="SEARCH..."
              style={{
                width: "100%", background: "#09091a", border: "1px solid #111",
                color: "#777", padding: "7px 10px 7px 28px",
                fontSize: 9, fontFamily: "'JetBrains Mono', monospace",
                letterSpacing: 1, outline: "none",
              }}
            />
          </div>

          {["", "Active", "Inactive", "Revoked"].map(s => (
            <button key={s || "ALL"}
              onClick={() => setStatusFilter(s)}
              style={{
                background: "transparent",
                border: `1px solid ${statusFilter === s ? "#00ff9d" : "#111"}`,
                color: statusFilter === s ? "#00ff9d" : "#333",
                padding: "6px 12px", fontSize: 8, letterSpacing: 2,
                cursor: "pointer", fontFamily: "'JetBrains Mono', monospace",
                transition: "all 0.15s",
              }}
            >{(s || "ALL").toUpperCase()}</button>
          ))}

          <span style={{ marginLeft: "auto", fontSize: 8, color: "#222", letterSpacing: 2 }}>
            {filtered.length} / {meta.total} CARRIERS
          </span>
        </div>

        {/* ── Table header ── */}
        <div style={{
          display: "grid", gridTemplateColumns: "2.5fr 1fr 1fr 1fr 64px",
          padding: "8px 14px", borderBottom: "1px solid #0d0d1a",
        }}>
          {["CARRIER", "DOT", "STATUS", "SAFETY", "SCORE"].map(h => (
            <div key={h} style={{ fontSize: 8, color: "#2a2a3e", letterSpacing: 2 }}>{h}</div>
          ))}
        </div>

        {/* ── Rows ── */}
        <div>
          {loading ? (
            <div style={{ padding: "48px", textAlign: "center", fontSize: 9, color: "#1c1c2e", letterSpacing: 3, animation: "pulse 1.5s infinite" }}>
              LOADING...
            </div>
          ) : filtered.length === 0 ? (
            <div style={{ padding: "48px", textAlign: "center", fontSize: 9, color: "#1c1c2e", letterSpacing: 2 }}>
              NO CARRIERS · UPLOAD A CCF FILE ABOVE TO BEGIN
            </div>
          ) : (
            filtered.map((c, i) => {
              const prev = prevScores[c.carrier_id];
              const changed = prev !== undefined && Math.abs(c.score - prev) > 0.1;
              return (
                <div key={c.id} className="carrier-row"
                  onClick={() => setSelected({ carrier: c, prevScore: prev })}
                  style={{
                    display: "grid", gridTemplateColumns: "2.5fr 1fr 1fr 1fr 64px",
                    padding: "12px 14px",
                    background: changed ? "#0d0a0022" : i % 2 === 0 ? "#06060e" : "#08081a",
                    borderBottom: "1px solid #0a0a15",
                    borderLeft: changed ? "2px solid #f5c51844" : "2px solid transparent",
                    animation: `slideUp 0.25s ease ${Math.min(i * 0.025, 0.3)}s both`,
                  }}
                >
                  <div>
                    <div style={{ fontSize: 11, color: changed ? "#f5c518" : "#ccc", marginBottom: 2, transition: "color 0.3s" }}>
                      {c.legal_name}
                    </div>
                    <div style={{ fontSize: 8, color: "#2a2a3e", letterSpacing: 1 }}>{c.carrier_id}</div>
                  </div>

                  <div style={{ fontSize: 10, color: "#444", alignSelf: "center" }}>{c.dot_number}</div>

                  <div style={{ alignSelf: "center" }}>
                    <span style={{
                      fontSize: 8, letterSpacing: 1, padding: "2px 7px",
                      background: c.authority_status === "Active" ? "#00ff9d0d" : c.authority_status === "Inactive" ? "#f5c5180d" : "#ff3b5c0d",
                      color:      c.authority_status === "Active" ? "#00ff9d"   : c.authority_status === "Inactive" ? "#f5c518"   : "#ff3b5c",
                      border: `1px solid ${c.authority_status === "Active" ? "#00ff9d22" : c.authority_status === "Inactive" ? "#f5c51822" : "#ff3b5c22"}`,
                    }}>
                      {c.authority_status?.toUpperCase()}
                    </span>
                  </div>

                  <div style={{ fontSize: 9, color: "#444", alignSelf: "center" }}>{c.safety_rating}</div>

                  <div style={{ alignSelf: "center" }}>
                    <ScoreRing score={c.score} size={44} prevScore={changed ? prev : null} />
                  </div>
                </div>
              );
            })
          )}
        </div>

        {/* ── Footer ── */}
        <div style={{
          marginTop: 24, paddingTop: 12, borderTop: "1px solid #0d0d1a",
          display: "flex", justifyContent: "space-between",
          fontSize: 8, color: "#1c1c2e", letterSpacing: 2,
        }}>
          <span>CARRIER ASSURE · HASH-BASED CHANGE DETECTION ENGINE</span>
          <span>CLICK ANY ROW TO VIEW BREAKDOWN + HISTORY</span>
        </div>
      </div>

      {selected && (
        <DetailPanel
          carrier={selected.carrier}
          prevScore={selected.prevScore}
          onClose={() => setSelected(null)}
        />
      )}
      <ToastStack toasts={toasts} />
    </>
  );
}
