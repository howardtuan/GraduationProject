import speech_recognition as sr
import tkinter as tk
from PIL import Image, ImageTk

class interface:
    
    def __init__(self):
        # Setup the environment
        r = sr.Recognizer()
        # 創建 tkinter 視窗
        self.root = tk.Tk()
        self.root.geometry("1024x768")

        self.image_labels = []
        
        # 創建文字區域並放置在右邊的1/3
        self.text_area = tk.Text(self.root)
        self.text_area.place(relx=0.66, rely=0, relwidth=0.33, relheight=1)
        
        frog_image = self.resize_by_width("assets/images/frog.jpeg", 400)
        self.frog_image_tk = ImageTk.PhotoImage(frog_image)

        map_image = self.resize_by_width("assets/images/map.png", 400)
        self.map_image_tk = ImageTk.PhotoImage(map_image)

        picA_image = self.resize_by_width("assets/images/picA.png", 400)
        self.picA_image_tk = ImageTk.PhotoImage(picA_image)

        picB_image = self.resize_by_width("assets/images/picB.png", 400)
        self.picB_image_tk = ImageTk.PhotoImage(picB_image)

        news_image = self.resize_by_width("assets/images/news.png", 400)
        self.news_image_tk = ImageTk.PhotoImage(news_image)
        
    def resize_by_width(self, image_path, width):
        with Image.open(image_path) as img:
            wpercent = (width / float(img.size[0]))
            hsize = int((float(img.size[1]) * float(wpercent)))
            return img.resize((width, hsize))
    
    def check(self, text):
        self.text_area.insert('end', text + '\n')
        if '壯觀的日月潭夕陽' in text:
            # 顯示地圖圖片
            image_label = tk.Label(self.root, image = self.picB_image_tk)
            image_label.pack(side = 'left', padx = 10, pady = 10)
            self.image_labels.append(image_label)
            # image_label.place(x = 0, y = 0)# 圖片都生成在同一個點
            self.root.update()
        elif '日月潭夕陽' in text:
            # 顯示地圖圖片
            image_label = tk.Label(self.root, image = self.picA_image_tk)
            image_label.pack(side='left', padx=10, pady=10)
            self.image_labels.append(image_label)
            # image_label.place(x = 0, y = 0)# 圖片都生成在同一個點
            self.root.update()


        if '青蛙' in text:
            # 顯示青蛙圖片
            image_label = tk.Label(self.root, image = self.frog_image_tk)
            image_label.pack(side='left', padx=10, pady=10)
            self.image_labels.append(image_label)
            # image_label.place(x = 0, y = 0)# 圖片都生成在同一個點
            self.root.update()
        if '路線' in text:
            # 顯示地圖圖片
            image_label = tk.Label(self.root, image=self.map_image_tk)
            image_label.pack(side='left', padx=10, pady=10)
            self.image_labels.append(image_label)
            # image_label.place(x = 0, y = 0)# 圖片都生成在同一個點
            self.root.update()
        
        if '新聞' in text:
            # 顯示地圖圖片
            image_label = tk.Label(self.root, image=self.news_image_tk)
            image_label.pack(side='left', padx=10, pady=10)
            self.image_labels.append(image_label)
            # image_label.place(x = 0, y = 0)# 圖片都生成在同一個點
            self.root.update()
        if text == '刪除':
            # 隱藏所有圖片
            for label in self.image_labels:
                label.pack_forget()
            self.root.update()