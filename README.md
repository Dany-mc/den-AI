# den-AI

> **The critic that fixes your documents.**
> den-AI roasts your slide decks and reports without mercy — then rebuilds them better.

Every office has that one colleague with brutal taste who tells you your deck is unreadable, your chart is misleading, and slide 7 should never have existed. den-AI is that colleague, as a CLI agent. The difference: after the roast, it actually fixes the thing.

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
- **`denai roast <file>`** — takes a `.pptx` or `.docx` and delivers a sharp, slide-by-slide (or section-by-section) critique: a **den score** out of 10, the top sins, and a concrete fix for every flaw. Output lands in your terminal, in a Markdown report, and in a **shareable HTML scorecard**.
- **`denai fix <file>`** — rebuilds the document: cuts filler, merges redundant slides, turns titles into takeaways and walls of text into tight bullets.

Every jab points at a real flaw and how to fix it — sharp, never gratuitous. And den-AI is bilingual: it roasts in the language of your document.

### The brand rule

den-AI extracts your document's brand signals (dominant colors, fonts) and **respects them in the rebuild** — *if* they deserve it. If your palette is part of the problem, den-AI says so in the roast and rebuilds in its own signature **den style** instead. You get judged twice: content and identity.

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
denai web --port 9000 --no-browser # studio, your way
```

Outputs, next to your file:

| File | What it is |
|---|---|
| `<name>.denai.md` | Full roast report, section by section |
| `<name>.denai.html` | Shareable scorecard (screenshot it, post it) |
| `<name>.denai.json` | Machine-readable roast — feeds `denai fix` |
| `<name>.denai-fixed.pptx/docx` | The rebuilt document |

## How it works

1. **Extract** — `python-pptx` / `python-docx` turn your file into structured content + distilled brand signals (dominant palette, fonts).
2. **Judge** — Claude, wearing the den-AI persona, scores every unit and the brand itself.
3. **Rebuild** — the fix spec (tight titles, bullets, narrative order) is rendered back to a real `.pptx`/`.docx`, in your brand or in den style.

## Roadmap

- [x] Roast + rebuild for PPTX and DOCX
- [x] den-AI studio — local web UI (`denai web`)
- [ ] PNG export of the scorecard
- [ ] Charts in rebuilt decks (matplotlib)
- [ ] `denai roast --diff` — before/after comparison
- [ ] CSV/data input: from raw numbers straight to a den-approved report

## License

[MIT](LICENSE) — roast responsibly.
