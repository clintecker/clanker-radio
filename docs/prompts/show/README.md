# Daily show prompts

Live copies are in `src/ai_radio/show_generator.py` (`_RESEARCH_PROMPTS`, `_TOPIC_RULES`, `_SHOW_ROLE`,
`_SHOW_FORMAT_RULES`, `_INTERVIEW_TEMPLATE`, `_DISCUSSION_TEMPLATE`, `_FIELD_REPORT_TEMPLATE`). All of them open with
the shared world/voice preamble in `../shared_preamble.md` (`src/ai_radio/world_prompt.py`), the same world the
bulletin and station IDs use. If you edit one copy, edit the other.

Pipeline: `research_topics` -> `generate_{interview,discussion,field_report}_script` -> TTS.

- `research_literal.md` / `research_translate.md`: chosen by `config.world.world_news_mode`, like the bulletin.
  Both run with Google Search grounding. *literal* returns real, current developments, kept exactly true;
  *translate* retells them as this world's own equivalents and never names the real world.
- `topic_rules.md`: how the script treats the topics in each mode. In translate mode the program name and persona
  descriptions (written in real-world terms in `show_schedules`) are rendered in-world on air; speaker tags stay exact.
- `interview.md`, `discussion.md`, `field_report.md`: creative direction per format.
- `format_rules.md`: the output contract, which the audio pipeline parses and must not change: one turn per line
  starting `[speaker: Name]`, optional bracketed delivery cues, about 1,200 words (discussion also under 7,500 bytes),
  spoken words only. It ends with a self-check pass, like the bulletin.

The structured (JSON) field-report pipeline's prompt lives in `scripts/test_cold_open.py`
(`generate_field_report_json`). It uses the same preamble and keeps every `FieldReportScript` field, per-field word
budget and the interference flags on segments 0, 3 and 6. The renderer's fallback interference lines
(`src/ai_radio/script_renderer.py`) no longer assume a particular world.

Samples: `../samples/`.
