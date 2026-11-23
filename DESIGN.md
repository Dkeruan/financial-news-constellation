---
name: Financial News Constellation
description: Company-targeted news sentiment on a warm, dark analytics board.
colors:
  canvas: "#e7e5e2"
  surface: "#f4f2ef"
  ink: "#181818"
  muted: "#5e5d5a"
  quiet: "#777572"
  line: "#cfccc8"
  panel: "#242424"
  panel-raised: "#30302f"
  panel-ink: "#f5f4f2"
  panel-muted: "#b9b7b4"
  panel-line: "#4a4947"
  accent: "#c43a50"
  accent-bright: "#fa7182"
  action: "#111111"
  action-hover: "#353535"
  action-disabled: "#626262"
  white: "#ffffff"
  positive: "#82dc98"
  negative: "#ff7887"
  neutral: "#c1c4c9"
  co-mention-edge: "#858b91"
  chart-zero: "#aaa7a3"
  chart-axis: "#c4c2bf"
  chart-grid: "rgba(214,211,207,.16)"
  graph-label: "#e4e2df"
  unscored: "#dedbd6"
  selection: "#f5b8c0"
typography:
  display:
    fontFamily: "sans-serif"
    fontSize: "clamp(1.8rem, 3vw, 2.45rem)"
    fontWeight: 620
    lineHeight: 1.08
    letterSpacing: "-0.035em"
  brand-name:
    fontFamily: "sans-serif"
    fontSize: "1.88rem"
    fontWeight: 620
    letterSpacing: "-0.045em"
  section-title:
    fontFamily: "sans-serif"
    fontSize: "1.42rem"
    fontWeight: 620
    letterSpacing: "-0.035em"
  subsection-title:
    fontFamily: "sans-serif"
    fontSize: "1.02rem"
    fontWeight: 620
  body:
    fontFamily: "sans-serif"
  description:
    fontSize: "0.88rem"
  section-note:
    fontSize: "0.8rem"
    lineHeight: 1.45
  label:
    fontSize: "0.75rem"
    fontWeight: 650
    lineHeight: 1.35
  coverage-value:
    fontSize: "1.62rem"
    fontWeight: 560
  metric-value:
    fontSize: "2rem"
    fontWeight: 650
    lineHeight: 1.05
    letterSpacing: "-0.04em"
  article-title:
    fontSize: "0.78rem"
    fontWeight: 560
    lineHeight: 1.35
  article-meta:
    fontSize: "0.67rem"
    lineHeight: 1.35
rounded:
  panel: "18px"
  panel-mobile: "15px"
  disclosure: "12px"
  table: "12px"
  empty-state: "16px"
  pill: "999px"
spacing:
  content-max-width: "1540px"
  desktop-top: "1.35rem"
  desktop-bottom: "2.2rem"
  mobile-gutter: "0.85rem"
  mobile-top: "1rem"
  mobile-bottom: "1.35rem"
  setup-padding: "0.8rem 1rem"
  panel-padding: "1rem 1.1rem"
  mobile-panel-padding: "0.75rem 0.8rem"
components:
  button-primary:
    backgroundColor: "{colors.action}"
    textColor: "{colors.white}"
    rounded: "{rounded.pill}"
  button-primary-hover:
    backgroundColor: "{colors.action-hover}"
  button-primary-disabled:
    backgroundColor: "{colors.action-disabled}"
    textColor: "{colors.white}"
  button-secondary:
    rounded: "{rounded.pill}"
  card-research:
    backgroundColor: "{colors.surface}"
    rounded: "{rounded.panel}"
    padding: "{spacing.setup-padding}"
  card-analytics:
    backgroundColor: "{colors.panel}"
    textColor: "{colors.panel-ink}"
    rounded: "{rounded.panel}"
    padding: "{spacing.panel-padding}"
  select-company:
    backgroundColor: "{colors.panel-raised}"
    textColor: "{colors.panel-ink}"
  chip-positive:
    backgroundColor: "rgba(130,220,152,.13)"
    textColor: "{colors.positive}"
    rounded: "{rounded.pill}"
  chip-negative:
    backgroundColor: "rgba(255,120,135,.13)"
    textColor: "{colors.negative}"
    rounded: "{rounded.pill}"
  chip-neutral:
    backgroundColor: "rgba(193,196,201,.13)"
    textColor: "{colors.neutral}"
    rounded: "{rounded.pill}"
---

# Design System: Financial News Constellation

## Overview

**Creative North Star: "The Analyst's Signal Board"**

Financial News Constellation uses a warm gray shell around a compact research setup and a charcoal analysis board. The header pairs the product name with a view toggle. Research controls gather company targets, bundled or user-added RSS feeds, a lookback window, and the primary action; source health, registry editing, and CSV import stay in disclosures. With results, the selected-company sentiment index and targeted article count lead, with total headline, company, feed, freshness, and run-status context tucked beneath them. The company network sits beside that signal summary; the larger sentiment trend leads the evidence row beside recent article analytics. Full article browsing and model details remain below in disclosures.

The surface hierarchy is built through tone and contrast: the setup area sits on a light warm surface, while coverage and analysis share dark charcoal panels with soft text and fine borders. The Research action is black; coral marks focus and interaction, with brighter coral in the trend and selected-node outline. Vivid green, rose, and silver carry positive, negative, and near-neutral sentiment. Typography inherits a sans-serif theme, keeping labels and article rows compact while numeric values stay easy to scan.

**Key Characteristics:**
- **Warm shell, dark analysis:** warm gray frames the page; charcoal panels hold the data work.
- **Black action, coral signal:** the Research control stays black while coral is reserved for interaction and chart emphasis.
- **Explicit sentiment:** bright class colors appear with labels and numeric estimates.

<!-- Not canonized: the unused `.bento-card` selector and the standalone legend's legacy dark green, gray, and red swatches remain in the source. Active analytics panels and network nodes use the current charcoal and bright sentiment palette. -->

## Colors

The palette pairs a warm gray canvas and ink with charcoal analytics surfaces, coral interaction accents, and bright sentiment colors.

### Primary
- **Coral Accent:** the configured Streamlit accent marks keyboard focus, text caret, and the network and trend chart's hover outlines.
- **Signal Coral:** the brighter coral draws the trend line and selected network node, and underlines article links on hover.
- **Black Research Action:** the primary button uses black with white text; its hover state darkens slightly and its disabled state lifts to a legible gray.

### Secondary
- **Positive Green:** the positive score, node, probability segment, article chip, and coverage status dot.
- **Negative Rose:** the negative score, node, probability segment, and article chip.
- **Neutral Silver:** the near-neutral score, node, probability segment, and article chip.

### Neutral
- **Warm Gray Canvas:** the page background around the working board.
- **Warm Surface:** the research setup, sidebar, and standard disclosures.
- **Charcoal Panel:** the constellation, company snapshot, article list, and trend chart.
- **Raised Charcoal:** the dark company selector, creating a small tonal step within the board.
- **Ink and Muted Ink:** headings use dark ink on the light shell; supporting copy uses muted ink. On analytics panels, light panel ink carries values and softer panel ink carries explanations.
- **Warm Borders:** a light border separates setup and disclosure surfaces; a deeper charcoal border separates analysis panels and their rows.
- **Chart Guides and Graph Lines:** muted silver supports chart axes and zero marks; slate connects co-mentioned companies; near-white ticker labels stay visible on charcoal.

**The Contrast Role Rule.** Keep the setup surface light and the analysis surface charcoal; reserve raised charcoal for nested controls.

**The Labeled Sentiment Rule.** Pair each sentiment color with its class label and a signed index or probability value. Describe probabilities as estimates rather than certainty or forecasts.

## Typography

**Display Font:** Streamlit's configured sans-serif theme
**Body Font:** the same inherited sans-serif theme
**Label/Mono Font:** no distinct label or mono face; Plotly labels use a system UI sans-serif stack.

**Character:** The type is compact and neutral so article detail and numeric signals carry the emphasis. Headings use tight tracking, while counts and scores use tabular numerals.

### Hierarchy
- **Display** (620, `clamp(1.8rem, 3vw, 2.45rem)`, 1.08 line-height): page-level headings.
- **Brand name** (620, `1.88rem`, `-0.045em` tracking): product identity in the header.
- **Section title** (620, `1.42rem`, `-0.035em` tracking): the main company analysis heading.
- **Subsection title** (620, `1.02rem`): snapshot, recent-article, trend, and method headings.
- **Description** (`0.88rem`, max `65ch`): the short product explanation beneath the brand.
- **Section note** (`0.8rem`, 1.45 line-height, max `72ch`): chart and article interpretation copy on dark panels.
- **Label** (650, `0.75rem`, 1.35 line-height): compact descriptors and form labels.
- **Metric value** (650, `2rem`, 1.05 line-height, `-0.04em` tracking): signed company index; the selected-company card enlarges it and the mobile rule reduces it slightly.
- **Article title and metadata** (`0.78rem` / `0.67rem`): a two-line-capped headline with a single compact source/date line.

**The Numeric Clarity Rule.** Use tabular numerals for counts, signed indices, and probability percentages; keep the index visually distinct from class probability.

## Layout

The wide Streamlit shell has a `1540px` maximum width. On desktop, the header places the product identity opposite the Demo or Research view action. The light research panel contains company selection and a compact feeds/lookback/Research control row; registry management, source status, and CSV input open below it.

When scored data is present, the first analysis row pairs the co-mention network with a company snapshot inside one shared panel, with a quiet vertical divider between them. This makes the graph and selected-company metrics read as one view. The snapshot leads with the selected company's signed sentiment index and unique article count; total headlines, companies, feeds or sources, freshness, run state, and unmatched count appear as a compact footer. The network gets a `1.48:1` width advantage over the snapshot. The next row puts the sentiment trend first and gives it a slight width advantage over recent article evidence (`1.2:1`). The network plot is `360px` high and the trend plot is `342px` high. The article panel shows up to six newest company-targeted rows; the separate all-article table and model quality/method stay collapsed below. Source status contains the RSS health table plus a local URL-and-label form for adding custom RSS/Atom feeds; adding a URL stores it without requesting it, and the feed picker selects it for a later Research run.

At widths up to `600px`, the shell tightens to `0.85rem` side gutters, the header stacks, and each panel uses smaller padding and `15px` corners. The constellation legend stacks into two compact lines. The analysis order remains network, company snapshot, sentiment trend, then recent article evidence, matching the DOM and focus order. Article rows keep signal details aligned to the right.

## Elevation & Depth

The working board has no authored shadows. Depth comes from the warm shell, light setup panel, charcoal analysis surfaces, and one raised charcoal layer for the nested company select. Thin borders separate adjacent panels and article rows without lifting the cards from the page.

**The Tonal Stack Rule.** Use the light surface for setup and supporting disclosures, charcoal for analysis, and raised charcoal for nested emphasis; the shipped system separates panels with tone and borders rather than shadows.

## Shapes

Cards use moderate `18px` corners, tightening to `15px` on mobile. Buttons, status pills, sentiment chips, and the probability meter use pill silhouettes. Disclosure rows and data tables use `12px` corners; the empty state uses a larger `16px` outline with a dashed border. Network nodes remain circular, with a heavier coral ring for the selected company.

## Components

### Buttons
- **Shape:** fully pill-shaped (`999px`).
- **Primary:** black with white text; hover changes to charcoal and disabled changes to a lighter gray. Streamlit supplies the control's intrinsic height and padding.
- **Secondary:** native Streamlit treatment for Demo, company-list actions, and utility controls, sharing the pill shape.
- **Focus / press:** keyboard focus uses a `2px` coral outline with a `3px` offset. Press scales to `.985`; color, border, and transform transitions last `120ms`. Reduced-motion preferences shorten transitions to near zero.

### Chips
- **Style:** compact pill with a translucent tint of its class color and matching text.
- **State:** positive, negative, and neutral use their own class colors; unscored rows use a quiet pale label. Each chip includes a readable class name.

### Cards / Containers
- **Corner Style:** `18px` on desktop and `15px` at the mobile breakpoint.
- **Background:** warm surface for research setup; charcoal for constellation, snapshot, recent articles, and trend.
- **Shadow Strategy:** none; use tonal contrast and thin borders.
- **Border:** warm gray around setup; charcoal gray around analysis panels.
- **Internal Padding:** setup uses `.8rem 1rem`; analysis uses `1rem 1.1rem`, reducing to `.75rem .8rem` on mobile.

### Inputs / Fields
- **Style:** company selection in the snapshot uses a raised charcoal fill, charcoal border, and light text. Research target, feed, and lookback controls keep Streamlit's native light-theme treatment.
- **Focus:** the shared coral keyboard outline has a `2px` stroke and `3px` offset; text fields use the coral caret.
- **Error / Disabled:** primary action disabled state uses gray; Streamlit error and warning messages retain their native semantic treatments.

### Navigation
- **Style:** the header's Demo / Research view toggle sits opposite the brand. It uses a secondary pill button and switches to the alternate view.
- **Mobile:** header content aligns to the start and stacks vertically.

### Company Constellation

Company nodes are circular and sized by unique article count; positive, negative, and near-neutral values use green, rose, and silver. A three-segment sentiment legend sits inside the network panel, with compact keys for node size and link width. A slate edge connects companies mentioned in the same article, with width increasing by shared-article count. Ticker labels sit beneath nodes, and the selected node receives a bright coral ring. Axes stay hidden because position is only a layout of shared coverage. Hover reveals company, class, index, and article count; users can pan the graph and select a node to update the other analysis panels.

### Company Snapshot

The selected-company card combines a company selector, signed index, leaning label, and targeted article count in its first signal row. A three-part average-probability meter follows, with negative/neutral/positive labels and the probability-estimate caveat. A compact footer groups total headlines, companies, feeds or sources, freshness, run state, and any unmatched count.

### Recent Article Analytics Rows

Each row gives the title and source/time on the left, with sentiment chip, signed index, and estimated top-class probability aligned on the right. Titles clamp at two lines and open the source when a safe URL is available. The list is newest first and limited to six items; its header names the signal and estimate fields.

### Sentiment Trend

The trend is a bright coral line with circular markers on transparent plot backgrounds. Its date axis and sentiment-index axis remain visible, with `−1`, `0`, and `+1` ticks and a dotted zero guide. Hover shows date, score, and article count; the plot supports zoom and reset-view controls.

### Disclosure Rows

Use native expanders for company registry management, source status, CSV input, all-article browsing, and model quality/method. The all-article table keeps sortable source, time, headline, target, sentiment, index, probability, and link information together with an export action.

## Do's and Don'ts

### Do:
- **Do** preserve the warm setup surface and charcoal analysis panels as distinct contrast roles.
- **Do** keep the Research action black and use coral for focus and chart selection/emphasis.
- **Do** pair every sentiment color with a class name and a numeric estimate.
- **Do** encode article count in node size and shared-article count in edge width.
- **Do** keep the graph positions descriptive only; explain that edges mean co-mention in shared article coverage.
- **Do** keep recent article source/time with the sentiment chip, index, and probability estimate in the same row.
- **Do** retain visible trend axes and its dotted zero reference.

### Don't:
- **Don't** use color alone to identify a sentiment class.
- **Don't** imply co-mention lines represent corporate relationships, market correlation, causation, or forecasts.
- **Don't** present model probabilities as calibrated certainty, returns, or investment advice.
- **Don't** bring the retired cool blue palette or light-card analytics treatment back into the active analysis board.
