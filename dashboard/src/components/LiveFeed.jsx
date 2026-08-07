/* ──────────────────────────────────────────────────────────────
   LiveFeed — Step 2
   Shows price, RSI, MACD, Bollinger Bands, EMA, rules triggered
────────────────────────────────────────────────────────────── */

function IndBar({ label, value, display, pct, color }) {
  return (
    <div className="indicator-row">
      <div className="ind-label">
        <span>{label}</span>
        <span>{display}</span>
      </div>
      <div className="ind-bar-track">
        <div
          className={`ind-bar-fill ${color}`}
          style={{ width: `${Math.min(100, Math.max(0, pct))}%` }}
        />
      </div>
      {value && (
        <div className={`ind-reading ${color}`}>{value}</div>
      )}
    </div>
  )
}

function rsiColor(rsi) {
  if (rsi < 30) return 'green'
  if (rsi > 70) return 'red'
  return 'yellow'
}

function rsiReading(rsi) {
  if (rsi < 30) return '⬇ Oversold — potential BUY trigger'
  if (rsi > 70) return '⬆ Overbought — potential SELL trigger'
  return '● Neutral zone'
}

export default function LiveFeed({ result, loading, error }) {
  if (error) {
    return (
      <>
        <div className="section-label">Live Indicators <span className="step-tag">STEP 2</span></div>
        <div style={{ color: 'var(--sell)', fontSize: 13, padding: '8px 0' }}>⚠ {error}</div>
      </>
    )
  }

  if (loading) {
    return (
      <>
        <div className="section-label">Live Indicators <span className="step-tag">STEP 2</span></div>
        <div className="skeleton" style={{ height: 28, width: '55%', marginBottom: 16 }} />
        {[1,2,3,4].map(i => (
          <div key={i} style={{ marginBottom: 12 }}>
            <div className="skeleton" style={{ height: 10, width: '40%', marginBottom: 6 }} />
            <div className="skeleton" style={{ height: 4 }} />
          </div>
        ))}
        <div className="skeleton" style={{ height: 10, width: '60%', marginBottom: 6, marginTop: 8 }} />
        {[1,2].map(i => (
          <div key={i} className="skeleton" style={{ height: 10, marginBottom: 5 }} />
        ))}
      </>
    )
  }

  if (!result) {
    return (
      <>
        <div className="section-label">Live Indicators <span className="step-tag">STEP 2</span></div>
        <div style={{ color: 'var(--text-dim)', fontSize: 12, padding: '8px 0', fontStyle: 'italic' }}>
          Run analysis to see live indicator values.
        </div>
      </>
    )
  }

  const ind  = result.indicators || {}
  const rsi  = ind.rsi ?? 50
  const ema  = ind.ema_20 ?? 0
  const macd = ind.macd_histogram ?? 0
  const close = ind.close ?? 0
  const bbu  = ind.bb_upper ?? 0
  const bbl  = ind.bb_lower ?? 0
  const bbm  = ind.bb_middle ?? 0
  const bbRange = bbu - bbl
  const bbPos = bbRange > 0 ? ((close - bbl) / bbRange) * 100 : 50

  const emaColor = close > ema ? 'green' : 'red'
  const macdColor = macd > 0 ? 'green' : 'red'
  const macdPct = Math.min(100, (Math.abs(macd) / (Math.abs(macd) + 0.01)) * 100)

  const rules = result.rules_triggered || []

  return (
    <div className="fade-in">
      <div className="section-label">
        Live Indicators
        <span className="step-tag">STEP 2</span>
      </div>

      {/* Price tile */}
      <div className="price-tile">
        <span className="price-symbol">{result.symbol}</span>
        <span className="price-value">${close.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</span>
        <span className="price-date">{result.data_as_of}</span>
      </div>

      <div className="divider" />

      {/* RSI */}
      <IndBar
        label="RSI (14)"
        display={`${rsi.toFixed(1)}`}
        pct={rsi}
        color={rsiColor(rsi)}
        value={rsiReading(rsi)}
      />

      {/* MACD */}
      <IndBar
        label="MACD Histogram"
        display={`${macd >= 0 ? '+' : ''}${macd.toFixed(4)}`}
        pct={50 + (macd > 0 ? Math.min(50, macdPct * 0.5) : -Math.min(50, macdPct * 0.5))}
        color={macdColor}
        value={macd > 0 ? '⬆ Bullish momentum' : '⬇ Bearish momentum'}
      />

      {/* Bollinger Bands */}
      <IndBar
        label={`BB Position (${bbl.toFixed(0)}–${bbu.toFixed(0)})`}
        display={`${bbPos.toFixed(0)}%`}
        pct={bbPos}
        color={bbPos < 20 ? 'green' : bbPos > 80 ? 'red' : 'blue'}
        value={
          bbPos < 20 ? '⬇ Near lower band — support zone'
          : bbPos > 80 ? '⬆ Near upper band — resistance zone'
          : '● Mid-band range'
        }
      />

      {/* EMA */}
      <IndBar
        label={`EMA (20)  →  ${ema.toFixed(2)}`}
        display={close > ema ? `+${((close/ema-1)*100).toFixed(2)}% above` : `-${((1-close/ema)*100).toFixed(2)}% below`}
        pct={close > ema ? Math.min(100, ((close/ema-1)*100)*10 + 50) : Math.max(0, 50 - ((1-close/ema)*100)*10)}
        color={emaColor}
        value={close > ema ? '⬆ Price above EMA — uptrend confirmed' : '⬇ Price below EMA — downtrend'}
      />

      <div className="divider" />

      {/* Rules triggered */}
      <div className="section-label" style={{ marginBottom: 6 }}>
        Rules Triggered ({rules.length})
      </div>
      {rules.length === 0 ? (
        <div className="no-rules">No primary rules fired — HOLD signal</div>
      ) : (
        <div className="rules-list">
          {rules.slice(0, 4).map((r, i) => (
            <div key={i} className="rule-item">
              <span className="rule-bullet">✔</span>
              <span>{r}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
