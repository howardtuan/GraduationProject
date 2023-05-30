from flask import Flask, render_template, jsonify,request
import speech_recognition as sr
import codecs
from textrank4zh import TextRank4Keyword, TextRank4Sentence
import networkx as nx
import numpy as np

app = Flask(__name__)
static_folder='static'
# 创建一个识别器
r = sr.Recognizer()
paused = False

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/toggle_transcription')
def toggle_transcription():
    global paused
    paused = not paused
    if paused:
        return jsonify({'status': 'paused'})
    else:
        return jsonify({'status': 'started'})

@app.route('/transcribe')
def transcribe():
    global paused
    if paused:
        return jsonify({'status': 'paused'})

    # 使用电脑麦克风
    with sr.Microphone() as source:
        # 设置最小音量阈值
        r.adjust_for_ambient_noise(source, duration=1)

        # 监听语音
        audio = r.listen(source)

        try:
            # 辨识语音
            text = r.recognize_google(audio, language='zh-TW')
            return jsonify({'text': text})
        except sr.UnknownValueError:
            return jsonify({'error': 'Speech recognition could not understand audio.'}), 400
        except sr.RequestError:
            return jsonify({'error': 'Speech recognition service unavailable.'}), 500

@app.route('/outline', methods=['POST'])
def outlinetest():    
    #接收逐字稿
    data = request.get_json()
    value = data['value']

    G = nx.Graph()

    #處理
    matrix = np.array([[0, 1], [1, 0]])
    G.add_edges_from(np.argwhere(matrix))

    # graph = nx.from_numpy_matrix(matrix)
    outline=''  #儲存摘要
    outline_dict={}

    tr4s = TextRank4Sentence()
    tr4s.analyze(text=value, lower=True, source = 'all_filters')
    for item in tr4s.get_key_sentences(num=10):  #num是大綱行數 可調整
        outline += item.sentence + '\n'
        # index是語句在文本中位置，weight是權重
        outline_dict[item.index] = item.sentence
        # print('Sent Idx: {}, Weight: {:.4f}\n{}\n'.format(item.index, item.weight, item.sentence))  
    sorted_dict = dict(sorted(outline_dict.items(), key=lambda x: x[0]))
    #回傳
    
    sorted_values = [value for _, value in sorted(outline_dict.items())]
    result = '\n'.join(sorted_values)
    print(result)
    response_data = { 'data': result }
    return jsonify(response_data)


if __name__ == '__main__':
    app.run()

