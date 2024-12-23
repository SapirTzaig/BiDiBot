from openai import OpenAI

client = OpenAI(
  api_key="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"
)

completion = client.chat.completions.create(
  model="gpt-4o-mini",
  store=True,
  messages=[
    {"role": "user", "content": "write a haiku about ai"}
  ]
)

print(completion.choices[0].message);