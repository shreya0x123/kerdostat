import { useState, useCallback } from 'react'
import SymbolBar   from './components/SymbolBar.jsx'
import LiveFeed    from './components/LiveFeed.jsx'
import ProposalCard from './components/ProposalCard.jsx'
import ActionPanel from './components/ActionPanel.jsx'

const API = 'http://localhost:5050'

export default function App() {
  const [symbol,   setSymbol]   = useState('AAPL')
  const [interval, setInterval] = useState('1day')
  const [loading,  setLoading]  = useState(false)
  const [result,   setResult]   = useState(null)
  const [error,    setError]    = useState(null)
  const [tradeLog, setTradeLog] = useState([])

  const runAnalysis = useCallback(async (sym, intv) => {
    setLoading(true)
    setError(null)
    setResult(null)
    try {
      const res  = await fetch(`${API}/analyze-yahoo`, {
        method:  'POST',
        headers: { 'Content-Type': 'application/json' },
        body:    JSON.stringify({ symbol: sym, interval: intv }),
      })
      const data = await res.json()
      if (!data.ok) throw new Error(data.error || 'Analysis failed')
      setResult(data.result)
    } catch (e) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }, [])

  const handleTrade = useCallback(async (action, params = {}) => {
    if (!result) return
    try {
      const res  = await fetch(`${API}/trade-action`, {
        method:  'POST',
        headers: { 'Content-Type': 'application/json' },
        body:    JSON.stringify({
          action,
          symbol:  result.symbol,
          signal:  result.signal,
          price:   result.indicators?.close,
          ...params,
        }),
      })
      const data = await res.json()
      setTradeLog(prev => [data, ...prev])
      return data
    } catch (e) {
      console.error('Trade error', e)
    }
  }, [result])

  return (
    <>
      <div className="app-bg" />
      <div className="app-shell">
        {/* ── Header ── */}
        <header className="header">
          <div className="header-logo">
            <div className="logo-mark">K</div>
            <div>
              <div className="logo-text">KERDOSTAT</div>
              <div className="logo-sub">Explainable AI Trading Signal System</div>
            </div>
          </div>
          <div className="header-status">
            <div className="status-dot" />
            <span>Signal Engine Active</span>
            <span style={{ color: 'var(--text-faint)' }}>·</span>
            <span>XDI Engine Active</span>
          </div>
          <div className="header-badge">EVALUATOR DEMO</div>
        </header>

        {/* ── Body ── */}
        <div className="main-body">
          {/* LEFT: Symbol selector + Live indicators */}
          <div className="left-col">
            <div className="glass symbol-bar">
              <SymbolBar
                symbol={symbol}
                interval={interval}
                loading={loading}
                onSymbolChange={setSymbol}
                onIntervalChange={setInterval}
                onAnalyze={() => runAnalysis(symbol, interval)}
              />
            </div>

            <div className="glass live-feed">
              <LiveFeed result={result} loading={loading} error={error} />
            </div>
          </div>

          {/* RIGHT: Proposal Card + Action Panel */}
          <div className="right-col">
            {result ? (
              <>
                <div className={`glass proposal-card ${result.signal?.toLowerCase()}`}>
                  <ProposalCard result={result} />
                </div>
                <div className="glass action-panel">
                  <ActionPanel
                    result={result}
                    tradeLog={tradeLog}
                    onTrade={handleTrade}
                  />
                </div>
              </>
            ) : (
              <div className="glass" style={{ flex: 1, display: 'flex' }}>
                <div className="empty-state">
                  <div className="empty-icon">📡</div>
                  <div className="empty-title">Awaiting Analysis</div>
                  <div className="empty-desc">
                    Select a symbol on the left and click&nbsp;
                    <strong style={{ color: 'var(--accent)' }}>Run Analysis</strong>
                    &nbsp;to generate a live BUY / SELL / HOLD recommendation
                    with XDI justification.
                    {error && (
                      <span style={{ display: 'block', color: 'var(--sell)', marginTop: 12 }}>
                        ⚠ {error}
                      </span>
                    )}
                  </div>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </>
  )
}
