# Task Tracker Interface Patterns

This file records the visual and interaction conventions currently implemented in `frontend/src`. It is descriptive, not a roadmap. When it conflicts with the application, the current implementation is the source of truth.

## Direction

Task Tracker is a dense operational interface for recurring Payroll and Sales Tax work. It should feel like a dark technical ledger: sober, precise, readable, and structured by dates and thin rules. Visual hierarchy comes from typography, borders, and quiet surface shifts rather than decoration or card elevation.

## Color tokens

The implemented tokens live in `styles.css`:

| Token | Value | Current role |
| --- | --- | --- |
| `--canvas-deep` | `#051419` | Body and access-screen background |
| `--canvas` | `#07191e` | Page and navigation background |
| `--surface-1` | `#0a2026` | Hovered rows/cells and Calendar detail surface |
| `--surface-2` | `#0d272e` | Defined dark elevated surface token |
| `--surface-inset` | `#06161a` | Input and select backgrounds |
| `--text-primary` | `#edf3ef` | Headings, company names, active navigation, input text |
| `--text-secondary` | `#a8b8bc` | Supporting content and operational values |
| `--text-tertiary` | `#7e9298` | Metadata, inactive navigation, labels, empty states |
| `--text-muted` | `#5f747a` | De-emphasized dates, access numbering, outside-month content |
| `--mint` | `#99d9ba` | Primary action, active rules, Payroll distinction, focus |
| `--mint-strong` | `#b8ead1` | Mint hover state |
| `--line` | `rgba(151, 181, 186, 0.2)` | Standard structural borders |
| `--line-soft` | `rgba(151, 181, 186, 0.11)` | Calendar cell divisions and quiet separators |
| `--line-emphasis` | `rgba(153, 217, 186, 0.55)` | Hovered control borders |
| `--danger` | `#e2948d` | Errors and delete actions |
| `--warning` | `#d6bf78` | Pending status |
| `--progress` | `#89b6cd` | In Progress status |
| `--success` | `#8ccbaa` | Completed status |

Mint is the single identity accent. Semantic colors are restrained and reserved for status, errors, and destructive actions. Payroll uses mint; Sales Tax uses a neutral blue-gray (`#aebfc5`) rather than introducing another accent family.

## Typography roles

- `Manrope` is the primary sans-serif. It carries page headings, company names, navigation, body copy, and controls.
- `IBM Plex Mono` is used for dates, statuses, task types, counts, access-mode labels, form labels, metadata, and small operational details.
- Body text defaults to `1rem` with weight `500`.
- Page headings are bold, tightly tracked, and operationally sized with `clamp(1.85rem, 4vw, 2.6rem)` and weight `700`.
- The access-screen heading is the one larger exception, using `clamp(2rem, 7vw, 3.4rem)`.
- Small technical labels are generally uppercase, letter-spaced, and at least `0.7rem`; primary dates and operational values are around `0.88–0.95rem`.
- Company names and section headings remain in sentence/title case; uppercase is reserved for compact metadata rather than ordinary copy.

## Spacing principles

The interface uses compact spacing bands rather than a formally tokenized spacing scale:

- Micro gaps and label offsets: roughly `4–12px`.
- Control and component spacing: roughly `13–24px`.
- Section and page separation: roughly `28–44px`.
- Desktop content gutters: `32px` per side through `calc(100% - 64px)`.
- Mobile content gutters: `14px` per side through `calc(100% - 28px)`.

Spacing should preserve scanability without creating isolated cards. Horizontal and vertical padding is usually balanced. Weekly rows are intentionally asymmetric: extra left padding makes room for the operational date rail.

## Borders, depth, and radius

- Depth is borders-first, supported by quiet dark surface shifts. There are no elevation shadows.
- Standard structure uses a `1px` low-opacity border.
- Softer calendar divisions use `--line-soft`; active or focus structure uses mint or `--line-emphasis`.
- The Weekly rail, active navigation underline, and error edge are `2px`; the selected Calendar rail is `3px`.
- Controls and status labels use `--radius-small: 3px`.
- `--radius-medium: 5px` is declared, but current components do not use it.
- The selected Calendar cell uses an inset mint `box-shadow` as a structural edge, not as elevation.

## Navigation patterns

The authenticated application shell uses a compact horizontal header on a subtly deeper surface than the page.

- Desktop is a three-zone grid within the same `1520px` maximum width as the main content: Task Tracker identity on the left, primary navigation centered, access context on the right.
- The product identity begins with a small solid mint square followed by `Task Tracker`.
- Active navigation uses primary text plus a thin mint underline.
- Inactive navigation is tertiary text and becomes primary on hover.
- Guest navigation contains Weekly and Calendar.
- Admin navigation contains Weekly, Calendar, and Clients.
- Access context shows the current mode in small mono uppercase text and a visually secondary action: `Log out` for Admin or `Change access` for Guest.
- At `700px` and below, the brand and access action remain on the first row while navigation moves to a full-width second row separated by a soft border.

The entry screen is a centered, narrow access panel. Guest and Admin are presented as numbered ruled rows, not cards. Admin authentication replaces the choices with one password form and Back/Sign in actions.

## Operational date rail

The signature pattern is a thin vertical rule paired with monospaced operational dates and metadata.

- Every Weekly task row has a muted `2px` left rail that turns mint on hover.
- A selected Calendar day has an inset mint left rail.
- Compact Calendar task entries have their own `1px` left rule; Payroll uses mint and Sales Tax uses the muted neutral rule.
- Dates, task types, statuses, counts, and recurrence metadata use mono typography so the rail reads as operational scheduling structure rather than decoration.
- Active navigation and filter underlines echo the same thin-rule language without becoming additional color accents.

## Weekly row pattern

- Weekly remains a continuous ruled list with top and bottom borders, never a card grid.
- Desktop uses an aligned five-region row: Company, Task type, Process/Due, Pay date, and Status.
- A compact mono column-heading row reinforces alignment without turning Weekly into a table component.
- Payroll uses both date columns; Sales Tax uses the Process/Due column and leaves Pay date empty.
- Each date keeps its compact label above the larger mono value so the row remains understandable when headings hide responsively.
- Hover adds only a barely visible mint-tinted surface shift and activates the left rail.
- All, Payroll, and Sales Tax filters are a ruled tab row with mono count boxes and a mint active underline.
- Previous/Next Week controls remain paired at the page-header edge.
- Loading, empty, and error states stay within the same list flow.

## Calendar grid pattern

- Calendar uses one continuous seven-column, Monday-first grid with 42 day cells. Desktop cells are at least `138px` wide and `158px` tall.
- Weekday headings are compact uppercase mono labels.
- Day numbers are mono; days outside the active month are muted and slightly darker.
- Day cells are buttons with subtle row/column rules, not individual cards.
- Each day shows up to three compact task entries; additional items collapse to a `+N more` label.
- Task entries show company first and task type second, both truncated when needed.
- Selection is communicated by an inset mint rail and a quiet mint surface tint.
- Desktop pairs the grid with a `340px` selected-day detail panel on the right.
- The detail panel reuses task-type and status styling and shows the existing Payroll or Sales Tax date fields.
- Calendar status is presented as information; status editing remains in the Admin Weekly workflow.
- At narrower widths the grid scrolls horizontally rather than collapsing into an unrelated agenda layout.

## Client list and form conventions

- Clients is a ruled list, not a collection of cards.
- Desktop client rows use five aligned regions: Company, Services, Payroll platform, Frequency, and Actions.
- A compact mono heading row labels those regions on wide screens.
- EIN and frequency metadata use readable mono styling; company, services, and platform values use the primary sans hierarchy.
- Edit is a bordered secondary action; Delete is transparent and uses the danger color.
- Forms use a constrained `900px` content width and native accessible inputs, selects, dates, numbers, and checkboxes.
- Company, Payroll, and Sales Tax are fieldsets separated by thin horizontal rules rather than nested containers.
- Form labels are uppercase mono metadata; field values remain primary sans-serif text.
- Form fields use two columns on wider screens and one column on mobile.
- Payroll and Sales Tax enabled controls stay aligned with their fieldset legends.
- Form actions are right-aligned and use the shared secondary/primary button treatment.

## Repeated configuration pattern

- Repeated operational configurations, including Payroll Schedules and Sales Tax Registrations, use continuous ruled groups rather than cards.
- Each group begins with a compact identity line and keeps its related form controls aligned to the shared form grid.
- Separate neighboring groups with restrained low-opacity rules. Do not introduce additional surfaces, shadows, or nested containers to distinguish them.
- Add actions belong at the parent section level so they apply clearly to the full configuration collection.
- Remove or archive actions remain visually secondary. Use the established destructive color and quiet button treatment so their consequence is clear without competing with primary save actions.
- Jurisdiction, task source, and other compact source metadata use the existing uppercase IBM Plex Mono operational style.
- Weekly and Calendar identify a task source in one compact, middle-dot-separated line:
  - `PAYROLL · Employees · FL`
  - `SALES TAX · GA`
- Preserve the ledger-inspired border, typography, spacing, and color system when applying this pattern.
- Do not convert repeated configurations into pills, badges, nested cards, wizard steps, or a new accent-color taxonomy.

## Guest and Admin UI behavior

- A fresh unauthenticated visit shows the access screen.
- Guest enters without authentication and receives only Weekly and Calendar navigation.
- Guest task statuses are non-interactive bordered labels. Do not render a disabled select that implies edit access.
- Admin authentication restores the full application shell with Clients navigation.
- Admin Weekly rows use the native status select and retain the semantic status treatment.
- Calendar is one shared view for both modes and does not fork into role-specific versions.
- Logout and Change access are secondary text actions, not primary navigation destinations.
- Administrative UI must not be rendered for Guest even though backend authorization remains the ultimate enforcement boundary.

## Status presentation

Status uses the same semantic language whether rendered as an Admin select or a read-only label:

- Pending: muted gold (`--warning`).
- In Progress: muted blue (`--progress`).
- Completed: muted green (`--success`).

Statuses use uppercase IBM Plex Mono at compact size with a thin, color-related border. They are not filled pills. Calendar details and Guest Weekly rows use labels; Admin Weekly rows use selects.

## Responsive principles

- Preserve the operational structure before reducing density.
- At `1100px`, Weekly and Client column-heading rows hide and the operational columns tighten.
- At `900px`, Calendar detail moves below the grid and detail tasks may use two columns; the Client payroll-platform column hides temporarily to preserve the row.
- At `700px`, the header becomes two rows; page headers stack; Weekly becomes a logical two-column stack with company and status spanning the row; Clients and forms become single-column; Calendar retains horizontal scrolling.
- Period navigation buttons share the available width on mobile.
- Status controls expand to full row width after Weekly rows stack.
- At `440px`, the access-mode text in the header hides while the access action remains available, and small gaps tighten further.
- The minimum supported viewport is `320px`.

## Explicit anti-patterns

- No gradients, glow effects, dramatic shadows, or decorative background effects.
- No generic dashboard sidebar, metric-card grid, or floating-card composition.
- No cards nested inside cards; use continuous ruled lists, grids, and fieldset dividers.
- No excessive pills or large rounded corners.
- No rainbow task taxonomy; mint and neutral blue-gray distinguish task types, while semantic colors belong to status.
- No huge marketing headings, eyebrows, promotional copy, or decorative branding inside the operational app.
- No decorative icons where text already communicates the action.
- No custom controls solely for appearance when the current native control is accessible and sufficient.
- No duplicate Guest/Admin Calendar or task models.
- No editable-looking status control for Guest.
- No conversion of Weekly or Clients into card dashboards.
