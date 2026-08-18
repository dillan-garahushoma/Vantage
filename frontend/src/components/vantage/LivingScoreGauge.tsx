type Props = {
  score: number;
  size?: number;
  label?: string;
};

export function LivingScoreGauge({ score, size = 180, label = "Living Score" }: Props) {
  const radius = size / 2 - 12;
  const circumference = Math.PI * radius; // half circle
  const clamped = Math.max(0, Math.min(100, score));
  const offset = circumference - (clamped / 100) * circumference;

  const band =
    clamped >= 80 ? "Excellent" : clamped >= 65 ? "Healthy" : clamped >= 50 ? "Watch" : "At risk";

  return (
    <div className="flex flex-col items-center">
      <svg width={size} height={size / 2 + 16} viewBox={`0 0 ${size} ${size / 2 + 16}`}>
        <defs>
          <linearGradient id="scoreGradient" x1="0" y1="0" x2="1" y2="0">
            <stop offset="0%" stopColor="var(--color-primary)" />
            <stop offset="100%" stopColor="var(--color-accent)" />
          </linearGradient>
        </defs>
        <path
          d={`M 12 ${size / 2} A ${radius} ${radius} 0 0 1 ${size - 12} ${size / 2}`}
          fill="none"
          stroke="var(--color-muted)"
          strokeWidth="14"
          strokeLinecap="round"
        />
        <path
          d={`M 12 ${size / 2} A ${radius} ${radius} 0 0 1 ${size - 12} ${size / 2}`}
          fill="none"
          stroke="url(#scoreGradient)"
          strokeWidth="14"
          strokeLinecap="round"
          strokeDasharray={circumference}
          strokeDashoffset={offset}
          style={{ transition: "stroke-dashoffset 900ms cubic-bezier(0.22,1,0.36,1)" }}
        />
        <text
          x={size / 2}
          y={size / 2 - 12}
          textAnchor="middle"
          className="font-display"
          style={{ fontSize: size * 0.24, fill: "var(--color-foreground)", fontWeight: 700 }}
        >
          {clamped}
        </text>

        <text
          x={size / 2}
          y={size / 2 + 10}
          textAnchor="middle"
          style={{ fontSize: size * 0.075, fill: "var(--color-muted-foreground)" }}
        >
          {band}
        </text>
      </svg>
      <p className="mt-1 text-xs font-medium uppercase tracking-widest text-muted-foreground">
        {label}
      </p>
    </div>
  );
}
