# Next steps after the Backstory bones shipped, 2026-10-01

State: the Backstory bones are on ntknews.org (checked 2026-10-01): the 4A tab, in-app row and object pages with permalinks, static twins at `/backstory/<id>/` and `/backstory/<id>/objects/<n>/`, stakes paragraphs on all 14 held rows, and digest-to-Backstory links both ways. What's thin is content, not structure. This file is a working list; `docs/tickets/` is the source of truth and `bash scripts/rot.sh` says what is real.

## A. Content (the real remaining work)

| Ticket | What | Who |
|---|---|---|
| T-0062 | Beginnings load from the matrix (`instances[]`); "In the digest" carries prior stories. Needs the matrix content below, a change to `pick()` (it takes only the two earliest pre-1981 and two latest objects per row), and a `test: true` tag plus purge for past stories before launch. | Claude builds, after content exists |
| T-0060 | Add women and minority voices to the matrix (Addams, Du Bois, Booker T. Washington, Julia Dent Grant's Missouri case, King, Malcolm X, 1940s civil rights figures). Every object needs a real lookup. | Editor approves list; Claude researches |
| T-0061 | Kruse and Zelizer, *Fault Lines*, and named critics (left, right, Keynesian). The study guide is committed under `editorial/research/`, but it names no real critic. | Editor approves; Claude finds named critics |
| T-0048 | Object page content: two context paragraphs, "where it stands now", outbound source link. Mechanism undecided; I recommend new matrix columns, drafted with real search, reviewed by the editor, piloted on The Media's 4 objects. | Editor decides mechanism; Claude drafts |
| T-0045 | One verified pull-quote per object (feeds the 4D pull-quote and the placard). Same mechanism as T-0048. | Same |
| T-0047 | `power` indicator is still unverified. Needs one citable current figure, or a changed framing. | Editor decides; Claude looks up |

Suggested order: T-0048/T-0045 pilot on one row, then T-0060 and T-0061 candidate lists, then T-0062 build.

## B. Backstory loose ends

- **Stakes paragraphs are drafts.** Written 2026-10-01 for all 14 held rows, no second reader. Edit in `editorial/backstory-rows.json`. Editor.
- **T-0003** narratives are all empty. The long-form essay is a separate feature ("Rhymes") and explicitly out of scope; that ticket likely needs retitling or discarding. Editor decision.
- **T-0011** "cards are indistinguishable when two stories share a row". The 4A tab now shows one row per story, so this may be obsolete. Run its check and close or discard.
- **T-0012** seven fire rows carry no sub-genres, so the classifier can't reach them. Fire rows' 4C pages show only elapsed time. Small, bounded.
- **T-0032** manual check: open a story, open Backstory, confirm it lands on the paired row. Editor, two minutes on the live site.
- **Not built from 4A:** the per-device "Another beginning" rotation (needs multi-entry beginnings from T-0062).
- **Dead code:** the old dark Backstory modal (`openBsrDetail`, `bsrDetailHtml`, `bsrEpisodesHtml`) is unreachable since T-0057. Remove once T-0062 settles what `instances[]` means. Claude.
- **Two stories on one row** (Media and America Abroad today) show twice in the panel. By design; revisit if it reads badly.
- **4C/4D markup lives twice** (`digest/index.html` JS and `editorial/build_backstory_pages.py`). Keep them in step until one is generated from the other.

## C. Digest, Pulse and pipeline (not touched this week)

- **Promote READY tickets** (checks pass, nobody confirmed): T-0008, T-0016, T-0022, T-0040, T-0051. Editor glances, then Claude marks VERIFIED.
- **Editorial gut-checks:** T-0041 (VOICE_REF warmth clause on real Jefferson output), T-0040 (scoop import used once for real).
- **T-0002** Pulse reads two-day-stale data when served from Netlify. Known; Pulse's real home is the GitHub Pages origin.
- **T-0005** Haiku model string differs between stages. Small chore.
- **T-0014** show the classifier's proposed row in Pulse before publish; **Pulse tagging (T-0010) is untested** by the editor's account.
- **T-0016, T-0021, T-0027** Expertise and reading-record placeholders. Not urgent; product decisions first.
- **T-0009** the strategy corpus lives in files no agent can open. The macOS permission block on Downloads is the same class of problem.

## D. Repo and ops

- **Netlify credits ran out**, which silently blocked every production deploy for a stretch. Worth a calendar reminder or a low-credit alert. Editor.
- **Open PRs not from this work:** #1 (Cloudflare CMS spec), #36 (CI concurrency and timeout on the rot check), #47 (stage.sh tidy, overlaps the merged #55 and probably needs closing or a rebase). Editor decides.
- **Staging does not refresh itself.** After any merge, `bash scripts/stage.sh`. If `staging` needs rebuilding, rebuild from `main` and re-merge only the PRs still being tried.
- **`design_handoff_backstory/` is untracked**, and so are four `NTK_*.docx` files in the repo root. Decide whether the handoff should be committed (the tickets cite it) and where the docx files belong. Editor.
- **Branches kept** after merge: `T-0054`, `T-0056` to `T-0060`. Delete when comfortable.
- **Before a real launch:** purge the `test: true` past stories (T-0062), and re-run `bash scripts/rot.sh`.

## E. One open product question

Row pages open as an in-app overlay over the SPA and push their permalink (verified on ntknews.org: same document, no reload). They look identical to the static pages by design, and the overlay hides the tab bar and header. If the expectation is that the app's own chrome stays visible, that is a small change. Editor to say which.
