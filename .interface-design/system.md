# Task Tracker interface system

Task Tracker is a dense accounting operations product. Its implemented visual language is deep navy, warm gold, and warm white: professional, restrained, and structured with continuous rules rather than floating cards.

## Core tokens

The source of truth is `frontend/src/styles.css`.

| Token | Value | Role |
| --- | --- | --- |
| `--canvas-deep` | `#09172B` | Access screen and deepest backdrop |
| `--canvas` | `#0E1E35` | Main application background |
| `--surface-1` | `#142944` | Selected, hovered, and detail surfaces |
| `--surface-2` | `#1A3150` | Optional stronger hierarchy |
| `--surface-inset` | `#0A192D` | Header and form-control inset surface |
| `--gold` | `#E9C34A` | Identity, focus, selection, and primary actions |
| `--gold-strong` | `#F0CF66` | Gold hover/highlight |
| `--text-primary` | `#F4F4F1` | Headings and high-priority content |
| `--text-secondary` | `#AEB7C2` | Supporting copy and operational values |
| `--text-tertiary` | `#8794A4` | Labels and secondary navigation |
| `--text-muted` | `#68778A` | Outside-month and de-emphasized content |
| `--border` | `#263851` | Opaque structural-border reference |

Low-opacity line tokens derive from the same muted navy/gray family. Semantic warning, progress, success, and danger colors remain deliberately subdued so status never competes with the navy/gold identity.

## Typography

- Poppins is the only UI family: weight 400 for body/supporting text, 500 for controls and values, 600 for navigation and labels, and 700 for headings and important values.
- Dates and numbers stay in Poppins and use `font-variant-numeric: tabular-nums` where alignment improves scanning.
- Normal labels use sentence or title case. Uppercase is limited to compact operational metadata and status labels; it is not the default voice.
- Page headings use responsive sizing and tight but restrained tracking. The product remains operational, not promotional.

## Structure and spacing

- Use 4–12px for micro spacing, 13–24px within controls and rows, and 28–48px between major sections.
- Desktop gutters are 32px; mobile gutters are 14px. Content is capped at 1520px and forms at 1040px.
- Structure comes from one-pixel borders, continuous ruled lists, and quiet navy surface shifts. Gold rules are reserved for active/focus structure.
- Radius stays restrained at 3px for controls and labels. There are no elevation shadows.

## Navigation and access

- The top header uses the darker navy inset surface with a thin gold lower rule.
- Task Tracker remains a text identity with a small gold marker. No external company branding or logo is used.
- Active navigation is warm white with a gold underline; inactive navigation is muted and brightens on hover.
- Guest/Admin access behavior and visibility remain unchanged. The access screen uses the same ruled rows, navy surfaces, Poppins hierarchy, and gold focus states.

## Operational views

### Weekly

Weekly remains an aligned five-region ruled list: Company, Task, Process/Due, Pay Date, and Status. Rows are never individual cards. The left operational rail turns gold on hover; dates use tabular numerals. Payroll/Sales Tax distinctions remain subtle, while status keeps its existing behavior and restrained semantic colors.

### Calendar

Calendar remains a Monday-first 42-cell grid with a selected-day detail panel. Cells share continuous borders and scroll horizontally when needed. The selected date gets a quiet gold rail/tint. Compact task entries avoid a rainbow taxonomy. The header groups the monthly PDF download with Previous/Next Month controls and wraps the download action to a full row on narrow screens.

### Clients and forms

Clients remains a ruled list with aligned operational columns. Client forms use native controls, shared field grids, and horizontal fieldset dividers. Repeated Payroll Schedules and Sales Tax Registrations remain continuous configuration groups separated by quiet rules—never nested cards, pills, or wizard steps.

## Responsive behavior

- At 1100px, dense column headings hide and rows tighten.
- At 900px, Calendar detail moves below the grid and secondary Client columns may hide.
- At 700px, the header becomes two rows; page headers stack; Weekly and Clients reflow; forms become one column; Calendar retains horizontal scrolling; monthly PDF download spans the control row.
- The minimum supported viewport is 320px.

## Explicit anti-patterns

- No gradients, glows, dramatic shadows, large radii, floating cards, or cards inside cards.
- No marketing-site sections, promotional copy, imagery, logos, or borrowed brand content.
- No dashboard sidebar, metric-card grid, rainbow taxonomy, or decorative icon set.
- Do not turn Weekly, Calendar, Clients, or repeated configurations into unrelated layouts.
- Do not use gold everywhere: reserve it for identity, selected states, primary actions, focus, and a few structural rules.
- Do not use a monospace family as a second identity font; operational alignment comes from tabular numerals.
- Do not render editable-looking status controls for Guest or change Guest/Admin behavior for styling.
