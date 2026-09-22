# Station ID prompts

Live copies: `_STATION_ID_ROLE`, `_STATION_ID_TEMPLATE`, `_STATION_ID_USER_TEMPLATE` and `_STATION_ID_SHAPES`
in `src/ai_radio/script_writer.py` (`build_station_id_prompts`, `generate_station_id`). If you edit one copy, edit the other.

- `system.md`: the shared world/voice preamble (`../shared_preamble.md`) plus the station-ID rules.
- `user.md`: the per-ID request. At the top of the hour (`minute=0`) the ID gives the time; at :15/:30/:45 it doesn't,
  so the audio file can be reused at any quarter hour. One "shape" is drawn at random per ID so a day of IDs
  doesn't settle into one pattern.

Same standard as the bulletin: the world (station, location, setting, tone, framing) comes only from config and is
never spoken; plain spoken register; no slogans, wordplay, imagery, teasers or sign-offs; an occasional flat fact
native to the world. Output is spoken words only, 8 to 25 words. Samples: `../samples/`.
