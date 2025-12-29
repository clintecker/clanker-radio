"""Tests for AnnouncerPersonalityConfig domain configuration."""

import pytest

from ai_radio.config.announcer_personality import AnnouncerPersonalityConfig


class TestAnnouncerPersonalityConfig:
    """Tests for AnnouncerPersonalityConfig."""

    def test_default_announcer_name(self):
        """announcer_name should have default value."""
        config = AnnouncerPersonalityConfig()
        assert config.announcer_name == "DJ Coco"

    def test_announcer_name_from_env(self, monkeypatch):
        """announcer_name should load from RADIO_ANNOUNCER_NAME env var."""
        monkeypatch.setenv("RADIO_ANNOUNCER_NAME", "DJ Test")
        config = AnnouncerPersonalityConfig()
        assert config.announcer_name == "DJ Test"

    def test_default_energy_level(self):
        """energy_level should have default value."""
        config = AnnouncerPersonalityConfig()
        assert config.energy_level == 5

    def test_energy_level_from_env(self, monkeypatch):
        """energy_level should load from RADIO_ENERGY_LEVEL env var."""
        monkeypatch.setenv("RADIO_ENERGY_LEVEL", "7")
        config = AnnouncerPersonalityConfig()
        assert config.energy_level == 7

    def test_energy_level_validation_too_low(self, monkeypatch):
        """energy_level should reject values < 1."""
        monkeypatch.setenv("RADIO_ENERGY_LEVEL", "0")
        with pytest.raises(ValueError):
            AnnouncerPersonalityConfig()

    def test_energy_level_validation_too_high(self, monkeypatch):
        """energy_level should reject values > 10."""
        monkeypatch.setenv("RADIO_ENERGY_LEVEL", "11")
        with pytest.raises(ValueError):
            AnnouncerPersonalityConfig()

    def test_default_vibe_keywords(self):
        """vibe_keywords should have default value."""
        config = AnnouncerPersonalityConfig()
        assert config.vibe_keywords == "laid-back, friendly, warm, easygoing, tropical"

    def test_vibe_keywords_from_env(self, monkeypatch):
        """vibe_keywords should load from RADIO_VIBE_KEYWORDS env var."""
        monkeypatch.setenv("RADIO_VIBE_KEYWORDS", "energetic, upbeat")
        config = AnnouncerPersonalityConfig()
        assert config.vibe_keywords == "energetic, upbeat"

    def test_default_max_riffs_per_break(self):
        """max_riffs_per_break should have default value."""
        config = AnnouncerPersonalityConfig()
        assert config.max_riffs_per_break == 1

    def test_max_riffs_per_break_from_env(self, monkeypatch):
        """max_riffs_per_break should load from RADIO_MAX_RIFFS_PER_BREAK env var."""
        monkeypatch.setenv("RADIO_MAX_RIFFS_PER_BREAK", "3")
        config = AnnouncerPersonalityConfig()
        assert config.max_riffs_per_break == 3

    def test_default_max_exclamations_per_break(self):
        """max_exclamations_per_break should have default value."""
        config = AnnouncerPersonalityConfig()
        assert config.max_exclamations_per_break == 2

    def test_max_exclamations_per_break_from_env(self, monkeypatch):
        """max_exclamations_per_break should load from RADIO_MAX_EXCLAMATIONS_PER_BREAK env var."""
        monkeypatch.setenv("RADIO_MAX_EXCLAMATIONS_PER_BREAK", "4")
        config = AnnouncerPersonalityConfig()
        assert config.max_exclamations_per_break == 4

    def test_default_unhinged_percentage(self):
        """unhinged_percentage should have default value."""
        config = AnnouncerPersonalityConfig()
        assert config.unhinged_percentage == 20

    def test_unhinged_percentage_from_env(self, monkeypatch):
        """unhinged_percentage should load from RADIO_UNHINGED_PERCENTAGE env var."""
        monkeypatch.setenv("RADIO_UNHINGED_PERCENTAGE", "50")
        config = AnnouncerPersonalityConfig()
        assert config.unhinged_percentage == 50

    def test_unhinged_percentage_validation_too_low(self, monkeypatch):
        """unhinged_percentage should reject values < 0."""
        monkeypatch.setenv("RADIO_UNHINGED_PERCENTAGE", "-1")
        with pytest.raises(ValueError):
            AnnouncerPersonalityConfig()

    def test_unhinged_percentage_validation_too_high(self, monkeypatch):
        """unhinged_percentage should reject values > 100."""
        monkeypatch.setenv("RADIO_UNHINGED_PERCENTAGE", "101")
        with pytest.raises(ValueError):
            AnnouncerPersonalityConfig()

    def test_default_humor_priority(self):
        """humor_priority should have default value."""
        config = AnnouncerPersonalityConfig()
        assert config.humor_priority == "observational > analogy > wordplay > weather-roast > character-voice"

    def test_humor_priority_from_env(self, monkeypatch):
        """humor_priority should load from RADIO_HUMOR_PRIORITY env var."""
        monkeypatch.setenv("RADIO_HUMOR_PRIORITY", "wordplay > observational")
        config = AnnouncerPersonalityConfig()
        assert config.humor_priority == "wordplay > observational"

    def test_default_allowed_comedy(self):
        """allowed_comedy should have default value."""
        config = AnnouncerPersonalityConfig()
        assert config.allowed_comedy == "relatable complaints, tech metaphors (light), quick punchlines, playful hyperbole"

    def test_allowed_comedy_from_env(self, monkeypatch):
        """allowed_comedy should load from RADIO_ALLOWED_COMEDY env var."""
        monkeypatch.setenv("RADIO_ALLOWED_COMEDY", "puns, observations")
        config = AnnouncerPersonalityConfig()
        assert config.allowed_comedy == "puns, observations"

    def test_default_banned_comedy(self):
        """banned_comedy should have default value."""
        config = AnnouncerPersonalityConfig()
        assert config.banned_comedy == "meme recitation (POV/tell-me-you), dated slang, 'fellow kids' energy, extended sketches >10sec, self-congratulation"

    def test_banned_comedy_from_env(self, monkeypatch):
        """banned_comedy should load from RADIO_BANNED_COMEDY env var."""
        monkeypatch.setenv("RADIO_BANNED_COMEDY", "offensive jokes")
        config = AnnouncerPersonalityConfig()
        assert config.banned_comedy == "offensive jokes"

    def test_default_unhinged_triggers(self):
        """unhinged_triggers should have default value."""
        config = AnnouncerPersonalityConfig()
        assert config.unhinged_triggers == "hurricanes, tsunami warnings, volcanic activity, coconut shortages, extreme surf conditions, tourist invasions"

    def test_unhinged_triggers_from_env(self, monkeypatch):
        """unhinged_triggers should load from RADIO_UNHINGED_TRIGGERS env var."""
        monkeypatch.setenv("RADIO_UNHINGED_TRIGGERS", "storms, earthquakes")
        config = AnnouncerPersonalityConfig()
        assert config.unhinged_triggers == "storms, earthquakes"

    def test_default_sentence_length_target(self):
        """sentence_length_target should have default value."""
        config = AnnouncerPersonalityConfig()
        assert config.sentence_length_target == "6-14 words average, vary rhythm"

    def test_sentence_length_target_from_env(self, monkeypatch):
        """sentence_length_target should load from RADIO_SENTENCE_LENGTH_TARGET env var."""
        monkeypatch.setenv("RADIO_SENTENCE_LENGTH_TARGET", "8-12 words")
        config = AnnouncerPersonalityConfig()
        assert config.sentence_length_target == "8-12 words"

    def test_default_max_adjectives_per_sentence(self):
        """max_adjectives_per_sentence should have default value."""
        config = AnnouncerPersonalityConfig()
        assert config.max_adjectives_per_sentence == 2

    def test_max_adjectives_per_sentence_from_env(self, monkeypatch):
        """max_adjectives_per_sentence should load from RADIO_MAX_ADJECTIVES_PER_SENTENCE env var."""
        monkeypatch.setenv("RADIO_MAX_ADJECTIVES_PER_SENTENCE", "3")
        config = AnnouncerPersonalityConfig()
        assert config.max_adjectives_per_sentence == 3

    def test_default_natural_disfluency(self):
        """natural_disfluency should have default value."""
        config = AnnouncerPersonalityConfig()
        assert config.natural_disfluency == "0-1 per break (e.g., 'okay—so...', 'wait, my sensor just refreshed')"

    def test_natural_disfluency_from_env(self, monkeypatch):
        """natural_disfluency should load from RADIO_NATURAL_DISFLUENCY env var."""
        monkeypatch.setenv("RADIO_NATURAL_DISFLUENCY", "1-2 per break")
        config = AnnouncerPersonalityConfig()
        assert config.natural_disfluency == "1-2 per break"

    def test_default_banned_ai_phrases(self):
        """banned_ai_phrases should have default value."""
        config = AnnouncerPersonalityConfig()
        expected = "'as an AI', 'according to my data', 'in today's world', 'stay tuned for more', 'News:', 'In other news', 'seem excited/interested', 'back when we had', 'wasn't already on life support', 'stay warm', 'keep your head down', 'more music coming up', 'that's all for now', 'cutting through you', 'cut right through', 'cut through a', 'cutting right through', 'stabbing', 'stabs', 'stab', 'pierce', 'piercing', 'slice', 'slicing', 'secure your', 'securing your', 'secure anything', 'securing anything', 'anything loose', 'tie down', 'batten down', 'bundle up if you're heading out', 'layer up'"
        assert config.banned_ai_phrases == expected

    def test_banned_ai_phrases_from_env(self, monkeypatch):
        """banned_ai_phrases should load from RADIO_BANNED_AI_PHRASES env var."""
        monkeypatch.setenv("RADIO_BANNED_AI_PHRASES", "hello world")
        config = AnnouncerPersonalityConfig()
        assert config.banned_ai_phrases == "hello world"

    def test_default_weather_structure(self):
        """weather_structure should have default value."""
        config = AnnouncerPersonalityConfig()
        assert config.weather_structure == "Give the current conditions and forecast in 20-30 seconds. Vary your approach - sometimes lead with temperature, sometimes with conditions, sometimes with a consequence. Not every weather report needs advice or a joke. Just tell people what it's like outside in a way that feels natural to the moment."

    def test_weather_structure_from_env(self, monkeypatch):
        """weather_structure should load from RADIO_WEATHER_STRUCTURE env var."""
        monkeypatch.setenv("RADIO_WEATHER_STRUCTURE", "Quick weather update")
        config = AnnouncerPersonalityConfig()
        assert config.weather_structure == "Quick weather update"

    def test_default_weather_translation_rules(self):
        """weather_translation_rules should have default value."""
        config = AnnouncerPersonalityConfig()
        assert config.weather_translation_rules == "Keep it breezy and conversational. When relevant, mention specific impacts (beach conditions, outdoor plans, boat weather, tourist activities). But don't force it - sometimes just saying the conditions is enough. Vary structure: lead with temp, or conditions, or impact, or forecast. Mix it up."

    def test_weather_translation_rules_from_env(self, monkeypatch):
        """weather_translation_rules should load from RADIO_WEATHER_TRANSLATION_RULES env var."""
        monkeypatch.setenv("RADIO_WEATHER_TRANSLATION_RULES", "Keep it simple")
        config = AnnouncerPersonalityConfig()
        assert config.weather_translation_rules == "Keep it simple"

    def test_default_news_tone(self):
        """news_tone should have default value."""
        config = AnnouncerPersonalityConfig()
        assert config.news_tone == "Normal: laid-back, friendly, conversational. Serious mode: respectful, minimal jokes, no snark. Trigger serious mode for: deaths, disasters, violence, accidents. Keep it real and relatable."

    def test_news_tone_from_env(self, monkeypatch):
        """news_tone should load from RADIO_NEWS_TONE env var."""
        monkeypatch.setenv("RADIO_NEWS_TONE", "Always serious")
        config = AnnouncerPersonalityConfig()
        assert config.news_tone == "Always serious"

    def test_default_news_format(self):
        """news_format should have default value."""
        config = AnnouncerPersonalityConfig()
        assert config.news_format == "Cover the provided headlines (typically 3-4 stories). Keep it natural and conversational. Vary how you treat each story - some get one sentence, some get two, some get a casual observation. Mix it up naturally. Skip stories if redundant or low-value. Ethical boundaries: no joking about victims, no punching down, no conspiracy framing, no unsourced hot takes."

    def test_news_format_from_env(self, monkeypatch):
        """news_format should load from RADIO_NEWS_FORMAT env var."""
        monkeypatch.setenv("RADIO_NEWS_FORMAT", "Brief headlines only")
        config = AnnouncerPersonalityConfig()
        assert config.news_format == "Brief headlines only"

    def test_default_accent_style(self):
        """accent_style should have default value."""
        config = AnnouncerPersonalityConfig()
        assert config.accent_style == "Light transatlantic or coastal US/Canadian - subtle, globally legible. Internet-native 'streamer' sound. Mid-20s to mid-30s vibe. Crisp enunciation with subtle tech slang fluency. NOT cartoonish accents or heavy caricature"

    def test_accent_style_from_env(self, monkeypatch):
        """accent_style should load from RADIO_ACCENT_STYLE env var."""
        monkeypatch.setenv("RADIO_ACCENT_STYLE", "British accent")
        config = AnnouncerPersonalityConfig()
        assert config.accent_style == "British accent"

    def test_default_delivery_style(self):
        """delivery_style should have default value."""
        config = AnnouncerPersonalityConfig()
        assert config.delivery_style == "Medium-fast with purposeful pauses, crisp consonants, smile in voice, varied pacing with micro-pauses, occasional self-referential asides ('okay, nerd alert, but...')"

    def test_delivery_style_from_env(self, monkeypatch):
        """delivery_style should load from RADIO_DELIVERY_STYLE env var."""
        monkeypatch.setenv("RADIO_DELIVERY_STYLE", "Slow and steady")
        config = AnnouncerPersonalityConfig()
        assert config.delivery_style == "Slow and steady"

    def test_default_radio_resets(self):
        """radio_resets should have default value."""
        config = AnnouncerPersonalityConfig()
        assert config.radio_resets == "Station ID at start and end of each break (required). Time reference somewhere in the break (required for listener orientation). HOW you work these in is up to you - be natural, don't force a template."

    def test_radio_resets_from_env(self, monkeypatch):
        """radio_resets should load from RADIO_RADIO_RESETS env var."""
        monkeypatch.setenv("RADIO_RADIO_RESETS", "Station ID only")
        config = AnnouncerPersonalityConfig()
        assert config.radio_resets == "Station ID only"

    def test_default_listener_relationship(self):
        """listener_relationship should have default value."""
        config = AnnouncerPersonalityConfig()
        assert config.listener_relationship == "Talking to neighbors and friends, not a crowd. 'We're all here living the island life together' not 'performing at you'. Casual, warm, like chatting at the beach."

    def test_listener_relationship_from_env(self, monkeypatch):
        """listener_relationship should load from RADIO_LISTENER_RELATIONSHIP env var."""
        monkeypatch.setenv("RADIO_LISTENER_RELATIONSHIP", "Formal announcements")
        config = AnnouncerPersonalityConfig()
        assert config.listener_relationship == "Formal announcements"
