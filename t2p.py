import requests

# 输入关键字
keywords = ['沙灘', '車子']

# 遍历关键字并搜索图像
for keyword in keywords:
    # 发送搜索请求
    url = f"https://api.unsplash.com/search/photos?query={keyword}&per_page=1"
    headers = {"Authorization": "Client-ID Bp1FHabpX_l5GhTunUrURKZbYlsO0chZT2_Zrj-Mb-M"}
    response = requests.get(url, headers=headers)
    
    # 解析响应数据
    data = response.json()
    if 'results' in data and len(data['results']) > 0:
        # 获取图像 URL
        image_url = data['results'][0]['urls']['regular']
        
        # 下载图像
        image_data = requests.get(image_url).content
        
        # 保存图像到本地文件
        with open(f"{keyword}.jpg", "wb") as f:
            f.write(image_data)
        
        print(f"找到关键字 '{keyword}' 的图像，并已保存到本地。")
    else:
        print(f"没有找到关键字 '{keyword}' 的图像。")
