// Panels and KPI tiles used on every page.
export function Card({ title, hint, children, right }) {
  return (
    <div className="card">
      {(title || right) && (
        <div className="card-head">
          {title && <h2>{title}</h2>}
          {right}
        </div>
      )}
      {hint && <div className="hint">{hint}</div>}
      {children}
    </div>
  );
}

export function KpiCard({ label, value, sub, tone = "accent" }) {
  return (
    <div className={`card kpi ${tone}`}>
      <div className="label">{label}</div>
      <div className="value">{value}</div>
      {sub && <div className="sub">{sub}</div>}
    </div>
  );
}

export function PageHead({ title, subtitle, right }) {
  return (
    <div className="page-head">
      <div>
        <h1>{title}</h1>
        {subtitle && <p>{subtitle}</p>}
      </div>
      {right}
    </div>
  );
}