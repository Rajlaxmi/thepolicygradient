# The Policy Gradient

A curated email digest of reinforcement learning research, designed as
HTML emails for clients like Gmail, Outlook, and Apple Mail.

## Files

- `templates/issue11_featured_orals.html` — Vol. 04, Issue 11 (May 2026)
  Six featured RL orals from ICLR 2026:
  ScaleRL, TROLL, OpTI-BFM, TD-JEPA, ExDM, T³.

- `templates/issue12_application_layer.html` — Vol. 04, Issue 12 (May 28, 2026)
  Six more RL orals, focused on the application layer:
  AgentFlow, Mean Flow Policy, FIRE, MemAgent, MedAgentGym,
  Cross-Embodiment Offline RL.

## Design notes

Both files use the same email-compatible template:

- Table-based layout (required by Outlook)
- All styles inline; the <style> block only holds resets and one
  mobile media query
- Web-safe font stack: Georgia (body), Courier New (accents)
- 600px container, mobile-stacking @ 620px
- VML/MSO conditional comments for Outlook rendering
- Hidden preheader for inbox previews
- No web fonts, no JavaScript, no external CSS, no images

## Visual language

- Cream paper (#fbf8f1) on warm gray ground (#f3efe6)
- Oxblood accent (#8a3324), saffron highlight (#e9b44c)
- Georgia masthead "The Policy Gradient" with mixed italic/roman
- Numbered paper cards (01–06) with hairline rules
- "Why it matters" pull quotes with oxblood left rule
- Ornamental ❦ ❦ ❦ section breaks
- Inverted (black) editor's note block

## Adapting to a new issue

To repurpose for a different conference or track:

1. Update the masthead row (Vol/Issue/Date)
2. Update the hero headline and standfirst paragraph
3. Replace each paper card's: category tag, title, authors, summary,
   "Why it matters" line, and OpenReview link
4. Update the "Also worth reading" list
5. Update the editor's note

The structural HTML stays put.

## Sources

All paper data sourced from OpenReview ICLR 2026 oral track:
https://openreview.net/group?id=ICLR.cc/2026/Conference#tab-accept-oral

All abstracts © respective authors, CC BY 4.0.
