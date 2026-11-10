# 05 — Studio media assets & the metagame info panel

Game-agnostic reference for the BGA Studio **Media** tab (box/icon/banner/publisher/display/title)
and the **Game information** panel fields. Worked out empirically while prepping *The Reckoners*
for alpha — the per-slot upload dialogs each state their own rules, and several "info panel" fields
turn out **not** to be developer-editable. Captured here so the next game doesn't re-derive it.

## 1. Media tab — image slots

Each `+`/replace dialog states its own **dimensions + format + transparency** rules. They are NOT
uniform (some png, some jpg; some must be transparent, some must not). Confirm the dialog text per
slot before exporting.

| Slot | Dimensions | Format | Background / transparency | Notes |
|------|-----------|--------|---------------------------|-------|
| **Box** | 280×280 | **PNG** | **Transparent, NO shadow** | Must be a **3D render** of the physical box as in an online shop. If no 3D shot, use https://www.3d-pack.com/. Prefer the edition matching the adaptation art / original publisher. |
| **Icon** | 50×50 | **PNG** | Transparent optional; **no border** | Make the game recognizable in lists — a distinctive part of the cover (e.g. the title or hero). Tiny: symbols/figures read better than text. |
| **Publisher** | 280×280 | **PNG** | May be transparent | Publisher's logo. Up to 2 allowed. Displayed on the game description page. |
| **Display** | height **400–760**, width **≤ 1.5 × height** | **JPG** | (opaque) | Component/table spread shot ("as displayed"). A landscape product shot fits well. |
| **Title** | 2000×2000 | **PNG** | **Transparent**, **≥500px clear margin top & bottom** | The game's **title logo**, shown *instead of* the name text, overlaid on the box. NOT the cover — just the logo, centered in the middle band. |
| **Banner** | 1386×400 | (confirm dialog) | **Must contain NO text** | Wide hero art. Aspect is ~3.46:1, so expect a horizontal crop of taller art. |

### Image budget (pre-release checklist)
- **Each image ≤ 4 MB**, **total ≤ 15 MB**. Compress; re-encoding as **indexed palette** (vs RGB)
  helps a lot. Legitimate overage (e.g. expansions) must be **noted when requesting alpha**.
- Sanity-check locally: sum sizes of the *served* `img/` tree (exclude gitignored work folders).

### Deployed-tree hygiene
- Only **referenced** images should ship. Grep the client for image path patterns
  (`img/<dir>/<name>_${var}.jpg`, `epicImgUrl`, `char_`, etc.) and diff against the tree.
- Watch for **variant orphans**: if code loads `foo_clean.jpg`, the non-`_clean` `foo.jpg` is dead.
- **Never deploy confidential/publisher art** (`img/OfficialArt/**`, TTS placeholders, PDFs,
  extraction scratch). Verify over SFTP: `ls /<game>/img` should show only the runtime dirs.
- A path that appears only in a **code comment** is not a runtime dependency (e.g. symbols baked
  into JS as inline SVG, with the source PDFs/extracts kept local-only).

## 2. Tooling — generating the slots with Pillow (PIL)

All slots were produced from official art with `PIL` (+ `numpy`). Reusable recipes:

- **Cover-crop to fill** `(w,h)`: scale by `max(w/iw, h/ih)`, center-crop the overflow.
- **Fit / letterbox**: scale by `min(...)`, paste centered on a background (transparent, or a
  blurred+darkened copy of the same art for a "hero" fill).
- **Banner (no text)**: crop a horizontal band from higher-res art, avoiding baked-in lettering;
  or center the full cutout with a blurred side-fill. A **middle band** usually frames the subject
  better than a top crop.
- **Key a solid background → transparent** (e.g. logo on black, box photo on white):
  - On black: `alpha = clip((maxchannel-lo)/(hi-lo))**γ` — black→0, bright→1.
  - On white with a soft shadow: **flood-fill from the corners** with a unique key color and a
    generous threshold (grabs white + most of the shadow, stops at the object's silhouette), then
    `alpha = 0` where keyed; feather with a ~1px blur; trim to the alpha bbox. Requirement is
    "no shadow", so tune the threshold to eat the gradient.
  - Mask stray connected bits (e.g. a board edge in the crop) with a small corner triangle —
    keep it tight so you don't clip the artwork.
- **Metallic title text** (fallback when no logo asset): render heavy font (Arial Black) to a mask,
  paste a vertical silver **gradient** through it, add a dark stroke; two-part lockup (small "THE"
  over big word) reads bigger than one wide line.
- Supersample 2× and downscale (LANCZOS) for smooth polygon/edge anti-aliasing.
- **Format gotcha**: export per the slot's dialog. When a slot demands PNG, don't ship JPG (the
  uploader rejects it); when it demands JPG, convert.

## 3. Game information panel — who controls what

Half of the "Game information" fields are **NOT** editable via `gameinfos.jsonc` or the Control
Panel — they're BGA-staff-side or community-driven. Don't chase them in files.

| Field | Source / who controls it |
|-------|--------------------------|
| **display_name / display_name_en** | The **project's registered (lowercase) name** — staff-only. NOT `game_name` (confirmed: `heartsla` ships `game_name="My Great Game"` yet displays its project name). `game_name` is used for translation base / page title only. To change casing/name → **request from BGA staff**; usually normalized at publication. **The developer CAN change the shown name** in the translation center: game module, English → English, the string with context "Game name" (`<project>_displayed`); "Request a change" there is auto-validated for the dev (Reckoners, 2026-10-28, per Studio's advice). A project *rename* is refused once the game is deployed. |
| **Developed by** | BGA-managed; defaults to **"Board Game Arena"** for in-dev games. Attributed to the **Studio dev account** at review/publication. To credit your main play account, ask staff to **link Studio account → main account (id)**. |
| **Designer / Artist / Editor / Year** | Pulled from **BGG** via `bgg_id` (or set explicitly with `designer`/`artist` in gameinfos). |
| **Number of players** | `gameinfos.jsonc` → `players` array. |
| **Game duration** | `estimated_duration` is **launch-only**; once games are played, BGA shows the **auto-computed average**. Can't force it afterward. |
| **Complexity / Strategy / Luck / Interaction** | **Community player votes.** Fill in as players rate. Not developer-editable. |
| **Available since / Release (`999999-9999` = unreleased)** | BGA lifecycle, staff-side. |

`gameinfos.jsonc` changes require **Control Panel → "Reload game informations"** + a hard refresh
to appear. It's JSONC (comments allowed) — validate it parses (strip comments, `json.loads`);
a silent parse error makes the reload a no-op.

## 4. Adjacent Studio fields

- **`game_interface_width.min`** (gameinfos): default **740** (= max; a 1024px screen). Lower →
  BGA renders **natively narrower** on mobile (larger/sharper) instead of scaling the 740 canvas.
  But `min` is a **promise the layout works at that width** — only lower it to a width you've
  verified (checklist tests mobile). 320 is the phone floor; 480–600 is a realistic first target
  for a dense board.
- **`zombieModeLevel`** (Studio field, per the *Zombie Mode* wiki): **0** Passing (just advance),
  **1** Random valid action, **2** Greedy (best immediate), **3** Smart (plan/remember). Set it to
  what you **actually implemented** — a "finish/skip" handler in every active state is **level 0**.
  Every `ACTIVE_PLAYER`/`MULTIPLE_ACTIVE_PLAYER` state MUST have a `zombie()` handler or the table
  can hang. For **co-op**, level 0 (a quitter contributes nothing) is honest and harmless; the
  "aim for 1–2" advice targets competitive games.

## 5. "How to play" / help panel

The in-game **help / "How to play"** text is authored on the **BGA wiki page `Gamehelp<gamename>`**
(the client links to edit it, cf. Santorini's `Gamehelpsantorini`), **not** a repo file — an empty
page = empty panel. Draft the content (goal, round flow, symbol legend, win/lose) and paste it there.
In-game element help is separate: tooltips via `addTooltip` / a custom `data-tip` system.
