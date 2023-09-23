import os
import livejson
import numpy as np
from transformers import pipeline
from sentence_transformers import SentenceTransformer, util

image_dir = "./static/images/"
image_paths = [os.path.join(image_dir, image_name) for image_name in os.listdir(image_dir)] #使用 os.listdir 获取该目录下所有图像文件的路径，并存在 image_paths
image_to_text = pipeline("image-to-text", model = "nlpconnect/vit-gpt2-image-captioning")   #GPT2的模型将圖轉成文字描述
text_encode = SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2') #將文字描述轉成嵌入向量
jsonF = livejson.File("ImageCaption.json")

for image_path in image_paths:
    text = image_to_text(image_path)[0]["generated_text"]   #開轉文字
    embedding = text_encode.encode(text, convert_to_tensor = True).cpu().numpy()    #再全轉向量
    arr_path = "./static_arr/" + image_path.split("/")[3].split(".")[0] + "_" + image_path.split("/")[3].split(".")[1]
    np.save(arr_path, embedding)    #將向量存到static_arr中
    jsonF[image_path] = text    #將相對路徑存到
