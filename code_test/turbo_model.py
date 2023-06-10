import os
import openai
openai.api_key = 'api key'
while True:  
    completion = openai.ChatCompletion.create(
      model="gpt-3.5-turbo",
      messages=[
            {"role": "system", "content": "系統訊息，目前無用"},
            {"role": "assistant", "content": "此處填入機器人訊息"},
            {"role": "user", "content": input("You: ")}
        ]
    )
    print(completion.choices[0].message.content)
