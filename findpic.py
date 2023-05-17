import cv2
import numpy as np
import difflib
from googletrans import Translator

# 图像路径和中文文本
image_path = './pic/828eaa7a3469666631769e73a736cf18.jpeg.jpg'
text = 'super car'


# 图像特征提取
image = cv2.imread(image_path)
image_features = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

# 计算文本与图像之间的相似度
similarity = difflib.SequenceMatcher(None, text, image_path).ratio()

# 设置相似度阈值
threshold = 0.5

if similarity > threshold:
    print(f"找到与文本匹配的图像：{image_path}")
else:
    print("没有找到与文本匹配的图像。")
