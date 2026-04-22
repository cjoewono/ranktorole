# Design System: RankToRole

**Project ID:** _(assign after first Stitch generation)_

---

## 1. Visual Theme & Atmosphere

**RankToRole** bridges the military world and the civilian tech sector. The aesthetic must project two things simultaneously: the discipline and authority veterans carry, and the forward momentum of a tech career starting now.

**Vibe:** Sophisticated, trustworthy, and tech-forward. Not corporate-sterile — there is warmth in the amber accent that acknowledges the user's service. Not military-heavy — no camouflage, no stars-and-stripes. Instead: precision geometry, confident typography, and a cool blue palette that signals competence without coldness.

**Emotional arc of the UI:** The user arrives uncertain (career pivot anxiety) and leaves confident (resume drafted, future visible). Every design decision should reduce friction and reinforce that this tool is credible and on their side.

---

## 2. Color Palette & Roles

| Name                 | Hex       | Tailwind Equivalent | Role                                                    |
| -------------------- | --------- | ------------------- | ------------------------------------------------------- |
| **Command Navy**     | `#0f172a` | `slate-900`         | Primary surface, hero backgrounds, nav bar              |
| **Trust Blue**       | `#1d4ed8` | `blue-700`          | Primary action buttons, active states, links            |
| **Sky Accent**       | `#3b82f6` | `blue-500`          | Hover states, highlights, focus rings                   |
| **Transition Amber** | `#f59e0b` | `amber-400`         | Achievement badges, progress indicators, warmth accents |
| **Interface White**  | `#f8fafc` | `slate-50`          | Page backgrounds, card surfaces                         |
| **Slate Mid**        | `#64748b` | `slate-500`         | Secondary text, placeholders, dividers                  |
| **Slate Light**      | `#cbd5e1` | `slate-300`         | Borders, disabled states, input outlines                |
| **Success Green**    | `#10b981` | `emerald-500`       | Finalized state, validation success, checkmarks         |
| **Alert Red**        | `#ef4444` | `red-500`           | Errors, validation failures, destructive actions        |

**Palette philosophy:** Command Navy grounds the layout. Trust Blue drives action. Transition Amber rewards the user's progress — it appears _only_ on achievement moments (draft generated, resume finalized) to preserve its emotional weight.

---

## 3. Typography Rules

**Font Stack:** `Inter, ui-sans-serif, system-ui, sans-serif`

- Inter is clean, geometric, and used widely in tech products — signals credibility immediately.
- No serif fonts. The aesthetic is modern-professional, not academic.

**Monospace (for resume bullets, code-like data):** `JetBrains Mono, ui-monospace, monospace`

- Used sparingly for extracted resume text, bullet previews, and any raw text display areas.

| Role                 | Size               | Weight                | Color                | Notes                            |
| -------------------- | ------------------ | --------------------- | -------------------- | -------------------------------- |
| Page Title / Hero H1 | `text-4xl` (36px)  | `font-bold` (700)     | `slate-900` or white | Tight tracking: `tracking-tight` |
| Section Heading H2   | `text-2xl` (24px)  | `font-semibold` (600) | `slate-900`          |                                  |
| Card Title H3        | `text-lg` (18px)   | `font-semibold` (600) | `slate-900`          |                                  |
| Body / Paragraph     | `text-base` (16px) | `font-normal` (400)   | `slate-600`          | Line height: `leading-relaxed`   |
| Helper / Caption     | `text-sm` (14px)   | `font-normal` (400)   | `slate-500`          |                                  |
| Button Label         | `text-sm` (14px)   | `font-medium` (500)   | White or `blue-700`  | Uppercase tracking optional      |
| Badge / Tag          | `text-xs` (12px)   | `font-semibold` (600) | Varies               | Pill-shaped containers           |

---

## 4. Component Stylings

### Buttons

- **Primary CTA** (e.g., "Generate Draft", "Approve & Finalize"): Solid Trust Blue (`bg-blue-700`), white text, softly rounded (`rounded-lg`), hover darkens to `blue-800`, focus ring in Sky Accent. Padding: `px-6 py-2.5`.
- **Secondary** (e.g., "Upload Another", "Cancel"): White background, `border border-slate-300`, `text-slate-700`, hover `bg-slate-50`.
- **Danger** (e.g., "Delete Resume"): `bg-red-50 text-red-600 border border-red-200`, hover `bg-red-100`.
- **Disabled state**: `opacity-50 cursor-not-allowed` — never hide disabled buttons, just mute them.
- **Shape rule**: All buttons use `rounded-lg` (8px). Never pill-shaped for primary actions — pills are for tags/badges only.

### Cards & Containers

- Background: `bg-white`, border: `border border-slate-200`, radius: `rounded-xl` (12px).
- Elevation: Whisper-soft shadow — `shadow-sm` for resting state, `shadow-md` on hover/focus.
- Padding: `p-6` standard, `p-4` compact.

### Input Fields

- Border: `border border-slate-300`, radius: `rounded-lg`.
- Focus: `ring-2 ring-blue-500 border-blue-500` (Sky Accent ring).
- Background: `bg-white`, placeholder text: `text-slate-400`.
- Error state: `border-red-400 ring-red-200`.

### Status Badges / Pipeline State Tags

- Shape: Pill (`rounded-full`), `text-xs font-semibold`, `px-3 py-1`.
- `UPLOADED` → `bg-slate-100 text-slate-600`
- `DRAFTING` → `bg-blue-100 text-blue-700`
- `REVIEWING` → `bg-amber-100 text-amber-700`
- `FINALIZING` → `bg-purple-100 text-purple-700`
- `DONE` → `bg-emerald-100 text-emerald-700`

### Navigation Bar

- Background: Command Navy (`bg-slate-900`), sticky top.
- Logo: White wordmark, `font-bold text-xl`, left-aligned.
- Nav links: `text-slate-300` default, `text-white` active, `hover:text-white` transition.
- Height: `h-16` (`64px`).

### Chat Interface (Resume refinement turns)

- User messages: Right-aligned, `bg-blue-600 text-white rounded-2xl rounded-br-sm`.
- Assistant messages: Left-aligned, `bg-slate-100 text-slate-800 rounded-2xl rounded-bl-sm`.
- Timestamp / meta: `text-xs text-slate-400` below each bubble.

---

## 5. Layout Principles

**Grid:** 12-column grid with `max-w-5xl` (1024px) centered container and `px-6` gutter. Two-column split (`grid-cols-2`) for resume input vs. preview. Single column on mobile.

**Whitespace strategy:** Generous. Section spacing `py-16` between major blocks. Card groups `gap-6`. Never crowd the page — the user is already stressed about their career pivot. Open space = confidence.

**Hierarchy rule:** One dominant action per screen. Every page has exactly one Trust Blue primary button in view. Secondary actions are visually recessive.

**Responsive breakpoints (Tailwind defaults):**

- Mobile-first base styles
- `sm:` (640px) — two-column where applicable
- `lg:` (1024px) — full layout, sidebar patterns

**Page-level backgrounds:**

- Auth pages (login, register): Command Navy full-screen background with a centered white card.
- App pages (dashboard, resume builder): `bg-slate-50` page background, white content cards.

---

## 6. Motion & Micro-interactions

- **Transitions:** `transition-colors duration-200` on all interactive elements.
- **Loading states:** Pulsing skeleton loaders (`animate-pulse bg-slate-200`) while LLM is generating — never a spinner alone.
- **State changes:** Draft appearing animates in with `animate-fade-in` (custom: `opacity-0 → opacity-100` over `300ms`).
- **No decorative animations** — this is a productivity tool, not a marketing site. Motion serves function only.

---

## 7. Iconography

- **Library:** Heroicons (already compatible with Tailwind/React).
- **Style:** Outline icons at `20px` (`w-5 h-5`) for UI chrome; solid at `24px` for emphasis.
- **Color:** Always inherit from parent text color — never hardcode icon colors independently.

---

## 9. Utility Classes

Shared CSS utilities defined in `frontend/src/index.css` via `@layer components`.

| Class             | Expands to                                     | Usage                                            |
| ----------------- | ---------------------------------------------- | ------------------------------------------------ |
| `.label-tactical` | `font-label text-xs tracking-widest uppercase` | Form labels, section labels, small caps headings |

### Form components

Canonical form primitives live in `frontend/src/components/forms/`:

| Component        | File                 | Props                                                     | Usage                                                                   |
| ---------------- | -------------------- | --------------------------------------------------------- | ----------------------------------------------------------------------- |
| `TacticalLabel`  | `TacticalLabel.jsx`  | `children`, `htmlFor`                                     | Wrap label text; pass `htmlFor` to link to input `id` for accessibility |
| `TacticalSelect` | `TacticalSelect.jsx` | `value`, `onChange`, `required`, `id`, `name`, `children` | Styled `<select>` with `tactical-input` + `appearance-none`             |

`TacticalLabel` and `TacticalSelect` are the **canonical primitives** for form labels and selects. Use these in all new form work.

**Migration status (as of April 22, 2026):** ForgeSetup, Login, and Register are fully migrated. Contacts and CareerRecon are **not yet migrated** — their form layouts diverge (avatar logic, branch dropdown) and are deferred post-launch.

---

## 8. Stitch Prompt Template

Use this block as the opening of any new screen prompt passed to Stitch:

```
Professional, trustworthy, and tech-forward UI for a military-to-civilian career transition platform.

**DESIGN SYSTEM (REQUIRED):**
- Platform: Web, desktop-first (responsive to mobile)
- Palette: Command Navy (#0f172a, backgrounds/nav), Trust Blue (#1d4ed8, primary actions), Sky Accent (#3b82f6, hover/focus), Transition Amber (#f59e0b, achievement moments), Interface White (#f8fafc, page bg), Slate grays for text hierarchy
- Typography: Inter sans-serif; bold h1 (36px), semibold h2 (24px), normal body (16px slate-600)
- Geometry: Softly rounded cards (rounded-xl), rounded-lg buttons and inputs, pill badges only
- Elevation: Whisper-soft shadows (shadow-sm resting, shadow-md on hover)
- Atmosphere: Sophisticated yet approachable — discipline of military precision meets modern tech product clarity
```
