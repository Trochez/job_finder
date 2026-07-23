# job_finder Dashboard — Design System

## Design Tokens

### Color Palette

| Token                     | Value   | Usage                           |
|---------------------------|---------|---------------------------------|
| `--color-primary`         | #1a56db | Brand, nav, primary actions     |
| `--color-primary-hover`   | #1648c0 | Button hover states             |
| `--color-surface`         | #ffffff | Card, sidebar, modal backgrounds|
| `--color-bg`              | #f3f4f6 | Page background                 |
| `--color-text`            | #111827 | Body text                       |
| `--color-text-secondary`  | #6b7280 | Labels, captions, meta          |
| `--color-border`          | #d1d5db | Dividers, table borders         |
| `--color-success`         | #059669 | Eligible, positive states       |
| `--color-warning`         | #d97706 | Threshold near-limit, paused    |
| `--color-error`           | #dc2626 | Ineligible, errors, failures    |
| `--color-info`            | #0284c7 | Info badges, neutral states     |

### Typography

- **Font stack**: `system-ui, -apple-system, sans-serif` (no external fonts)
- **Scale**:

| Level     | Size     | Weight  | Line Height |
|-----------|----------|---------|-------------|
| h1        | 1.5rem   | 700     | 1.2         |
| h2        | 1.25rem  | 600     | 1.3         |
| h3        | 1.125rem | 600     | 1.4         |
| body      | 0.875rem | 400     | 1.5         |
| small     | 0.75rem  | 400     | 1.5         |
| label     | 0.8125rem| 500     | 1.4         |

### Spacing

4px base unit (0.25rem). Scale: `0.25rem` (xs), `0.5rem` (sm), `1rem` (md), `1.5rem` (lg), `2rem` (xl), `3rem` (2xl).

### Border Radius

- Small: `0.25rem` (inputs, badges)
- Medium: `0.375rem` (cards, buttons)
- Large: `0.5rem` (modals, panels)

### Shadows

- Card: `0 1px 3px 0 rgba(0,0,0,0.1), 0 1px 2px -1px rgba(0,0,0,0.1)`
- Elevated: `0 4px 6px -1px rgba(0,0,0,0.1), 0 2px 4px -2px rgba(0,0,0,0.1)`

## Navigation Structure

```
Dashboard                   GET /dashboard
Profile Settings            GET/POST /profile-settings
CV Source                   GET/POST /cv-source
Job Review                  GET /job-review
Audit                       GET /audit
Checkpoints                 GET/POST /checkpoints
```

Navigation is a top horizontal bar with active-page indicator. On viewports < 768px collapses to hamburger.

## Responsive Breakpoints

| Name      | Width    | Layout                         |
|-----------|----------|--------------------------------|
| Mobile    | 375px    | Single column, collapsed nav   |
| Tablet    | 768px    | Single column, expanded nav    |
| Desktop   | 1024px   | Two-column grid (filters+content) |
| Wide      | 1280px   | Max-width container, spacious  |

## Accessibility Targets

- **Semantic HTML**: `<nav>`, `<main>`, `<section>`, `<header>`, `<footer>`, `<table>`, `<form>`
- **Heading hierarchy**: h1 (page title) -> h2 (section) -> h3 (subsection). No jumps.
- **Focus management**: Visible `:focus-visible` ring on all interactive elements. Skip-to-content link.
- **ARIA**: `aria-current="page"` on active nav, `aria-label` on icon-only controls, `aria-describedby` on form inputs with help text, `role="status"` on live regions.
- **Keyboard**: All controls reachable via Tab. Forms submit on Enter. Checkpoints actionable via Space/Enter.
- **Color contrast**: All text meets WCAG AA (4.5:1 ratio minimum).
- **Reduced motion**: `@media (prefers-reduced-motion)` disables non-essential animations.
- **Error messages**: Inline, associated with input via `aria-describedby`. Not just color-coded.
- **Empty states**: Meaningful messages with guidance, not blank panels.
