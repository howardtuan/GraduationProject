import os
import openai
from flask import Flask, render_template, jsonify,request
import json

with open('secret.json', 'r') as file:
    data = json.load(file)
OPENAI_API_KEY = data.get("OPENAI_API_KEY")
app = Flask(__name__)
static_folder='static'


@app.route('/')
def index():
    return render_template('index.html')

@app.route("/get_dialogue_summary", methods=["POST"])
def get_dialogue_summary():
    openai.api_key = OPENAI_API_KEY
    input_param = request.get_json().get('inputParam')
    print('接收的逐字稿',input_param)
    completion = openai.ChatCompletion.create(
      model="gpt-3.5-turbo",
      messages=[
            {"role": "system", "content": "你是一位負責將逐字稿轉換為重點整理的工作人員，請將以下逐字稿修改為大綱以及重點整理，格式為「主題：」「大綱：」「重點整理：」請條列式自動換行:"},
            {"role": "user", "content": input_param}
        ]
    )
    print(completion.choices[0].message.content)

    completed_text = completion.choices[0].message.content
    print(completed_text)
    return jsonify(response=completed_text)


    

if __name__ == '__main__':
    app.run()

