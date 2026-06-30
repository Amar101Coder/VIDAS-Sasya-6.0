import re
import json
from openai import OpenAI

# Replace with your OpenAI API key
client = OpenAI(api_key="YOUR_API_KEY")


def get_difficult_words(text):
    """
    Uses AI to generate a dictionary of difficult words
    and their simpler replacements.
    """

    prompt = f"""
You are an English simplification assistant.

Read the following text.

Find difficult English words that an average Grade 6-8 student may struggle with.

Return ONLY a JSON dictionary.

Example:
{{
    "utilize": "use",
    "commence": "start",
    "terminate": "end"
}}

Text:
{text}
"""

    response = client.chat.completions.create(
        model="gpt-5-mini",
        messages=[
            {
                "role": "system",
                "content": "Return only valid JSON."
            },
            {
                "role": "user",
                "content": prompt
            }
        ],
        temperature=0.2
    )

    return json.loads(response.choices[0].message.content)


def simplify_text(text, dictionary):
    simplified = text

    for hard, easy in dictionary.items():
        simplified = re.sub(
            rf"\b{re.escape(hard)}\b",
            easy,
            simplified,
            flags=re.IGNORECASE
        )

    return simplified


def highlight_difficult_words(text, dictionary):
    highlighted = text

    for hard, easy in dictionary.items():
        highlighted = re.sub(
            rf"\b({re.escape(hard)})\b",
            rf'<span class="highlight" title="Meaning: {easy}">\1</span>',
            highlighted,
            flags=re.IGNORECASE
        )

    return highlighted


if __name__ == "__main__":

    text = """
    Students should commence the experiment and utilize numerous scientific instruments.
    The professor instructed them to implement the procedure carefully before they terminate the session.
    """

    # Generate dictionary using AI
    difficult_words = get_difficult_words(text)

    print("Generated Dictionary:")
    print(json.dumps(difficult_words, indent=4))

    simplified = simplify_text(text, difficult_words)
    highlighted = highlight_difficult_words(text, difficult_words)

    print("\nSimplified Text:\n")
    print(simplified)

    print("\nHighlighted HTML:\n")
    print(highlighted)