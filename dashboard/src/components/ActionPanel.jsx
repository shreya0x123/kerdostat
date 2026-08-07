/* ──────────────────────────────────────────────────────────────
   ActionPanel — Step 5
   Human-in-the-Loop: Yes / No / Modify + paper trade log
────────────────────────────────────────────────────────────── */
import { useState } from 'react'

export default function ActionPanel({ result, tradeLog, onTrade }) {
  const [showModify, setShowModify] = useState(false)
  const [qty, setQty]   = useState(10)
  const [sl,  setSl]    = useState('')
  const [tp,  setTp]    = useState('')
  const [busy, setBusy] = useState(false)

  const signal = result?.signal || 'HOLD'
  const price  = result?.indicators?.close

  async function handleAction(action, params = {}) {
    setBusy(true)
    await onTrade(action, params)
    setBusy(false)
    if (action !== 'NO') setShowModify(false)
  }

  return (
    <>
      {/* ── Step 5 label ── */}
      <div className="section-label" style={{ marginBottom: 12 }}>
        Human-in-the-Loop Decision
        <span className="step-tag">STEP 5</span>
      </div>

      {/* Intercept description */}
      <div style={{ fontSize: 12, color: 'var(--text-dim)', marginBottom: 12, lineHeight: 1.6 }}>
        The Autopilot pauses here. Choose your action before any execution occurs.
      </div>

      {/* Action buttons */}
      <div className="action-buttons">
        <button
          className="action-btn yes"
          disabled={busy}
          onClick={() => handleAction('YES', { qty, sl: sl || undefined, tp: tp || undefined })}
        >
          <span className="action-btn-icon">✅</span>
          <span className="action-btn-label">Yes</span>
          <span className="action-btn-desc">Approve & Execute</span>
        </button>

        <button
          className="action-btn no"
          disabled={busy}
          onClick={() => handleAction('NO')}
        >
          <span className="action-btn-icon">✖</span>
          <span className="action-btn-label">No</span>
          <span className="action-btn-desc">Dismiss Trade</span>
        </button>

        <button
          className="action-btn modify"
          onClick={() => setShowModify(v => !v)}
        >
          <span className="action-btn-icon">✎</span>
          <span className="action-btn-label">Modify</span>
          <span className="action-btn-desc">Tweak & Confirm</span>
        </button>
      </div>

      {/* Modify drawer */}
      {showModify && (
        <div className="modify-drawer">
          <div className="drawer-title">
            ✎ Intervention — Override Parameters
          </div>
          <div className="param-grid">
            <div className="param-field">
              <label className="param-label">Quantity</label>
              <input
                className="param-input"
                type="number"
                min={1}
                value={qty}
                onChange={e => setQty(Number(e.target.value))}
              />
            </div>
            <div className="param-field">
              <label className="param-label">Stop-Loss ($)</label>
              <input
                className="param-input"
                type="number"
                step="0.01"
                placeholder={price ? (price * 0.97).toFixed(2) : 'e.g. 175.00'}
                value={sl}
                onChange={e => setSl(e.target.value)}
              />
            </div>
            <div className="param-field">
              <label className="param-label">Take-Profit ($)</label>
              <input
                className="param-input"
                type="number"
                step="0.01"
                placeholder={price ? (price * 1.05).toFixed(2) : 'e.g. 210.00'}
                value={tp}
                onChange={e => setTp(e.target.value)}
              />
            </div>
          </div>
          <button
            className="confirm-btn"
            disabled={busy}
            onClick={() => handleAction('MODIFY', { qty, sl: sl || undefined, tp: tp || undefined })}
          >
            {busy ? 'Submitting…' : '⚡  Confirm Modified Trade'}
          </button>
        </div>
      )}

      {/* Trade log */}
      {tradeLog.length > 0 && (
        <>
          <div className="trade-log-title" style={{ marginTop: 16 }}>
            Paper Trade Log ({tradeLog.length})
          </div>
          <div className="trade-log">
            {tradeLog.map((entry, i) => {
              const actionType = entry.action || '?'
              const logCls =
                actionType === 'NO'                ? 'no'
                : (entry.signal === 'BUY')         ? 'buy'
                : (entry.signal === 'SELL')        ? 'sell'
                : 'hold'
              const id = entry.order_id
                ? entry.order_id.replace('PAPER-', '')
                : `DISMISSED-${i}`

              return (
                <div key={i} className="log-entry">
                  <span className={`log-action ${logCls}`}>
                    {actionType === 'NO' ? 'SKIP' : entry.side?.toUpperCase() || actionType}
                  </span>
                  <span className="log-msg">{entry.message}</span>
                  <span className="log-id">{id}</span>
                </div>
              )
            })}
          </div>
        </>
      )}
    </>
  )
}
