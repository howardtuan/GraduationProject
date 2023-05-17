from flask import Flask, render_template, jsonify
import speech_recognition as sr

app = Flask(__name__)
static_folder='static'
# 創建一個辨識器
r = sr.Recognizer()

@app.route('/')
def index():
    return render_template('index_2.html')

@app.route('/transcribe')
def transcribe():
    # 使用電腦麥克風
    with sr.Microphone() as source:
        # 設置最小音量閾值
        r.adjust_for_ambient_noise(source, duration=1)

        # 監聽語音
        audio = r.listen(source)

        try:
            # 辨識語音
            text = r.recognize_google(audio, language='zh-TW')
            return jsonify({'text': text})
        except sr.UnknownValueError:
            return jsonify({'error': 'Speech recognition could not understand audio.'}), 400
        except sr.RequestError:
            return jsonify({'error': 'Speech recognition service unavailable.'}), 500

if __name__ == '__main__':
    app.run()
