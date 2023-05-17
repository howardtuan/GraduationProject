import os
import cv2
from fuzzywuzzy import fuzz
from translate import Translator

# 中文文本
text = '青蛙 有名的 跑車'

# 创建翻译器对象
translator = Translator(to_lang="en", from_lang="zh")

# 图片文件夹路径
image_folder = './pic'

# 按空格分割字符串为单词列表
words = text.split()

# 逐个词进行翻译
translated_words = []
for word in words:
    translated_word = translator.translate(word)
    translated_words.append(translated_word)

# 输出翻译结果
translated_text = ' '.join(translated_words)
print(translated_text)

# 搜索匹配的图片
matched_images = []
for filename in os.listdir(image_folder):
    image_path = os.path.join(image_folder, filename)
    image = cv2.imread(image_path)
    image_features = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

    for word in translated_words:
        similarity = fuzz.ratio(word, filename)  # 使用fuzzywuzzy计算相似度
        threshold = 50  # 调整阈值为合适的数值
        print(similarity)
        if similarity > threshold:
            matched_images.append(image_path)

# 输出匹配的图片文件路径
for image_path in matched_images:
    print(f'关键词匹配的图片路径: {image_path}')
