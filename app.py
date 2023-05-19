from flask import Flask, render_template, jsonify
import speech_recognition as sr

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

if __name__ == '__main__':
    app.run()
