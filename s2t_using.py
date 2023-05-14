import speech_recognition as sr
import jieba
from jieba import analyse


# 創建一個辨識器
r = sr.Recognizer()

# 使用電腦麥克風
with sr.Microphone() as source:
    # 設置最小音量閾值
    r.adjust_for_ambient_noise(source, duration=1)
    print("請開始說話...")

    # 持續監聽直到停止
    while True:
        # 辨識語音
        audio = r.listen(source)

        try:
            text = r.recognize_google(audio, language='zh-TW', show_all=False)
            for char in text:
                print(char, end='', flush=True)
            print('\n')
            if text == '高歌離席':
                print('走囉嘿嘿～')
                break
            # 分词
            seg_list = jieba.cut(text)

            # 关键词提取
            keywords = analyse.extract_tags("".join(seg_list), topK=3, withWeight=False)

            # 打印关键词
            print("關鍵字：", " ".join(keywords))
   
        except sr.UnknownValueError:
            pass
        except sr.RequestError as e:
            print("無法辨識語音服務：{0}".format(e))