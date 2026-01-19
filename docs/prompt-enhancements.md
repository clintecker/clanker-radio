# Script Generation Prompt Enhancements

Based on analysis of NPR interview transcripts and real conversation patterns.

## ACTIVE LISTENING (Interviewer)

The interviewer is NOT a passive question-asker. They are actively engaged:

### Affirmations
- Use throughout: "Yeah", "Mm-hmm", "Right", "Absolutely"
- Validates points before moving on
- Shows they're tracking the conversation

### Reflection & Bridging
- Reflect back what was said: "So what you're saying is..."
- Bridge topics: "Yeah. Now, OK, that brings me to..."
- Acknowledge emotion: "That must have been rough"
- Add context: "I heard about that raid, but I didn't know you were there"

### Examples:
❌ **Bad (too passive):**
```
Q: What happened at the raid?
A: [long answer about raid]
Q: What about the water supply?
```

✅ **Good (active listening):**
```
Q: What happened at the raid?
A: [long answer about raid]
Q: Damn. So you lost people there... [pause] That's gotta be weighing on you. How are you dealing with that while still trying to keep the water supply running?
```

## LAYERED QUESTIONING

Questions should flow organically from answers, not feel like a pre-written list.

### Start Broad → Narrow
1. "What's the situation in Pilsen?"
2. [They mention water issues]
3. "You mentioned water - what happened with the pump?"
4. [They mention specific attack]
5. "Who was behind that? CorpSec or local?"

### Follow-Up Patterns
- **Clarifying**: "Wait, you said Maria was there? What was she doing?"
- **Probing**: "Why did you make that call? What were you thinking?"
- **Connecting**: "Is that related to what you mentioned about Bridgeport?"
- **Reflecting**: "So you're saying it's not just about the resources, it's about trust?"

## PACING VARIATION

Not every question/answer should have the same weight.

### Heavy Moments (Slow Down)
- Deaths, losses, hard decisions
- Let silence breathe
- Interviewer shows emotion: "Shit, I'm sorry"
- Don't rush to next topic

### Light Moments (Speed Up)
- Small victories, funny mishaps
- Both can laugh
- Quick back-and-forth
- "Wait, you did WHAT?" [laughing]

### Example Rhythm:
```
Heavy: Loss of Maria (slow, emotional)
  ↓
Light: The drone they disabled with a bucket (quick laugh)
  ↓
Medium: Planning next supply run (practical)
  ↓
Heavy: The risk of getting caught (tension)
```

## CONVERSATIONAL REPAIRS

Real people clarify, backtrack, and correct themselves.

### Patterns to Include:
- "I mean..."
- "Wait, no, let me say that better..."
- "You know what I'm trying to say?"
- "Actually, that's not quite right. What really happened was..."
- "Sorry, I'm not explaining this well. Let me try again."

### In Questions:
- "How do you... I mean, what's your strategy for..."
- "The thing I'm trying to understand is..."

### In Answers:
- "We lost three people. No, wait, four. I forgot about Javier."
- "It was Tuesday. Or Wednesday? No, Tuesday, because that's when..."

## THINKING TOGETHER

The interviewer should process aloud, not just ask questions.

### Add Observations:
- "That makes sense, because..."
- "I'm wondering if..."
- "What strikes me about that is..."
- "I hadn't thought about it that way"

### Share Connections:
- "I was talking to someone from Bridgeport last week, and they said something similar..."
- "This reminds me of what happened in Humboldt Park..."

### Mutual Problem-Solving:
```
Q: How are you protecting the mesh network from CorpSec?
A: We're using frequency hopping...
Q: Okay, but doesn't that require... wait, how do you synchronize the nodes without a master clock? That seems like it would expose you.
A: Good question. So what we do is...
```

## HUMOR & LIGHTNESS

Even in dire situations, people laugh. It builds trust and breaks tension.

### Types of Humor:
- **Gallows humor**: "Yeah, getting shot at really motivates you to run faster"
- **Absurdity**: "So there I am, hiding in a dumpster, and I realize I forgot my radio"
- **Irony**: "CorpSec calls us terrorists. We're literally bringing people food and water."
- **Self-deprecating**: "I'm not exactly a tech genius. I still can't program my burner phone."

### When to Use:
- After heavy moments (relief)
- During tactical discussions (humanity)
- When describing close calls (coping mechanism)

## EMOTIONAL VULNERABILITY

Don't just state facts. Show how they FEEL about it.

### In Answers:
- "Honestly? I'm scared. Every time I leave the safe house, I wonder if I'm coming back."
- "I keep thinking about Maria. Like, what if I'd been faster?"
- "Sometimes I just want to quit. But then I remember why we're doing this."

### In Questions:
- "How do YOU deal with that? I mean, personally?"
- "Are you okay? Really?"
- "That must keep you up at night."

## SPECIFIC ENHANCEMENTS FOR FIELD REPORT

Add these instructions to the prompt:

```
INTERVIEWER BEHAVIOR:
- Affirm answers: "Yeah", "Mm-hmm", "Right"
- Reflect back: "So what you're saying is..."
- Add observations: "That makes sense because..."
- Show emotion: "Damn, I'm sorry", [laughing], "Wait, seriously?"
- Bridge topics: "Yeah. Now, that brings me to..."
- Share connections: "I heard something similar from..."

QUESTION PATTERNS:
- Start broad: "What's the situation?"
- Narrow from answers: "You mentioned X - tell me more about that"
- Probe: "Why did you make that call?"
- Clarify: "Wait, who was there?"
- Connect: "Is that related to...?"

PACING:
- Vary weight: Heavy (deaths) → Light (small victory) → Medium (tactics)
- After heavy moments, take a breath
- Quick back-and-forth during lighter moments
- Don't rush past emotion

CONVERSATIONAL TEXTURE:
- Include repairs: "I mean...", "Wait, let me say that better..."
- Add humor: Gallows humor, absurdity, self-deprecating
- Show vulnerability: Fears, doubts, grief
- Let them interrupt each other occasionally (mark with [interrupting])

INTERVIEWER ENGAGEMENT:
- Process aloud: "I'm wondering if..."
- Add context they know: "I heard the raid was bad, but..."
- Think together: "Wait, how does that work? That seems like it would..."
- Don't just ask questions - participate in the conversation
```

## EXAMPLE COMPARISON

### CURRENT APPROACH (Too Formal):
```
Q: What's the situation with the water supply in Pilsen?
A: CorpSec cut off access. We're running night convoys through the tunnels.
Q: How are you protecting your patrol routes?
A: We rotate them daily and use mesh networks for coordination.
```

### ENHANCED APPROACH (Natural):
```
Q: Mateo, how bad is the water situation in Pilsen right now?
A: Bad. Real bad. CorpSec cut off access to the main line last week.
Q: Damn. So what are you doing? You can't just let people go without water.
A: No, we're... [sighs] We're running night convoys through the old tunnels. It's slow, dangerous work, but—
Q: [interrupting] The tunnels? Isn't that where Maria got caught?
A: Yeah. Different tunnel, but yeah. We learned from that. Now we... Look, it's still risky, but what choice do we have?
Q: Right. Okay, so you're using the tunnels. How do you keep CorpSec from tracking the routes?
A: We rotate them every night. And we're using the mesh network to coordinate in real-time. If someone spots a patrol, we can reroute before—
Q: Wait, how do you do that without... I mean, doesn't the mesh network traffic give away your position?
A: [laughs] Good question. You sound like my tech guy. So what we do is...
```

Notice the differences:
- Affirmations: "Damn", "Right"
- Emotional reaction: "You can't just let people go without water"
- Interruption: Real conversation flow
- Follow-up from answer: "The tunnels? Isn't that where..."
- Processing aloud: "Wait, how do you do that without..."
- Humor: "You sound like my tech guy"
- Natural flow rather than Q&A list

---

## ALTERNATE SEGMENT TYPE: TACTICAL DEBRIEF

Instead of interview format, try a **post-action conversation** between two equals.

### Concept
Two organizers just got back from a supply run that went wrong. They're processing what happened while it's fresh.

### Structure

**Cold Open:**
```
[Both catching breath, adrenaline still high]
Person A: [breathing hard] Okay. We're clear. You good?
Person B: Yeah. Yeah, I'm good. [pause] Jesus, that was close.
Person A: Too close. What the hell happened back there?
```

**Reconstruction:**
- Walk through what happened step by step
- Different perspectives: "I thought you were behind me" vs "I was dealing with the drone"
- Puzzle-solving together: "Why did they have patrols there? That route was clean last week."
- Emotional reactions: Fear, relief, guilt, anger

**Lessons Learned:**
- "Next time, we..."
- "If that happens again..."
- Organic teaching for listeners

**Looking Forward:**
- What do they tell the collective?
- What do they keep between them?
- Ready to go again?

### Why This Works
- More dynamic than Q&A
- Emotional authenticity (just lived it)
- Natural teaching moments
- Shows decision-making under pressure
- Builds character relationship

### Example Excerpt:
```
A: When that drone came around the corner, why'd you go left?
B: Because right was a dead end. I scouted that alley last week, remember?
A: Oh. Right. Shit, I forgot.
B: [laughs] Yeah, well, I'm glad one of us remembered. But why didn't you follow me?
A: I couldn't! There was a patrol coming up from behind. I had to—
B: Wait, a patrol? I didn't see a patrol.
A: You were already around the corner. They came out of the basement entrance on Halsted.
B: [pause] Okay. Okay, so we need to map the basement entrances. Add that to the briefing.
A: Already writing it down. Also, we need better comms. I couldn't reach you when—
B: I know. The jammer was stronger than we thought. We need to boost the signal or...
A: Or go analog. Hand signals.
B: [laughs] Like we're back in training. Remember when you couldn't tell left from right?
A: [laughing] Oh fuck off, that was one time!
```

Notice:
- Reconstructing together
- Different info from different perspectives
- Emotional moments (fear → relief → humor)
- Practical lessons emerging organically
- Relationship building
- Natural teaching without being didactic
