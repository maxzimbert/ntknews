# Handoff: Expertise

The design canvas for Expertise as a pillar, 2026-10-21. The live, pannable version is the
"NTK Expertise" artifact on claude.ai (private to the editor until shared); these files are
the same artboards, checked in so they survive the artifact and can be diffed.

Read `docs/expertise.md` first. It holds the pitch, what prod does today, what is mocked
only, and the one decision the editor has not made (status legibility, boards A/B/C).

## About the files

`*.dc.html` are **design references built in HTML** (Claude's Design Component format):
intended layout, type, colour, copy and interaction, not production code to copy in. Recreate
in `digest/index.html` with the app's existing Newsreader/Overpass loading and CSS variables.
`canvas.json` is the layout of the boards on the canvas and is not needed to read them.

## Boards

| File | What it shows | Status |
|---|---|---|
| `Main.dc.html` | The pitch: three systems, one arc, what counts. | Pitch material |
| `Tiers.dc.html` | The seven-rung beat scale with meaning, behaviour pattern, and who hears it. Amber marks what T-0100 added. | Matches prod |
| `OptionA.dc.html` | `/me` status, legible not numeric: rail plus behaviour marks. | **Shipped in prod** |
| `OptionB.dc.html` | `/me` status, Spelling Bee style: counts toward the next rung on the card. | Option, not built |
| `OptionC.dc.html` | `/me` status, quiet: status word and the record only. | Option, not built |
| `FlowWeekOne.dc.html` | Day 1 orientation card, day 2 return line, day 5 Following It toast. | Matches prod |
| `FlowByway.dc.html` | Backstory tab, row, object, and the toast on the way back. | Matches prod |
| `FlowWitness.dc.html` | Share sheet to Carrying It; the Witness graduation; the mark on `/me`. | Graduation and Triforce are mock |
| `Me.dc.html` | The full `/me` page for a two-month reader, with the Triforce slot. | Prod minus the Triforce |
| `Triforce.dc.html` | Curiosity, Persistence, Assuredness: earned in sequence after the first Witness. Thresholds are a proposal. | Mock only |
| `Inspect.dc.html` | The founder's inspect bar and the four fixture readers. | Matches prod (`/me?inspect=month2`) |
| `Moments.dc.html` | The "Every line" sheet: all copy the system can say, firsts and marks included (T-0101). | Matches prod |

## Design system this follows

The app's own, `docs/design-system.md`: Newsreader for anything written, Overpass for chrome;
dark ground `#261F23` with `/me` on `#1E181B`; accents blue `#0798F2`, amber `#F2AE2E`, terra
`#DC6550`, teal `#01B2A7`; radii 3px and 999px only. Rung colours are `BEATS_SCALE` in
`digest/index.html`. Flow boards sit on cream only because they are documents about the
app, not screens of it.

## Rules the boards obey, and the build must

- No points, no daily reset, no streak, no count of missed days (`docs/decisions.md`).
- Status is never shown on a story card. Moments appear between stories or on close.
- Copy describes behaviour that already happened. It never issues an instruction. Option B
  is the one board that breaks this, and says so on its face.
- The Witness graduation is the only moment allowed to hold the screen.
