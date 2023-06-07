import os
import openai
from flask import Flask, render_template, jsonify,request
app = Flask(__name__)
static_folder='static'

@app.route('/')
def index():
    return render_template('index.html')

@app.route("/get_dialogue_summary", methods=["POST"])
def get_dialogue_summary():
    key = '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'
    openai.api_key = key

    # 从 POST 请求的 JSON 数据中获取参数值
    input_param = request.get_json().get('inputParam')
    print('接收的逐字稿',input_param)
    startQ = "請將以下逐字稿修改為大綱以及重點整理，格式為「主題：」「大綱：」「重點整理：」請條列式自動換行:"
    # 在 prompt 中使用获取到的参数值
    prompt = f"{startQ} {input_param}"
    # prompt=input_param
    response = openai.Completion.create(
        engine='text-davinci-003',
        prompt=prompt,
        max_tokens=2000,
        temperature=0.5
    )

    completed_text = response['choices'][0]['text']
    print(completed_text)
    return jsonify(response=completed_text)


    

if __name__ == '__main__':
    app.run()

