/* ──────────────────────────────────────────────────────────────
   ProposalCard — Steps 3 & 4
   Signal badge + confidence ring, XDI explanation, horizon badge,
   key factors table, hybrid decision, detailed reasoning
────────────────────────────────────────────────────────────── */

const SIGNAL_ICON = { BUY: '▲', SELL: '▼', HOLD: '●' }
const IMPACT_ICON = { bullish: '▲', bearish: '▼', neutral: '●' }
const IMPACT_CLASS = { bullish: 'impact-up', bearish: 'impact-down', neutral: 'impact-neut' }

const CIRCUMFERENCE = 2 * Math.PI * 30  // r=30

function ConfRing({ pct, cls }) {
  const offset = CIRCUMFERENCE * (1 - pct)
  return (
    <div className="conf-ring-wrap">
      <div className="conf-ring">
        <svg width="72" height="72" viewBox="0 0 72 72">
          <circle className="conf-track" cx="36" cy="36" r="30" />
          <circle
            className={`conf-fill ${cls}`}
            cx="36" cy="36" r="30"
            strokeDasharray={CIRCUMFERENCE}
            strokeDashoffset={offset}
          />
        </svg>
        <div className={`conf-pct ${cls}`}>{Math.round(pct * 100)}%</div>
      </div>
      <div className="conf-label">Confidence</div>
    </div>
  )
}

function ConfBar({ label, pct, cls }) {
  const color = cls === 'buy' ? 'green' : cls === 'sell' ? 'red' : 'yellow'
  return (
    <div className="indicator-row" style={{ marginBottom: 6 }}>
      <div className="ind-label">
        <span style={{ fontSize: 11 }}>{label}</span>
        <span style={{ fontFamily: 'var(--mono)', fontSize: 11 }}>{Math.round(pct * 100)}%</span>
      </div>
      <div className="ind-bar-track">
        <div className={`ind-bar-fill ${color}`} style={{ width: `${pct * 100}%` }} />
      </div>
    </div>
  )
}

export default function ProposalCard({ result }) {
  const signal    = result.signal || 'HOLD'
  const cls       = signal.toLowerCase()
  const conf      = result.confidence ?? 0
  const ruleConf  = result.rule_confidence ?? conf
  const mlConf    = result.ml_confidence
  const expl      = result.explanation || {}
  const hybrid    = result.hybrid_decision || {}

  // Horizon — can be a string (top-level) or dict (from XDI)
  const horizonDict = expl.prediction_horizon || {}
  const horizonDisplay = typeof horizonDict === 'object'
    ? (horizonDict.display || '—')
    : String(horizonDict || '—')
  const horizonTimeframe = typeof horizonDict === 'object'
    ? (horizonDict.timeframe || '')
    : ''

  const agreement = hybrid.agreement || 'NEUTRAL'

  return (
    <>
      {/* ── Header row: signal badge + confidence ring ── */}
      <div className="proposal-header">
        <div className="signal-badge">
          <div className={`signal-icon ${cls}`}>
            {SIGNAL_ICON[signal] || '?'}
          </div>
          <div className="signal-text">
            <div className={`signal-word ${cls}`}>{signal}</div>
            <div className="signal-sub">Module 1 — Signal Engine</div>
          </div>
        </div>
        <ConfRing pct={conf} cls={cls} />
      </div>

      {/* ── Confidence bars ── */}
      <ConfBar label="Rule Confidence" pct={ruleConf} cls={cls} />
      {mlConf != null && <ConfBar label="ML Confidence" pct={mlConf} cls={cls} />}

      <div className="divider" />

      {/* ── Module 2 tag ── */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', margin: '10px 0 8px' }}>
        <div className="section-label" style={{ margin: 0 }}>
          XDI Explanation <span className="step-tag">STEP 3</span>
        </div>
        <span className="module-tag">MODULE 2</span>
      </div>

      {/* ── Summary ── */}
      {expl.summary && (
        <div className="xdi-summary">{expl.summary}</div>
      )}

      {/* ── Step 4: Horizon badge ── */}
      <div style={{ margin: '2px 0 10px' }}>
        <div className="section-label" style={{ marginBottom: 6 }}>
          Prediction Horizon <span className="step-tag">STEP 4</span>
        </div>
        <span className="horizon-badge">
          <span className="horizon-icon">⏱</span>
          {horizonDisplay}
          {horizonTimeframe && (
            <span style={{ opacity: 0.6, fontSize: 11 }}>· {horizonTimeframe}</span>
          )}
        </span>
      </div>

      {/* ── Key Factors table ── */}
      {expl.key_factors?.length > 0 && (
        <>
          <div className="section-label" style={{ marginBottom: 6 }}>Key Factors</div>
          <table className="factors-table">
            <thead>
              <tr>
                <th>Indicator</th>
                <th>Value</th>
                <th></th>
                <th>Analysis</th>
              </tr>
            </thead>
            <tbody>
              {expl.key_factors.map((f, i) => (
                <tr key={i}>
                  <td>{f.indicator}</td>
                  <td style={{ textAlign: 'right' }}>{f.value}</td>
                  <td style={{ textAlign: 'center' }}>
                    <span className={IMPACT_CLASS[f.impact] || ''}>
                      {IMPACT_ICON[f.impact] || '?'}
                    </span>
                  </td>
                  <td>{f.interpretation}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </>
      )}

      {/* ── Actionable Insight ── */}
      {expl.actionable_insight && (
        <div className="xdi-summary" style={{ borderColor: 'rgba(0,255,135,0.15)', marginTop: 8 }}>
          <div style={{ fontSize: 10, fontWeight: 700, letterSpacing: '0.1em', color: 'var(--buy)', textTransform: 'uppercase', marginBottom: 6 }}>
            ⚡ Actionable Insight
          </div>
          {expl.actionable_insight}
        </div>
      )}

      {/* ── Hybrid Decision ── */}
      {hybrid && (
        <>
          <div className="section-label" style={{ marginTop: 10, marginBottom: 6 }}>Hybrid Decision (TA + ML)</div>
          <div className="hybrid-row">
            <span className="hybrid-key">Final Signal</span>
            <span className={`hybrid-val signal-word ${(hybrid.final_signal||'').toLowerCase()}`} style={{ fontSize: 13 }}>
              {SIGNAL_ICON[hybrid.final_signal]} {hybrid.final_signal}
            </span>
          </div>
          <div className="hybrid-row">
            <span className="hybrid-key">ML Agreement</span>
            <span className={`hybrid-val agreement-${agreement}`}>
              {agreement.replace(/_/g, ' ')}
            </span>
          </div>
          {hybrid.reasoning && (
            <div className="hybrid-row" style={{ flexDirection: 'column', alignItems: 'flex-start', gap: 4 }}>
              <span className="hybrid-key">Reasoning</span>
              <span style={{ fontSize: 11, color: 'var(--text-dim)', lineHeight: 1.5 }}>{hybrid.reasoning}</span>
            </div>
          )}
        </>
      )}

      {/* ── Risk ── */}
      {expl.risk_level && (
        <div style={{ marginTop: 10, display: 'flex', alignItems: 'center', gap: 8 }}>
          <span style={{ fontSize: 11, color: 'var(--text-dim)' }}>Risk:</span>
          <span style={{
            fontSize: 11, fontWeight: 700, letterSpacing: '0.08em',
            color: expl.risk_level === 'LOW' ? 'var(--buy)'
                 : expl.risk_level === 'HIGH' || expl.risk_level === 'EXTREME' ? 'var(--sell)'
                 : 'var(--hold)',
          }}>
            {expl.risk_level}
          </span>
          {expl.risk_reasoning && (
            <span style={{ fontSize: 11, color: 'var(--text-dim)', flex: 1 }}>
              — {expl.risk_reasoning.split('.')[0]}.
            </span>
          )}
        </div>
      )}
    </>
  )
}
