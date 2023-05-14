import speech_recognition as sr
import tkinter as tk
from PIL import Image, ImageTk

# 創建一個辨識器
r = sr.Recognizer()

# 創建 tkinter 視窗
root = tk.Tk()
root.geometry("1024x768")

# 創建文字區域並放置在右邊的1/3
text_area = tk.Text(root)
text_area.place(relx=0.66, rely=0, relwidth=0.33, relheight=1)

# 創建圖片並轉換成 Tkinter 圖像格式
def resize_by_width(image_path, width):
    with Image.open(image_path) as img:
        wpercent = (width / float(img.size[0]))
        hsize = int((float(img.size[1]) * float(wpercent)))
        return img.resize((width, hsize))


frog_image = resize_by_width("frog.jpeg", 400)
frog_image_tk = ImageTk.PhotoImage(frog_image)

map_image = resize_by_width("map.png", 400)
map_image_tk = ImageTk.PhotoImage(map_image)

picA_image = resize_by_width("picA.png", 400)
picA_image_tk = ImageTk.PhotoImage(picA_image)

picB_image = resize_by_width("picB.png", 400)
picB_image_tk = ImageTk.PhotoImage(picB_image)

news_image = resize_by_width("news.png", 400)
news_image_tk = ImageTk.PhotoImage(news_image)


# 創建圖片標籤列表
image_labels = []

# 使用電腦麥克風
with sr.Microphone() as source:
    # 設置最小音量閾值
    r.adjust_for_ambient_noise(source, duration=1)
    text_area.insert('end', "請開始說話...\n")
    root.update()

    # 持續監聽直到停止
    while True:
        # 辨識語音
        # audio = r.listen(source)
        audio = r.listen(source)
        # audio = r.listen(source, timeout=1, phrase_time_limit=3)

        try:
            # 辨識語音
            text = r.recognize_google(audio, language='zh-TW', show_all=False)
            text_area.insert('end', text + '\n')
            #講完第二句話就刪除前一句所講出的圖
            for label in image_labels:
                label.pack_forget()
            
            root.update()

            # 判斷輸入的文字
            if '壯觀的日月潭夕陽' in text:
                # 顯示地圖圖片
                image_label = tk.Label(root, image=picB_image_tk)
                image_label.pack(side='left', padx=10, pady=10)
                image_labels.append(image_label)
                # image_label.place(x = 0, y = 0)# 圖片都生成在同一個點
                root.update()
            elif '日月潭夕陽' in text:
                # 顯示地圖圖片
                image_label = tk.Label(root, image=picA_image_tk)
                image_label.pack(side='left', padx=10, pady=10)
                image_labels.append(image_label)
                # image_label.place(x = 0, y = 0)# 圖片都生成在同一個點
                root.update()


            if '青蛙' in text:
                # 顯示青蛙圖片
                image_label = tk.Label(root, image=frog_image_tk)
                image_label.pack(side='left', padx=10, pady=10)
                image_labels.append(image_label)
                # image_label.place(x = 0, y = 0)# 圖片都生成在同一個點
                root.update()
            if '路線' in text:
                # 顯示地圖圖片
                image_label = tk.Label(root, image=map_image_tk)
                image_label.pack(side='left', padx=10, pady=10)
                image_labels.append(image_label)
                # image_label.place(x = 0, y = 0)# 圖片都生成在同一個點
                root.update()
            
            if '新聞' in text:
                # 顯示地圖圖片
                image_label = tk.Label(root, image=news_image_tk)
                image_label.pack(side='left', padx=10, pady=10)
                image_labels.append(image_label)
                # image_label.place(x = 0, y = 0)# 圖片都生成在同一個點
                root.update()
            if text == '刪除':
                # 隱藏所有圖片
                for label in image_labels:
                    label.pack_forget()
                root.update()
            if text == '高歌離席':
                text_area.insert('end', '走囉嘿嘿～\n')
                root.update()
                break
        except sr.UnknownValueError:
            pass
        except sr.RequestError as e:
            text_area.insert('end', "無法辨識語音服務：{0}\n".format(e))
            root.update()

# 關閉 tkinter 視窗
root.mainloop()
