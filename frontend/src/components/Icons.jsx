function Base({ size = 18, children, ...rest }) {
    return (<svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.6} strokeLinecap="square" strokeLinejoin="miter" aria-hidden="true" focusable="false" {...rest}>
      {children}
    </svg>);
}
export const IconGrid = (p) => (<Base {...p}>
    <rect x="3" y="3" width="7" height="7"/>
    <rect x="14" y="3" width="7" height="7"/>
    <rect x="3" y="14" width="7" height="7"/>
    <rect x="14" y="14" width="7" height="7"/>
  </Base>);
export const IconReport = (p) => (<Base {...p}>
    <path d="M5 3h9l5 5v13H5z"/>
    <path d="M14 3v5h5"/>
    <path d="M8 13h8M8 17h5"/>
  </Base>);
export const IconWrench = (p) => (<Base {...p}>
    <path d="M15 3a5 5 0 0 0-4.6 7L4 16.4V20h3.6l6.4-6.4A5 5 0 1 0 15 3z"/>
    <path d="M15.5 8.5h.01"/>
  </Base>);
export const IconMegaphone = (p) => (<Base {...p}>
    <path d="M4 9v6h4l8 4V5L8 9z"/>
    <path d="M19 9a3 3 0 0 1 0 6"/>
  </Base>);
export const IconHome = (p) => (<Base {...p}>
    <path d="M4 11 12 4l8 7"/>
    <path d="M6 10v10h12V10"/>
    <path d="M10 20v-5h4v5"/>
  </Base>);
export const IconUsers = (p) => (<Base {...p}>
    <circle cx="9" cy="8" r="3"/>
    <path d="M3 20c0-3.3 2.7-6 6-6s6 2.7 6 6"/>
    <path d="M16 5.5a3 3 0 0 1 0 5.8M18 20c0-2-.6-3.7-1.6-5"/>
  </Base>);
export const IconChart = (p) => (<Base {...p}>
    <path d="M4 20V4"/>
    <path d="M4 20h16"/>
    <path d="M8 17v-5M12 17V7M16 17v-8"/>
  </Base>);
export const IconPlus = (p) => (<Base {...p}>
    <path d="M12 5v14M5 12h14"/>
  </Base>);
export const IconSearch = (p) => (<Base {...p}>
    <circle cx="11" cy="11" r="6"/>
    <path d="M20 20l-4.5-4.5"/>
  </Base>);
export const IconArrowLeft = (p) => (<Base {...p}>
    <path d="M19 12H6M11 6l-6 6 6 6"/>
  </Base>);
export const IconArrowRight = (p) => (<Base {...p}>
    <path d="M5 12h13M13 6l6 6-6 6"/>
  </Base>);
export const IconShield = (p) => (<Base {...p}>
    <path d="M12 3l7 3v6c0 4.5-3 7.8-7 9-4-1.2-7-4.5-7-9V6z"/>
    <path d="M9 12l2 2 4-4"/>
  </Base>);
export const IconClock = (p) => (<Base {...p}>
    <circle cx="12" cy="12" r="8"/>
    <path d="M12 8v4.5l3 2"/>
  </Base>);
export const IconAlert = (p) => (<Base {...p}>
    <path d="M12 4l9 16H3z"/>
    <path d="M12 10v4M12 17h.01"/>
  </Base>);
export const IconCheck = (p) => (<Base {...p}>
    <path d="M5 12.5 10 17l9-10"/>
  </Base>);
export const IconClose = (p) => (<Base {...p}>
    <path d="M6 6l12 12M18 6 6 18"/>
  </Base>);
export const IconMenu = (p) => (<Base {...p}>
    <path d="M4 7h16M4 12h16M4 17h16"/>
  </Base>);
export const IconLogout = (p) => (<Base {...p}>
    <path d="M15 4h4v16h-4"/>
    <path d="M10 8l-4 4 4 4M6 12h9"/>
  </Base>);
export const IconSparkle = (p) => (<Base {...p}>
    <path d="M12 3l1.8 5.2L19 10l-5.2 1.8L12 17l-1.8-5.2L5 10l5.2-1.8z"/>
  </Base>);
export const IconPin = (p) => (<Base {...p}>
    <path d="M12 21s6-6.1 6-10.5A6 6 0 0 0 6 10.5C6 14.9 12 21 12 21z"/>
    <circle cx="12" cy="10.5" r="2.2"/>
  </Base>);
export const IconStar = ({ filled = false, ...p }) => (<Base {...p} fill={filled ? 'currentColor' : 'none'}>
    <path d="M12 4l2.4 5 5.6.8-4 3.9 1 5.5-5-2.7-5 2.7 1-5.5-4-3.9 5.6-.8z"/>
  </Base>);
/** A stack of photographs — used where the count of published photos is shown. */
export const IconImages = (p) => (<Base {...p}>
    <path d="M8 4h12v12"/>
    <rect x="4" y="8" width="12" height="12"/>
    <path d="M4 17l3.5-3.5 2.5 2.5 3-3L16 16"/>
  </Base>);
export const IconChevronLeft = (p) => (<Base {...p}>
    <path d="M14.5 6 8.5 12l6 6"/>
  </Base>);
export const IconChevronRight = (p) => (<Base {...p}>
    <path d="M9.5 6l6 6-6 6"/>
  </Base>);
/** Four corner brackets: "open this, bigger". */
export const IconExpand = (p) => (<Base {...p}>
    <path d="M4 9V4h5"/>
    <path d="M20 15v5h-5"/>
    <path d="M20 9V4h-5"/>
    <path d="M4 15v5h5"/>
  </Base>);
