---
name: sketchwright
description: Turn a plain-English description into a clean, labeled technical illustration. Use when someone asks for a diagram, schematic, flowchart or technical illustration.
license: MIT
metadata:
  source: https://github.com/inkline/sketchwright
  attribution: "Ported from inkline/sketchwright by @inkline (MIT)."
---

# Sketchwright

Turn a plain-English description into a clean, labeled technical illustration.

## When to use
- The user asks for a diagram, flowchart, schematic, cutaway or other technical illustration.
- The user gives a list of steps or components and wants them drawn.

## How to work
1. Restate what will be drawn in one line and list the components.
2. Write the illustration as SVG. Label every component; keep text at 12px or larger.
3. For more than 30 nodes, use the auto-layout script (`scripts/layout.py`) instead of placing nodes by hand.
4. Save files only to the outputs folder. Never write anywhere else.
5. Offer PNG export and a dark-mode version as follow-ups.

## Limits
- No copyrighted characters or logos; offer a generic stand-in instead.
- If the description is empty, ask what to draw before drawing anything.

## Attribution
Ported from inkline/sketchwright by @inkline (MIT).
