import { cn } from '../../lib/utils'

export interface MapTextureProps {
  className?: string
}

export function MapTexture({ className }: MapTextureProps) {
  return (
    <svg
      viewBox="0 0 600 420"
      preserveAspectRatio="xMidYMid slice"
      aria-hidden="true"
      className={cn('h-full w-full', className)}
    >
      <defs>
        <linearGradient id="mt-bg" x1="0" y1="0" x2="1" y2="1">
          <stop offset="0%" stopColor="#F9F7FF" />
          <stop offset="60%" stopColor="#F1ECFF" />
          <stop offset="100%" stopColor="#E7E0FF" />
        </linearGradient>
        <linearGradient id="mt-parcel" x1="0" y1="0" x2="1" y2="1">
          <stop offset="0%" stopColor="#FFFFFF" stopOpacity="0.92" />
          <stop offset="100%" stopColor="#EFEAFF" stopOpacity="0.78" />
        </linearGradient>
      </defs>

      <rect width="600" height="420" fill="url(#mt-bg)" />

      <g fill="none" stroke="#C9BDF7" strokeWidth="1" opacity="0.55">
        <path d="M-20 268 C 90 232, 168 300, 268 268 S 452 208, 620 246" />
        <path d="M-20 316 C 96 288, 176 348, 280 318 S 462 262, 620 296" />
        <path d="M-20 200 C 84 168, 160 226, 258 196 S 448 140, 620 176" />
        <path d="M120 -20 C 150 90, 96 190, 140 300 S 190 400, 168 440" />
        <path d="M470 -20 C 440 96, 500 190, 452 300 S 420 400, 440 440" />
      </g>

      <ellipse cx="472" cy="336" rx="96" ry="58" fill="#DFEDE4" opacity="0.85" />
      <ellipse cx="96" cy="96" rx="72" ry="46" fill="#E6EFF6" opacity="0.75" />

      <g fill="url(#mt-parcel)" stroke="#E9E3FF" strokeWidth="1.2">
        <rect x="196" y="58" width="112" height="74" rx="12" />
        <rect x="322" y="58" width="96" height="74" rx="12" />
        <rect x="196" y="150" width="76" height="62" rx="12" />
        <rect x="286" y="150" width="132" height="62" rx="12" />
        <rect x="196" y="230" width="98" height="70" rx="12" />
        <rect x="308" y="230" width="110" height="70" rx="12" />
        <rect x="40" y="286" width="80" height="58" rx="12" />
        <rect x="428" y="140" width="86" height="62" rx="12" />
      </g>

      <g stroke="#FFFFFF" strokeWidth="11" strokeLinecap="round" fill="none" opacity="0.92">
        <path d="M20 248 C 170 214, 336 268, 580 206" />
        <path d="M182 8 C 190 140, 178 280, 186 412" />
        <path d="M428 8 C 440 130, 424 268, 436 412" />
        <path d="M16 118 C 160 92, 330 142, 578 96" />
      </g>

      <g fill="#A78BFA">
        <circle cx="214" cy="100" r="2.4" opacity="0.7" />
        <circle cx="252" cy="180" r="2.2" opacity="0.55" />
        <circle cx="352" cy="90" r="2.6" opacity="0.65" />
        <circle cx="330" cy="266" r="2.1" opacity="0.5" />
        <circle cx="228" cy="268" r="2.4" opacity="0.6" />
        <circle cx="470" cy="170" r="2.2" opacity="0.5" />
      </g>
    </svg>
  )
}

export default MapTexture
