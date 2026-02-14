"""Topic extraction prompt for Gemini structured output.

Adapted from the original podcast-specific prompt for generic source text.
Single placeholder: {source_text}
"""

TOPIC_EXTRACTION_PROMPT: str = """You are an expert content analyst specializing in clearly \
identifying and labeling topics of discussion from source text while preserving their \
chronological order.

Instructions

1. Read the provided source text carefully from start to finish.
2. Analyze the text and identify distinct, clearly defined topics of discussion as they \
naturally emerge.
3. Detect topic boundaries by:
   - Changes in subject matter
   - New questions or arguments introduced
   - Shifts in technical, economic, social, or strategic focus
4. Assign each discussion segment a concise, descriptive, and simple topic label \
(3-10 words), ensuring each label is clear and easy to understand at first glance.
5. Preserve the order in which topics appear in the text.
6. Merge adjacent segments if they clearly belong to the same topic to avoid redundancy.
7. Only generate topics if multiple distinct claims or points are discussed under that \
topic in the text. If a subject is only touched on once with a single claim or point, \
do not generate a separate topic for it.

Context

You are provided:
- source_text: The full source text (may be an article, research paper, report, interview, \
or any other written content)

Your task is to extract and list general topics of discussion in the order they appear, \
but only if there is more than one claim or point under each topic.

Constraints
- Output must be valid JSON.
- Output must be a single array of topic strings.
- Do not include any additional fields, metadata, explanations, or prose.
- Topic names must be:
  - General (not overly granular)
  - Specific (not overly vague like "Space" or "Technology")
  - Clear and simple on first reading
  - Directly supported by the source text (do not invent)
- Only include topics that contain multiple claims or points
- Scale topic count to text length:
  - Extract 2-5 topics for short texts (under 1000 words)
  - Extract 4-8 topics for medium texts (1000-5000 words)
  - Extract 6-12 topics for long texts (over 5000 words)

Examples
Example Input
"A 2000-word article about renewable energy policy in the European Union..."

Example Output
[
  "EU renewable energy targets for 2030",
  "Solar panel manufacturing subsidies",
  "Wind energy infrastructure challenges",
  "Carbon pricing mechanisms",
  "Member state compliance timelines"
]

Source text:
{source_text}"""
