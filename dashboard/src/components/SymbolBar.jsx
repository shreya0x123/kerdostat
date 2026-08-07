const PRESETS = ['AAPL', 'TSLA', 'NVDA', 'MSFT', 'SPY', 'AMZN']

const INTERVALS = [
  { value: '1min',  label: '1m' },
  { value: '5min',  label: '5m' },
  { value: '15min', label: '15m' },
  { value: '1hour', label: '1H' },
  { value: '1day',  label: '1D' },
]

export default function SymbolBar({ symbol, interval, loading, onSymbolChange, onIntervalChange, onAnalyze }) {
  return (
    <>
      {/* STEP 1 label */}
      <div className="section-label">
        Asset Selection
        <span className="step-tag">STEP 1</span>
      </div>

      {/* Preset chips */}
      <div className="symbol-chips">
        {PRESETS.map(s => (
          <button
            key={s}
            className={`chip ${symbol === s ? 'active' : ''}`}
            onClick={() => onSymbolChange(s)}
          >
            {s}
          </button>
        ))}
      </div>

      {/* Custom input + interval */}
      <div className="symbol-input-row">
        <input
          className="symbol-input"
          value={symbol}
          onChange={e => onSymbolChange(e.target.value.toUpperCase())}
          placeholder="TYPE SYMBOL…"
          maxLength={8}
          onKeyDown={e => e.key === 'Enter' && onAnalyze()}
        />
        <select
          className="interval-select"
          value={interval}
          onChange={e => onIntervalChange(e.target.value)}
        >
          {INTERVALS.map(i => (
            <option key={i.value} value={i.value}>{i.label}</option>
          ))}
        </select>
      </div>

      {/* Analyze button */}
      <button
        className={`analyze-btn ${loading ? 'loading' : ''}`}
        disabled={loading || !symbol}
        onClick={onAnalyze}
      >
        {loading ? (
          <><span className="spinner" /> Fetching live data…</>
        ) : (
          '⚡  Run Analysis'
        )}
      </button>

      {/* Source note */}
      <div style={{ marginTop: 8, fontSize: 10, color: 'var(--text-dim)', textAlign: 'center', letterSpacing: '0.03em' }}>
        Yahoo Finance · No API key required · Live market data
      </div>
    </>
  )
}
