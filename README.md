# den-AI

> **The critic that fixes your documents.**
> den-AI roasts your slide decks and reports without mercy — then edits them like a senior reviewer. Your design stays. Your filler doesn't.

Every office has that one colleague with brutal taste who tells you your deck is unreadable, your chart is misleading, and slide 7 should never have existed. den-AI is that colleague, as an agent. The difference: after the roast, it actually fixes the thing — **surgically, on your file**, not by regenerating some template-grey replacement. Titles become takeaways, walls of text become bullets, filler slides disappear, and you get the changelog of every cut.

```
$ denai roast q3-results.pptx

╭───────────────── den-AI verdict ─────────────────╮
│ den score: 4.2/10                                │
│                                                  │
│ “Twelve slides to say one number went up.        │
│  The number deserved better.”                    │
╰──────────────────────────────────────────────────╯

Top sins:
  ✗ Slide 3 is a wall of text wearing a title
  ✗ Vanity metrics with no baseline on slides 5-7
  ✗ Three different fonts fighting for attention
  ...

$ denai fix q3-results.pptx
✓ Rebuilt: q3-results.denai-fixed.pptx — kept your brand.
```

## What it does

- **`denai web`** — opens **den-AI studio** on localhost: drop a file in the browser, watch the den score ring fill up, read the roast, click *Fix it for me* and download the rebuilt document. Apple-grade UI, dark mode included, **IT · EN · ES** language switcher (changes both the interface and the roast language), nothing leaves your machine except the call to Claude.
- **`denai roast <file>`** — takes a `.pptx`, `.docx`, `.pdf` or `.md` and delivers a sharp, slide-by-slide (or section-by-section) critique: a **den score** out of 10, the top sins, and a concrete fix for every flaw. Output lands in your terminal, in a Markdown report, and in a **shareable scorecard** (HTML + PNG).
- **`denai fix <file>`** — **edits the original in place**: your theme, layouts and images stay exactly where they are. den-AI rewrites weak titles into takeaways, replaces walls of text with tight bullets, adds speaker notes, deletes true filler — and prints the changelog of every intervention. PDF and Markdown inputs (no design to preserve) are rebuilt as clean Word documents, **with real charts** (matplotlib) wherever the source has numbers worth seeing.
- **`denai roast --diff <file>`** — den-AI re-judges its own fix: before/after den score, delta, and a verdict on whether redemption was achieved.
- **`denai report <data.csv>`** — from raw numbers straight to a den-approved report (`--to docx|pptx`): headline number first, real insights, charts instead of tables, zero filler.

Every jab points at a real flaw and how to fix it — sharp, never gratuitous. And den-AI is bilingual: it roasts in the language of your document.

### The prime directive

**Never destroy the user's design.** den-AI fixes documents the way a great editor fixes prose: changing what's weak, touching nothing else. It judges your brand in the roast (palette, fonts, coherence — nothing is safe), but the fix operates on *your* file. The only documents it builds from scratch are the ones that have no design yet: PDFs, Markdown, and raw CSV data — those get den-AI's clean, chart-forward treatment.

## Install

```sh
# with uv (recommended)
uv tool install denai

# or with pipx / pip
pipx install denai
```

Requires Python ≥ 3.10 and the [Claude Code](https://claude.com/claude-code) CLI on your PATH (den-AI is built on the [Claude Agent SDK](https://code.claude.com/docs/en/agent-sdk/python)).

> Not on PyPI yet? Install from source: `uv tool install git+https://github.com/Dany-mc/den-AI`

## Authentication — guided, in the browser

You don't need to touch env vars. Run `denai web`: on first launch, den-AI studio opens a **Connect Claude** sheet with two one-click paths:

- **Claude subscription** — if you're logged into Claude Code on this machine (`claude` → `/login`, one time only), hit *Verify connection* and you're in. No per-token billing.
- **API key** — paste your Anthropic key in the sheet. It's stored only on your machine (`~/.denai/config.json`, `chmod 600`) and used only to call Claude.

Both paths are verified with a real one-token call before the sheet closes. Reopen anytime from the 🔑 icon in the header. Terminal purists can still just set `ANTHROPIC_API_KEY` — it always wins over the stored key, and the CLI commands (`roast`, `fix`) pick up the stored key too.

## Usage

```sh
denai web                          # den-AI studio in your browser — login included, first run is guided
denai roast deck.pptx              # the verdict, in your terminal
denai roast report.docx --no-card  # skip the HTML scorecard
denai fix deck.pptx                # the redemption (reuses the roast if present)
denai roast deck.pptx --model claude-opus-4-8   # bring a bigger brain
denai roast deck.pptx --lang es    # roast in Spanish (it / en / es)
denai roast report.pdf             # PDFs and Markdown get judged too
denai roast deck.pptx --diff       # before/after: did the fix earn its keep?
denai report sales.csv --to pptx   # raw CSV -> den-approved deck with charts
denai web --port 9000 --no-browser # studio, your way
```

Outputs, next to your file:

| File | What it is |
|---|---|
| `<name>.denai.md` | Full roast report, section by section |
| `<name>.denai.html` | Shareable scorecard (screenshot it, post it) |
| `<name>.denai.png` | The scorecard as an image — ready to post |
| `<name>.denai.json` | Machine-readable roast — feeds `denai fix` |
| `<name>.denai-fixed.pptx/docx` | The rebuilt document (PDF/MD inputs become .docx) |
| `<name>.denai-report.docx/pptx` | The report built from your CSV |

## How it works

1. **Extract** — `python-pptx` / `python-docx` / `pypdf` turn your file into structured content + distilled brand signals (dominant palette, fonts).
2. **Judge** — Claude, wearing the den-AI persona, scores every unit and the brand itself.
3. **Operate** — Claude produces a surgical edit plan (rewrite this title, replace that body, delete slide 7); den-AI applies it to a copy of your original file and hands you the changelog. For design-less inputs (PDF/MD/CSV), it builds a clean document with charts instead.

## Roadmap

- [x] Roast + rebuild for PPTX and DOCX
- [x] den-AI studio — local web UI (`denai web`)
- [x] PNG export of the scorecard
- [x] Charts in rebuilt decks (matplotlib)
- [x] `denai roast --diff` — before/after comparison
- [x] CSV/data input: from raw numbers straight to a den-approved report
- [x] PDF and Markdown input
- [ ] Themes: bring-your-own `den style`
- [ ] Batch mode: roast a whole folder, rank the survivors

## License

[MIT](LICENSE) — roast responsibly.
