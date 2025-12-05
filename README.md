# MCP HTML Course – Facebook‑style redesign

## Overview
This repository contains a simple HTML/CSS course about the **Model Context Protocol (MCP)**.  The UI has been updated to follow a **Facebook‑inspired design system**:

- Primary colour is Facebook blue (`#1877F2`).
- Sticky navigation bar with blue links and hover/active states.
- Content cards with rounded corners, subtle shadow, and a maximum width of 900 px.
- Dark‑mode support via a `.dark-mode` class on the `<body>` element.
- System UI font stack, consistent spacing (`1rem` base unit), and reusable CSS variables.

## Key Facebook UI elements replicated
| Element | CSS class / variable | Description |
|---------|---------------------|-------------|
| Header | `header` | Fixed‑height container for the site title. |
| Navigation bar | `nav` (and `nav a`) | Sticky at the top, semi‑transparent background, blue links, hover/active blue background, rounded corners. |
| Content cards | `.content-card` | White (or dark) background, rounded 8 px, subtle shadow, centred, max‑width 900 px. |
| Buttons | `.btn` (add to any `<button>` or `<a>`) | Blue background, white text, rounded corners, smooth hover transition. |
| Forms / inputs | `input`, `textarea` | Light border, focus outline uses the primary colour. |
| Dark mode | Add `dark-mode` class to `<body>` | Switches all CSS variables to dark equivalents (background `#1A202C`, primary `#63B3ED`, etc.). |
| Misc components | `blockquote`, `pre`, `code`, `figure` | Styled with left border, dark code background, SVG border, responsive sizing. |

## How to test locally
1. **Open the site** – on Windows run `start mcp-html-course\index.html` or double‑click the file in Explorer.
2. **Navigate** – click each navigation link; all pages should display the same header/nav styling.
3. **Responsive check** – resize the browser to mobile widths; the navigation wraps and cards stay centred.
4. **Dark‑mode toggle** – if the theme switch is present, click it and verify colours change to the dark palette.
5. **Component verification** – ensure headings, buttons, code blocks, blockquotes, and SVG figures render with the styles described above.
6. **Cross‑browser sanity** (optional) – open the page in Chrome, Edge, and Firefox.

If any element looks out of place, edit `mcp-html-course/styles.css`, save, and refresh the page.

## What was changed
- Updated `styles.css` primary colour to Facebook blue (`#1877F2`).
- Replaced the large inline `<style>` block in `index.html` with a `<link rel="stylesheet" href="styles.css">`.
- Added a comprehensive design mock‑up / style guide (this README).
- Created a Todo list to track the redesign process (now all items are completed).

---
*Prepared by Technica Engineering – UI/UX team*