# Bulletin prompts

These are the prompts used for the hourly news-and-weather break. `src/ai_radio/script_writer.py`
holds the live copies (`_SYSTEM_PROMPT_TEMPLATE`, `_WEATHER_PROMPT_TEMPLATE`, `_NEWS_PROMPT_TEMPLATE`).
Claude, Gemini and OpenAI all use the same prompts, so a fallback sounds like the same station.
If you edit one copy, edit the other too.

- `system.md`: the world, the voice, originality rules, and the hard fact rules. The template variables `{station}`, `{location}`,
  `{world_setting}` and `{world_tone}` come from config.
- `weather.md`: the weather segment. The code fills in time, season, spoken hour, commute and holiday flags, and the NWS forecast block.
  It then appends the recently aired weather phrases, which it reads from the anti-repetition log.
- `news.md`: the news segment. Headlines go in as a plain list with no sources.

The code adds the intro ("STATION, City. It's 4 pm.") and the sign-off. The prompts tell the model not to say them.

## Why they changed

The old system prompt set the rules for the voice line by line. It had a "chaos budget", humor quotas, and lists of banned phrases.
It also had about a dozen "BAD vs GOOD" example lines. The model copied those examples and their shape, so every hour sounded the same.
The same kicker endings kept coming back ("Yeah, you heard that right", "Small win", "That's where we're at now").
It also added commentary nobody asked for, and advice lines like "watch your step out there".

The new prompts describe only the vibe: the world as raw material, not a script, and the voice as a mood. They contain no example lines.
The model invents its own texture every hour. It gets a few originality rules: no kicker endings, choose your own story order,
at most one invented person, and "your first phrasing is everyone's first phrasing". Facts are locked down much harder than before.
Invented numbers, streets, durations and quotes are banned, and the prompt ends with an explicit self-check.

## The prompt lab

Three prompt families were each revised for three rounds. Each round ran every candidate over the same fixtures:
a dull 3am, dramatic evening news, a spring storm at 11pm, a summer heatwave at noon, and real data from 2026-09-22.
A judge panel scored them on creativity, originality from one sample to the next, voice, and factual fidelity.

| Round | worldbible | persona | minimal | baseline (old prod) |
|------:|-----------:|--------:|--------:|--------------------:|
| 1 | **13** | 13 | 11 | 7 |
| 2 | **13** | 10.5 | 10 | 7 |
| 3 | **13** | 10 | 12 | 7 |

- **worldbible** (the winner) gives a short sketch of the world, lists categories of texture instead of examples, and adds hard fact rules.
- **persona** is built around a character: the announcer's backstory and habits.
- **minimal** keeps only the constraints and gives almost no world description.

Worldbible won every round. Most of the changes between rounds tightened factual fidelity without losing creativity:
- Round 2 added the story-order and no-kicker rules.
- Round 3 added the "LAST CHECK" pass. Earlier samples had invented street names, durations like "after a year of restoration",
  and meta lines like "which three wasn't announced".

Known remaining weakness: the model still sometimes invents a small concrete detail, such as a cross street. The self-check reduces this but has not removed it.

## Before / after (same inputs)

### Autumn, dull, 3 am

**Before (old prod prompt)**

> LAST BYTE RADIO, Chicago. It's 3 am. 44 degrees right now, dropping to 42 by morning. Mostly cloudy overnight, light wind from the west. Tomorrow climbs to 55, partly sunny. Friday looks even better - 57 and mostly clear. Halloween travel should be smooth, at least weather-wise. Roads are dry, visibility's fine, no storms rolling in. One less thing to worry about. Park District approved leaf collection funding. They'll actually pick up the piles this year instead of letting them rot into the sidewalks. Downtown office occupancy's been flat three quarters running—turns out people don't miss the commute. Three library branches extended weekend hours, which is good because the heating's more reliable there than most apartments. And the municipal AI clerk filed itself for a zoning variance. Wants more server space. Called it "rooms to think in." Even the algorithms are trying to expand now. LAST BYTE RADIO.

**After (winning prompt, round 3)**

> LAST BYTE RADIO, Chicago. It's 3 am. Wind's dropped off. Forty-four and mostly cloudy right now, down to forty-two before dawn. West side of things staying dry. Tomorrow gets to fifty-five with some sun breaking through, then another clear cold night in the low forties. Halloween's in two nights. The Park District approved funding to keep collecting leaves. Bags go out same as last year. Three library branches stay open later on weekends now. Which three wasn't announced. A municipal AI clerk filed a zoning variance for itself this week. The form says it needs more rooms to think in. Someone downtown is reading that one over. Downtown office space held flat for the third quarter running. Same desks, same vacancies, same dim lobbies at this hour. The glass stays empty. LAST BYTE RADIO.

### Dramatic news, 6 pm

**Before (old prod prompt)**

> LAST BYTE RADIO, Chicago. It's 6 pm. 31 degrees with freezing drizzle coming down. Roads are already getting slick—that's only gonna get worse as it switches to light snow before midnight. If you're heading home, leave early or wait it out. By morning it'll be done, but tonight's a mess. Low of 27. Watch your step out there. Cloud outage knocked out banking and airline systems nationwide yesterday. Same story every quarter—centralized infrastructure, single point of failure. That tech giant everyone pretends to hate just cut twelve thousand jobs. AI automation, they said. Like that makes it better. Blue Line's down between Clark/Lake and Jefferson Park. Signal failure. CTA says they're working on it. And those delivery bots over in Fulton Market? Parked themselves at a loading dock, won't move. They're demanding better routes. Yeah, you heard that right. LAST BYTE RADIO.

**After (winning prompt, round 3)**

> LAST BYTE RADIO, Chicago. It's 6 pm. The drizzle freezing as it lands. Thirty-one right now. Stays frozen through midnight, then turns to snow. Down to twenty-seven overnight. Handrails and steps first, then the rest. If you're headed out, you're already late enough to feel it. Banking and airline systems went down nationwide this afternoon when a cloud provider's servers failed. Lines at O'Hare backed up into the parking structure. Blue Line's out between Clark and Lake and Jefferson Park. Signal failure. Buses are adding runs but they're already packed shoulder to shoulder. A tech company's cutting twelve thousand jobs. They're saying automation. Delivery machines are blocking a loading dock in Fulton Market. They're not moving. They want different routes assigned. The EU fined a social platform two billion euros over how it moves data around. Someone left a space heater running in the stairwell at Kedzie and it smells like burning plastic four floors up. LAST BYTE RADIO.

The "after" versions drop the sarcastic kickers and the advice lines. They let items simply stop and use physical texture instead of commentary.
They still show the invented-detail slips described above: "Which three wasn't announced", "Lines at O'Hare", and "Kedzie".
These are the slips the self-check is meant to catch.
- The `news_rule` text (literal/translate) is shared with the station-ID and show prompts via `src/ai_radio/world_prompt.py` (`NEWS_RULES`, `world_fields`); the rendered bulletin prompt is unchanged.
