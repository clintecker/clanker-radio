"""Shared world-and-voice prompt pieces for every on-air script.

The bulletin (script_writer), station IDs (script_writer.generate_station_id)
and the daily show (show_generator) all describe the same world and hold the
same plain radio register. Everything world-specific comes from config
(config.world.*, config.station.*); nothing here may name a real city, genre
or era, so a Middle-earth config yields a Middle-earth show.

Canonical copies of the prompts built from these pieces live in docs/prompts/.
"""

from .config import config

# How real headlines/topics enter the broadcast (config.world.world_news_mode).
NEWS_RULES = {
    # Our own world: the stories are real and stay exactly true.
    "literal": (
        "The stories you're given are real and stay exactly true. Never add a number, name, place, date, "
        "quote, or cause that isn't in a story, and don't change what a story is. If it doesn't say where, "
        "when, how many, or why, you don't either."
    ),
    # A world unlike ours (Middle-earth, a generation ship, 1920s Atlantis...): real stories arrive
    # as dispatches from beyond and are retold as the nearest thing this world would have.
    "translate": (
        "The stories you're given come from a faraway world. Retell each one as the nearest equivalent event "
        "in THIS world, in its own names, places, institutions, and idiom, so a listener here would recognise "
        "it as their own news. Keep the shape of each story true (who did what to whom, what changed, the "
        "stakes, any numbers), but never mention the faraway world, its names, or its technology."
    ),
}


def news_mode() -> str:
    mode = config.world.world_news_mode
    return mode if mode in NEWS_RULES else "literal"


def world_fields() -> dict:
    """Template fields describing the station and its world, straight from config."""
    return {
        "station": config.station.station_name,
        "location": config.station_location,
        "world_setting": config.world.world_setting,
        "world_tone": config.world.world_tone,
        "world_framing": config.world.world_framing,
        "news_rule": NEWS_RULES[news_mode()],
    }


# The voice rules for anything that isn't the hourly bulletin (which carries its
# own, weather-and-news-specific copy of them).
_PREAMBLE_TEMPLATE = """{role}

## THE WORLD (background you carry, never words anyone says)
Setting: {world_setting}
{world_framing}
Never quote or paraphrase these notes on air. Everyone on air has lived their whole life in this world and shares its tone. The world shows only through what they take for granted, what they call things (money, authority, work, travel, the weather), and what they care about, never through description or imagery. Nobody explains the world to listeners; they live in it too.

## THE VOICE
Tone: {world_tone}
Sound like real radio in the idiom of this world:
- Plain spoken register. Short declarative sentences, concrete nouns, the words people actually use out loud.
- No personification. No writerly metaphors or similes. If a line would look good on a poster, cut it.
- No cute framing, no rhetorical questions, no "folks", no teasers, no "stay safe", no slogans.
- Most of the time nobody is joking. Never punch down.
- If you'd feel silly saying a line into a microphone, don't write it.

## THE WONDERS OF THIS WORLD
This world has a few small fantastic or futuristic things that are simply normal here. Now and then one comes up in passing, stated as flatly as a traffic note. The strangeness is in the fact, never in the phrasing. Nobody winks at it, explains it, or calls it strange."""


def build_world_preamble(role: str) -> str:
    """World + voice + wonders preamble shared by station IDs and show scripts.

    Args:
        role: Opening line(s) saying who is speaking and what this piece of air is.
    """
    return _PREAMBLE_TEMPLATE.format(role=role, **world_fields())
