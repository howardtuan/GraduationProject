import os
import cv2
from translate import Translator
import pytesseract

# 中文文本
text = "跑車 晴天"

# 创建翻译器对象
translator = Translator(to_lang="en", from_lang="zh")

# 图片文件夹路径
image_folder = "./pic"

# 按空格分割字符串为单词列表
words = text.split()

# 翻译为英文
translated_words = []
for word in words:
    translated_word = translator.translate(word)
    translated_words.append(translated_word)

# 输出翻译结果
print("翻译后的关键词:")
for word in translated_words:
    print(word)

# 搜索匹配的图片
matched_images = []
for filename in os.listdir(image_folder):
    image_path = os.path.join(image_folder, filename)
    image = cv2.imread(image_path)

    # 提取图像内容
    gray_image = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

    # 读取图像内容为文本
    image_text = pytesseract.image_to_string(gray_image)

    # 比较关键词与图像内容
    for word in translated_words:
        if word in image_text:
            matched_images.append(image_path)

# 输出匹配的图片文件路径
if matched_images:
    print("找到匹配的图片路径:")
    for image_path in matched_images:
        print(image_path)
else:
    print("没有找到匹配的图片。")
