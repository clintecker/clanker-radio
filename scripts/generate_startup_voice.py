#!/usr/bin/env python3
"""Generate startup jingle voice-over for the radio station.

Creates a short system-style announcement for stream startup.
User will overlay this on music bed.
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from ai_radio.voice_synth import GeminiVoiceSynthesizer
from ai_radio.config import config


def main():
    """Generate startup voice sample."""

    # Startup message (system voice, not DJ voice)
    startup_text = f"""{config.station_name.upper()} IS BOOTING UP
AWAITING SYSOP COMMANDS..."""

    # Output path (use config)
    output_dir = config.assets_path
    output_file = output_dir / "startup_voice.mp3"

    # Use local path for testing
    if not output_dir.exists():
        output_dir = Path(__file__).parent.parent / "assets"
        output_dir.mkdir(exist_ok=True)
        output_file = output_dir / "startup_voice.mp3"

    print(f"Generating startup voice: {startup_text}")
    print(f"Output: {output_file}")

    # Generate with Gemini TTS
    synthesizer = GeminiVoiceSynthesizer()

    # Override the director prompt for system-style voice
    # Monkey-patch the synthesize method to use simpler prompt
    original_synthesize = synthesizer.synthesize

    def system_voice_synthesize(script_text, output_path):
        """Generate with system-style voice (no DJ character)."""
        # Simple, direct prompt for robotic system voice
        system_prompt = f"""Generate this as a clear, robotic system announcement voice.
Style: Computer system voice, neutral, mechanical but understandable.
Pacing: Moderate speed with clear pauses between lines.

{script_text}"""

        try:
            from google import genai
            from google.genai import types

            response = synthesizer.client.models.generate_content(
                model=synthesizer.model_name,
                contents=system_prompt,
                config=types.GenerateContentConfig(
                    response_modalities=["AUDIO"],
                    speech_config=types.SpeechConfig(
                        voice_config=types.VoiceConfig(
                            prebuilt_voice_config=types.PrebuiltVoiceConfig(
                                voice_name=synthesizer.voice
                            )
                        )
                    )
                )
            )

            # Extract audio data
            audio_data = response.candidates[0].content.parts[0].inline_data.data

            # Write to file
            output_path.parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, 'wb') as f:
                f.write(audio_data)

            print(f"✓ Voice generated: {output_path}")
            return True

        except Exception as e:
            print(f"✗ Generation failed: {e}")
            return False

    # Generate the voice
    success = system_voice_synthesize(startup_text, output_file)

    if success:
        print(f"\n✓ Startup voice ready!")
        print(f"  Location: {output_file}")
        print(f"\nNext steps:")
        print(f"  1. Overlay this on your music bed")
        print(f"  2. Export as {config.startup_path} (8-10 seconds total)")
        print(f"  3. We'll update radio.liq to use sequence() operator")
        return 0
    else:
        print("\n✗ Failed to generate voice")
        return 1


if __name__ == "__main__":
    sys.exit(main())
