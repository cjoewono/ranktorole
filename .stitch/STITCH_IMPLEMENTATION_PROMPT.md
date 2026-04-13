# RankToRole — Vanguard Tactical UI Implementation Prompt
## For Claude Code (claude-sonnet-4-20250514)

---

## CONTEXT

You are implementing a complete UI redesign of RankToRole using the **Vanguard Tactical** design system from `.stitch/vanguard_tactical/DESIGN.md`. The design system has been finalized through Stitch and the HTML mockups are in `.stitch/`. Your job is to translate those mockups into working React components that replace the current frontend.

**Before writing a single line of code:**
1. Read `.stitch/vanguard_tactical/DESIGN.md` (the design bible)
2. Read the current `frontend/` directory structure
3. Read `DATA_CONTRACT.md` (all API shapes remain unchanged)
4. Read `CLAUDE.md` (hard rules)

---

## STEP 0 — GATE CHECK (do not skip)

Run these and confirm they pass before touching any frontend file:

```bash
cd backend && pytest --tb=short -q
```

If tests fail, stop and report. Do not proceed.

---

## DESIGN SYSTEM — TAILWIND CONFIG

Replace `frontend/tailwind.config.js` with this exact config:

```js
/** @type {import('tailwindcss').Config} */
export default {
  darkMode: 'class',
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      colors: {
        'background':                '#111416',
        'surface':                   '#111416',
        'surface-dim':               '#111416',
        'surface-container-lowest':  '#0c0f10',
        'surface-container-low':     '#191c1e',
        'surface-container':         '#1d2022',
        'surface-container-high':    '#272a2c',
        'surface-container-highest': '#323537',
        'surface-variant':           '#323537',
        'surface-bright':            '#373a3c',
        'on-surface':                '#e1e2e5',
        'on-surface-variant':        '#c4c7c8',
        'on-background':             '#e1e2e5',
        'outline':                   '#8d9193',
        'outline-variant':           '#434749',
        'primary':                   '#ffb692',
        'primary-container':         '#5a2200',
        'primary-fixed':             '#ffdbcb',
        'primary-fixed-dim':         '#ffb692',
        'on-primary':                '#562000',
        'on-primary-container':      '#ff700f',
        'on-primary-fixed':          '#341100',
        'on-primary-fixed-variant':  '#7a3000',
        'inverse-primary':           '#9f4200',
        'secondary':                 '#8adb4d',
        'secondary-container':       '#56a315',
        'secondary-fixed':           '#a5f866',
        'secondary-fixed-dim':       '#8adb4d',
        'on-secondary':              '#183800',
        'on-secondary-container':    '#143000',
        'on-secondary-fixed':        '#0b2000',
        'on-secondary-fixed-variant':'#255100',
        'tertiary':                  '#9dcafd',
        'tertiary-container':        '#00355a',
        'tertiary-fixed':            '#d0e4ff',
        'tertiary-fixed-dim':        '#9dcafd',
        'on-tertiary':               '#003256',
        'on-tertiary-container':     '#729fcf',
        'on-tertiary-fixed':         '#001d34',
        'on-tertiary-fixed-variant': '#134975',
        'error':                     '#ffb4ab',
        'error-container':           '#93000a',
        'on-error':                  '#690005',
        'on-error-container':        '#ffdad6',
        'inverse-surface':           '#e1e2e5',
        'inverse-on-surface':        '#2e3133',
        'surface-tint':              '#ffb692',
      },
      fontFamily: {
        headline: ['Space Grotesk', 'sans-serif'],
        body:     ['Inter', 'sans-serif'],
        label:    ['Work Sans', 'sans-serif'],
      },
      borderRadius: {
        DEFAULT: '0.125rem',
        sm:      '0.125rem',
        md:      '0.375rem',
        lg:      '0.25rem',
        xl:      '0.5rem',
        full:    '0.75rem',
      },
    },
  },
  plugins: [],
}
```

---

## STEP 1 — GLOBAL CSS & FONTS

Replace `frontend/src/index.css`:

```css
@tailwind base;
@tailwind components;
@tailwind utilities;

@import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@300;400;500;600;700&family=Inter:wght@300;400;500;600;700&family=Work+Sans:wght@300;400;500;600;700&display=swap');
@import url('https://fonts.googleapis.com/css2?family=Material+Symbols+Outlined:wght,FILL@100..700,0..1&display=swap');

@layer base {
  html { @apply dark; }
  body { @apply bg-background font-body text-on-background; min-height: 100dvh; }
}

@layer utilities {
  .tactical-grid {
    background-image: radial-gradient(circle, #434749 1px, transparent 1px);
    background-size: 32px 32px;
    opacity: 0.08;
    pointer-events: none;
  }
  .mission-gradient {
    background: linear-gradient(135deg, #ffb692 0%, #5a2200 100%);
  }
  .material-symbols-outlined {
    font-variation-settings: 'FILL' 0, 'wght' 400, 'GRAD' 0, 'opsz' 24;
  }
  /* Focus bottom-border only, no box outline */
  .tactical-input {
    @apply bg-surface-container-highest text-on-surface font-body text-sm
           border-0 border-b-2 border-outline-variant outline-none
           px-3 pt-5 pb-2 w-full transition-colors;
  }
  .tactical-input:focus {
    @apply border-secondary;
  }
}
```

---

## STEP 2 — COMPONENT: NavBar.jsx

Replace `frontend/src/components/NavBar.jsx` entirely.

**Design spec:**
- Dark bar: `bg-surface-container-low` (no borders)
- Left: terminal icon `▣` + wordmark "MISSION CONTROL" in `font-headline font-bold text-primary`
- Right: nav links in `font-label tracking-widest text-xs uppercase text-on-surface-variant` with active state in `text-secondary`
- Mobile: bottom tab bar with icon + label (DASHBOARD, EDITOR, AI CHAT, SETTINGS)

**Implementation:**
```jsx
import { NavLink, useLocation } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'

const NAV_ITEMS = [
  { to: '/dashboard',  label: 'Dashboard',  icon: '⊞' },
  { to: '/translator', label: 'Editor',     icon: '⊟' },
  { to: '/contacts',   label: 'Intel',      icon: '◈' },
]

export default function NavBar() {
  const { logout } = useAuth()

  return (
    <>
      {/* Desktop top bar */}
      <nav className="hidden md:flex items-center justify-between bg-surface-container-low px-6 py-3">
        <div className="flex items-center gap-3">
          <span className="text-primary font-headline font-bold text-lg">▣</span>
          <span className="font-headline font-bold text-primary tracking-wide text-sm">
            MISSION CONTROL
          </span>
        </div>
        <div className="flex items-center gap-8">
          {NAV_ITEMS.map(({ to, label }) => (
            <NavLink
              key={to}
              to={to}
              className={({ isActive }) =>
                `font-label text-xs tracking-widest uppercase transition-colors ${
                  isActive ? 'text-secondary' : 'text-on-surface-variant hover:text-on-surface'
                }`
              }
            >
              {label}
            </NavLink>
          ))}
          <button
            onClick={logout}
            className="font-label text-xs tracking-widest uppercase text-on-surface-variant hover:text-error transition-colors"
          >
            Logout
          </button>
        </div>
      </nav>

      {/* Mobile bottom tab bar */}
      <nav className="md:hidden fixed bottom-0 left-0 right-0 z-50 bg-surface-container-low border-t border-outline-variant/15 flex">
        {NAV_ITEMS.map(({ to, label, icon }) => (
          <NavLink
            key={to}
            to={to}
            className={({ isActive }) =>
              `flex-1 flex flex-col items-center py-3 gap-1 font-label text-[10px] tracking-widest uppercase transition-colors ${
                isActive ? 'text-primary' : 'text-on-surface-variant'
              }`
            }
          >
            <span className="text-base">{icon}</span>
            {label}
          </NavLink>
        ))}
      </nav>
    </>
  )
}
```

---

## STEP 3 — PAGE: Login.jsx

Replace `frontend/src/pages/Login.jsx`.

**Design spec (from `.stitch/login_refined_tactical/`):**
- Full-screen dark background `bg-background` with dot-grid overlay (`tactical-grid` absolute positioned)
- Top mini-bar: `▣ MISSION CONTROL` left, `AUTH_SERVICE: ACTIVE` right in `text-secondary text-xs font-label tracking-widest`
- Card: `bg-surface-container-low` no border, no shadow (tonal layering only)
- Status chip: green dot + "SECURE TERMINAL CONNECTED" in `text-secondary`
- Headline: "COMMANDER ACCESS" in `font-headline font-bold text-5xl text-on-surface uppercase`
- Subtext: "Initialize biometric bypass or enter tactical credentials below."
- Inputs: `tactical-input` class. Labels: `font-label text-xs tracking-widest uppercase text-on-surface-variant`
  - Email: placeholder `C-ALPHA@VANGUARD.SYS`
  - Password: placeholder `••••••••••••` with eye toggle
- Primary CTA: full-width `mission-gradient` button, `text-on-primary font-label font-semibold tracking-widest uppercase text-sm`, rounded-md, "SIGN IN ›"
- Divider: `EXTERNAL PROTOCOLS` centered in `font-label text-xs tracking-widest text-outline`
- Google SSO: `bg-surface-container-highest` button, no border, "ACCESS VIA GOOGLE SSO"
- Footer links: "FORGOT PROTOCOL?" and "ENLIST NEW AGENT" (links to /register) in `text-tertiary font-label text-xs tracking-widest uppercase`
- Bottom bar: "AES-256 VALIDATED" and "TIER 1 ENCRYPTION" in `text-outline text-xs font-label tracking-widest`

**All existing auth logic (useAuth, loginRequest, navigate) stays exactly the same. Only the JSX/className changes.**

---

## STEP 4 — PAGE: Register.jsx

Replace `frontend/src/pages/Register.jsx`.

**Design spec:** Same shell as Login.
- Headline: "ENLIST NEW AGENT"
- Subtext: "Initialize your operator profile to begin deployment."
- Fields: Email, Username (label: "CALLSIGN"), Password (label: "SECURITY KEY")
- CTA: "CREATE PROFILE ›" with `mission-gradient`
- Footer link: "ALREADY ENLISTED? SIGN IN" → /login in `text-tertiary`

**All existing logic stays the same.**

---

## STEP 5 — PAGE: Dashboard.jsx

Replace `frontend/src/pages/Dashboard.jsx`.

**Design spec (from `.stitch/dashboard_refined_tactical/`):**
- Page bg: `bg-background`
- Top section (inside `bg-surface-container-low px-4 pt-4 pb-6`):
  - Status line: green dot + "SYSTEM ACTIVE / CORE_OPERATIONS" in `text-secondary font-label text-xs tracking-widest uppercase`
  - Headline: "YOUR DEPLOYMENTS" in `font-headline font-bold text-5xl uppercase text-on-surface` (large, bold, two lines)
  - Subtext in `text-on-surface-variant text-sm font-body`
  - New Resume button: `mission-gradient` pill-ish button, "+ NEW RESUME" in `font-label text-xs tracking-widest font-semibold uppercase text-on-primary`, rounded-md
- Resume cards list: `bg-surface-container` cards, no borders
  - Each card: file icon (gray rectangle), title in `font-headline font-semibold text-on-surface uppercase`, status chip (`text-secondary bg-secondary/10` for FINALIZED, `text-primary bg-primary/10` for IN PROGRESS), modified date, "EDIT & EXPORT" ghost button + trash icon
  - Clicking "EDIT & EXPORT" → navigate to /translator (existing behavior)
  - Delete behavior unchanged
- Stats section: Three stat cards (`bg-surface-container-low`), each with:
  - Label: `font-label text-xs tracking-widest uppercase text-on-surface-variant`
  - Value: `font-headline font-bold text-4xl text-on-surface`
  - Sub-label or colored progress bar
- Bottom mobile nav spacer: `pb-20 md:pb-0`

---

## STEP 6 — PAGE: Translator.jsx (The Editor)

Replace `frontend/src/pages/Translator.jsx`.

**Design spec (from `.stitch/editor_refined_tactical/`):**
- Page bg: `bg-background`, mobile-bottom-nav spacer
- Top progress indicator: 3 segmented green blocks + "EDIT & FINALIZE" in `font-headline font-bold text-2xl uppercase`
- **Input section** (`bg-surface-container-low px-4 py-6`):
  - "MISSION HEADLINE" label + `tactical-input` for civilian_title (or military_text as pre-fill)
  - "EXECUTIVE SUMMARY" label + `tactical-input` textarea for job_description
- **Mission Roles / Bullets section** (`mt-4`):
  - "MISSION ROLES" heading `font-headline font-bold text-2xl uppercase` + "+ ADD POSITION" ghost link in `text-tertiary`
  - Each bullet: accordion-style card `bg-surface-container`, green dot icon, bullet text
- **Tactical AI Assistant panel** (`bg-surface-container-low` bottom section):
  - Header: "TACTICAL AI ASSISTANT" + green "● ACTIVE LINK" in `text-secondary text-xs`
  - Chat bubble area: AI message in plain `font-body text-sm text-on-surface`
  - "SUGGESTED REVISION" block: `bg-surface-container-highest` card with `text-primary` header
  - Pill tags: ACTION VERBS, QUANTIFY IMPACT, SOFT SKILLS in `bg-surface-container-highest font-label text-xs tracking-wider`
  - Input: `tactical-input` placeholder "Consult Vanguard Intelligence..." + send button `text-primary`

**Preserve all existing state logic and API calls from `TranslateForm`. The component restructure is visual only.**

---

## STEP 7 — COMPONENT: ResumeOutput.jsx

Replace `frontend/src/components/ResumeOutput.jsx`.

**Design spec:** Render the resume result as a "Technical Brief" card.
- Container: `bg-surface-container-low p-6 mt-4`
- Title: `font-headline font-bold text-2xl uppercase text-on-surface`
- Section label: `font-label text-xs tracking-widest uppercase text-on-surface-variant mb-2`
- Summary: `font-body text-sm text-on-surface-variant leading-relaxed`
- Bullets: each prefixed with `text-secondary` checkmark icon `✓`, `font-body text-sm text-on-surface`
- No borders. Separation via tonal bg shifts only.

---

## STEP 8 — PAGE: Contacts.jsx

Replace `frontend/src/pages/Contacts.jsx`.

**Design spec (from `.stitch/contacts_tactical_redesign/`):**
- Page header: status chip + "OPERATOR INTEL" headline `font-headline font-bold text-4xl uppercase`
- "+ ADD CONTACT" button: `mission-gradient` rounded-md `font-label text-xs tracking-widest uppercase`
- Contact cards: `bg-surface-container` no border
  - Name: `font-headline font-semibold text-on-surface`
  - Email / company: `font-label text-xs tracking-widest uppercase text-on-surface-variant`
  - Edit / Delete: `text-tertiary` and `text-error` text links, no button chrome
- Form (when open): slide-in `bg-surface-container-low` panel using `tactical-input` for all fields
- Labels on all inputs: `font-label text-xs tracking-widest uppercase text-on-surface-variant`

**All existing CRUD logic unchanged.**

---

## STEP 9 — COMPONENT: TranslateForm.jsx

Update `frontend/src/components/TranslateForm.jsx` to use `tactical-input` class on textareas and Vanguard button styles. Logic is unchanged. Labels become `font-label text-xs tracking-widest uppercase text-on-surface-variant`.

---

## STEP 10 — VERIFY

After all files are updated:

```bash
# 1. Confirm backend tests still pass
cd backend && pytest --tb=short -q

# 2. Start frontend dev server
cd frontend && npm run dev

# 3. Smoke test manually:
# - /login renders dark tactical UI
# - /register renders correctly
# - Login flow works (auth logic unchanged)
# - /dashboard shows resume list
# - /translator shows translate form and outputs result
# - /contacts shows contacts list
```

Fix any Tailwind class errors (class names must match the token names in tailwind.config.js exactly). Fix any import errors. Do not add new packages.

---

## HARD RULES (from CLAUDE.md)

- Do NOT add packages
- Do NOT change model field names
- Do NOT modify `docker-compose.yml`, `.env`, or any backend file
- Do NOT change API endpoint paths or request/response shapes
- Do NOT store JWTs in localStorage (existing client.js pattern stays)
- All API calls stay relative paths (`/api/v1/...`)
- Auth logic in `AuthContext.jsx` is read-only — only JSX consumers change

---

## DELIVERABLE

When complete, output:
1. List of every file modified
2. Confirmation that `pytest` passed
3. Any deviations from spec and why
