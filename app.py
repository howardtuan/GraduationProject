import os
import openai
from flask import Flask, render_template, jsonify,request
import json

with open('secret.json', 'r') as file:
    data = json.load(file)
OPENAI_API_KEY = data.get("OPENAI_API_KEY")
app = Flask(__name__)
static_folder='static'


@app.route('/')
def index():
    return render_template('index.html')

@app.route("/get_dialogue_summary", methods=["POST"])
def get_dialogue_summary():
    openai.api_key = OPENAI_API_KEY
    input_param = request.get_json().get('inputParam')
    print('接收的逐字稿',input_param)
    completion = openai.ChatCompletion.create(
      model="gpt-3.5-turbo",
      temperature=0,   
      messages=[
            {"role": "system", "content": "你是一位負責將逐字稿轉換為重點整理的工作人員，請將以下逐字稿修改為大綱以及重點整理，格式為「主題：」「大綱：」「重點整理：」請條列式自動換行:"},
            {"role": "user", "content": input_param}
        ]
    )
    print(completion.choices[0].message.content)

    completed_text = completion.choices[0].message.content
    print(completed_text)
    return jsonify(response=completed_text)

@app.route("/get_sentence_analyze", methods=["POST"])
def get_sentence_analyze():
    openai.api_key = OPENAI_API_KEY
    input_param = request.get_json().get('inputParam')
    print('接收的逐字稿 main',input_param)
    completion = openai.ChatCompletion.create(
      model="gpt-3.5-turbo-16k",
      messages=[
            #進入特殊模式後，需要另外寫進入該模式的邏輯
            {"role": "system", "content": "你是負責判斷句子中重點含義的人，需要注意的點有以下：當語意是「用AI繪圖」，則回應「AI生圖」；當語意是「自己拍的照片」，則回應「相簿取圖」；當語意是「幫我查詢...或是該句子可以透過網路得到答案」，則回應「爬蟲模式」；當語意是「使用簡報」，則回應「簡報模式」；當語意是「產生圖表」，則回應「圖表模式」；當語意是「產生地圖」，則回應「地圖模式」；若語意沒有以上的內容，則回應「None」，不可以有其他類型的回應，僅可以回應以上我允許的文字"},
            {"role": "user", "content": "欸你看我昨天在日月潭拍的夕陽"},
            {"role": "assistant", "content": "相簿取圖"},
            {"role": "user", "content": "幫我用AI產生有一隻狗在草原上奔跑的圖"},
            {"role": "assistant", "content": "AI生圖"},
            {"role": "user", "content": "進入簡報模式"},
            {"role": "assistant", "content": "簡報模式"},
            {"role": "user", "content": "進入圖表模式，五月的銷售額為20萬，六月的有90萬"},
            {"role": "assistant", "content": "圖表模式"},
            {"role": "user", "content": "好想睡覺"},
            {"role": "assistant", "content": "None"},
            {"role": "user", "content": "幫我查麥當勞優惠的新聞"},
            {"role": "assistant", "content": "爬蟲模式"},
            {"role": "user", "content": "開啟地圖"},
            {"role": "assistant", "content": "地圖模式"},
            {"role": "user", "content": input_param}
        ]
    )
    print(completion.choices[0].message.content)

    completed_text = completion.choices[0].message.content
    print(completed_text)
    return jsonify(response=completed_text)
    # return render_template('index.html', completed_text=completed_text)  # 将 completed_text 传递给模板

initMessage="""
    你是一個簡報小幫手，使用者會輸入幾句話，你要負責生成那幾句話的PPT標題、內容文字以及圖片（每次都盡量根據使用者輸入的文字去選擇適合的圖片，提供圖片名稱即可），請用python的字典格式{'Title':'','LittleTitle':[],'Content':[],'PIC':[]}來回答。LittleTitle跟Content及PIC的value在同一個index情況下會有對應的關係！
    LittleTitle指的是這段文字的小標題。
    Content是重點整理使用者輸入的內容，並將其精簡化，不可使文字跟輸入的文字一模一樣!
    PIC通常會跟LittleTitle一樣，是輔助它的圖片！
    當還沒進到下一頁時，若先前已經介紹過某個LittleTitle並加入至LittleTitle、Content、PIC的話，不可以移除已經加入的內容！但如果兩句話都在講同一個小主題的話，可以更新並重整該主題的Content，使句字更順暢！接收到「下一頁」時，就回傳清空value的字典！
    若使用者輸入「離開簡報模式」，則回傳"None"字串即可。
    """
# messages_db = [
#     {"role": "system", "content": initMessage},
#     {"role": "user", "content": "今天我要介紹的主題就是2023中原資管小琉球之旅"},
#     {"role": "assistant", "content": "{'Title':'中原資管－小琉球之旅','LittleTitle':[],'Content':[],'PIC':['小琉球']}"},
#     {"role": "user", "content": "下一頁"},
#     {"role": "assistant", "content": "{'Title':'','LittleTitle':[],'Content':[],'PIC':[]}"},
#     {"role": "user", "content": "總共分為三部分，第一是旅遊景點，第二是水上活動，第三是美食推薦"},
#     {"role": "assistant", "content": "{'Title':'中原資管－小琉球之旅','LittleTitle':['旅遊景點','水上活動','美食推薦'],'Content':[],'PIC':[]}"},
#     {"role": "user", "content": "下一頁"},
#     {"role": "assistant", "content": "{'Title':'','LittleTitle':[],'Content':[],'PIC':[]}"},
#     {"role": "user", "content": "那這頁先來介紹旅遊景點"},
#     {"role": "assistant", "content": "{'Title':'旅遊景點','LittleTitle':[],'Content':[],'PIC':[]}"},
#     {"role": "user", "content": "我們第一個去的就是花瓶岩，他為小琉球最顯眼、最著名的地標，是一塊因地殼隆起作用而抬升於海面上的珊瑚礁岩"},
#     {"role": "assistant", "content": "{'Title':'旅遊景點','LittleTitle':['花瓶岩'],'Content':['我們首先造訪了小琉球的著名地標花瓶岩，它是海面上隆起的珊瑚礁岩。'],'PIC':['花瓶岩']}"},
#     {"role": "user", "content": "又因長期受海水差異性侵蝕，而形成頭大身小的外觀，類似花瓶的特殊造型，加上岩頂上長滿了臭娘子與盒果藤等植物，看起來如同插著花草的花瓶，因此取名為「花瓶岩」。"},
#     {"role": "assistant", "content": "{'Title':'旅遊景點','LittleTitle':['花瓶岩'],'Content':['我們首站造訪了小琉球的著名地標——花瓶岩。它因地殼隆起而升起于海面，外觀特殊，類似花瓶，岩頂長滿植物，被稱為「花瓶岩」。'],'PIC':['花瓶岩']}"},
#     {"role": "user", "content": "第二個地點則是龍蝦洞，是因海水侵蝕所形成的天然海蝕溝及美麗的石灰岩所構成的純天然洞穴"},
#     {"role": "assistant", "content": "{'Title':'旅遊景點','LittleTitle':['花瓶岩','龍蝦洞'],'Content':['我們首站造訪了小琉球的著名地標——花瓶岩。它因地殼隆起而升起于海面，外觀特殊，類似花瓶，岩頂長滿植物，被稱為「花瓶岩」。接著，我們前往龍蝦洞，這個地方是由海水侵蝕形成的天然海蝕溝和美麗的石灰岩組成的自然洞穴。'],'PIC':['花瓶岩','龍蝦洞']}"},
#     {"role": "user", "content": "海蝕溝外觀寬大且深，每當海浪拍打進入龍蝦洞內，潮聲如吼，蔚為壯觀。"},
#     {"role": "assistant", "content": "{'Title':'旅遊景點','LittleTitle':['花瓶岩','龍蝦洞'],'Content':['我們首站造訪了小琉球的著名地標——花瓶岩。它因地殼隆起而升起于海面，外觀特殊，類似花瓶，岩頂長滿植物，被稱為「花瓶岩」。第二個地點是龍蝦洞，由海水侵蝕形成的天然海蝕溝和美麗的石灰岩構成的自然洞穴。海蝕溝寬大且深，海浪拍打進洞內時發出激越的潮聲，令人驚嘆。'],'PIC':['花瓶岩','龍蝦洞']}"},
#     {"role": "user", "content": "下一頁"},
#     {"role": "assistant", "content": "{'Title':'','LittleTitle':[],'Content':[],'PIC':[]}"},
#     {"role": "user", "content": "這一頁則是水上活動，有SUP和獨木舟兩種設施，「SUP」是「Stand Up Paddle」的縮寫，中文是「立式划槳」的意思，顧名思義就是以站姿划槳前進的運動，是個簡單易學、老少咸宜的活動，新手老手都能玩。"},
#     {"role": "assistant", "content": "{'Title':'水上活動','LittleTitle':['SUP','獨木舟'],'Content':['這頁介紹了水上活動，包括SUP（立式划槳）和獨木舟。SUP是以站姿划槳前進的運動，適合各年齡層，容易上手。'],'PIC':['SUP','獨木舟']}"},
#     {"role": "user", "content": "而獨木舟活動也無需具備任何經驗亦無特別的年齡限制，入門相當容易，就算是不會游泳的小朋友或者長者都可以參加。"},
#     {"role": "assistant", "content": "{'Title':'水上活動','LittleTitle':['SUP','獨木舟'],'Content':['這頁介紹了水上活動，包括SUP（立式划槳）和獨木舟。SUP是以站姿划槳前進的運動，適合各年齡層，容易上手。而獨木舟活動同樣適合沒有經驗的人，並無特定年齡限制。即使是不會游泳的小朋友或長者也可以參加，入門容易。'],'PIC':['SUP','獨木舟']}"},
#     {"role": "user", "content": "下一頁"},
#     {"role": "assistant", "content": "{'Title':'','LittleTitle':[],'Content':[],'PIC':[]}"},
#     {"role": "user", "content": "最後一頁則是美食推薦，包括海龜燒、來這吃冰吧和小蝌蚪起司餅"},
#     {"role": "assistant", "content": "{'Title':'美食推薦','LittleTitle':['海龜燒','來這吃冰吧','小蝌蚪起司餅'],'Content':[],'PIC':['海龜燒','來這吃冰吧','小蝌蚪起司餅']}"},
#     {"role": "user", "content": "海龜燒其實就是海龜造型的雞蛋糕，將外皮烤得非常酥脆且充滿雞蛋香與奶香，有著可愛的外觀和甜甜的滋味"},
#     {"role": "assistant", "content": "{'Title':'美食推薦','LittleTitle':['海龜燒','來這吃冰吧','小蝌蚪起司餅'],'Content':['海龜燒是海龜造型的雞蛋糕，外皮酥脆，充滿雞蛋和奶香，外觀可愛，味道甜美。'],'PIC':['海龜燒','來這吃冰吧','小蝌蚪起司餅']}"},
#     {"role": "user", "content": "來這吃冰吧是網美最愛的韓系風格雪花冰店，店內裝潢以白色簡約為主，有種小清新的感覺～"},
#     {"role": "assistant", "content": "{'Title':'美食推薦','LittleTitle':['海龜燒','來這吃冰吧','小蝌蚪起司餅'],'Content':['海龜燒是海龜造型的雞蛋糕，外皮酥脆，充滿雞蛋和奶香，外觀可愛，味道甜美。「來這吃冰吧」是網美們喜愛的韓系風格雪花冰店，店內以白色簡約裝潢為主，帶有小清新的氛圍。'],'PIC':['海龜燒','來這吃冰吧','小蝌蚪起司餅']}"},
#     {"role": "user", "content": "最後則是連在地人都激推的美食，小蝌蚪起司餅！酥脆的餅皮搭配香濃罪惡的起司和店家特調的醬料及海苔粉，鹹甜的口味越嚼越香，而且每一口都能吃到飛魚卵在嘴巴逼逼波波的滋味，超級幸福～"},
#     {"role": "assistant", "content": "{'Title':'美食推薦','LittleTitle':['海龜燒','來這吃冰吧','小蝌蚪起司餅'],'Content':['海龜燒是海龜造型的雞蛋糕，外皮酥脆，充滿雞蛋和奶香，外觀可愛，味道甜美。「來這吃冰吧」是網美們喜愛的韓系風格雪花冰店，店內以白色簡約裝潢為主，帶有小清新的氛圍。最後，我們來介紹當地人大力推薦的美食，小蝌蚪起司餅！餅皮酥脆，搭配濃郁的起司、店家特調的醬料和海苔粉，鹹甜的口味令人愛不釋口。每一口都帶來飛魚卵爆漿的美味，極具幸福感。'],'PIC':['海龜燒','來這吃冰吧','小蝌蚪起司餅']}"},
#     {"role": "user", "content": "離開簡報模式"},
#     {"role": "assistant", "content": "None"},

#     {"role": "user", "content": "以上是某一個主題的訓練範本，接下來的主題會截然不同，請記得以上的回應模式，但不要將主題內容跟後面的主題混為一談"},
# ]   
messages_db = [
    {"role": "system", "content": initMessage},
    {"role": "user", "content": "今天的報告主題是中原大學周邊介紹"},
    {"role": "assistant", "content": "{'Title':'中原大學周邊介紹','LittleTitle':[],'Content':[],'PIC':['小琉球']}"},
    {"role": "user", "content": "下一頁"},
    {"role": "assistant", "content": "{'Title':'','LittleTitle':[],'Content':[],'PIC':[]}"},
    {"role": "user", "content": "總共分為兩部分，第一是生活小物，第二是美食補給"},
    {"role": "assistant", "content": "{'Title':'中原大學周邊介紹','LittleTitle':['生活小物','美食補給'],'Content':[],'PIC':[]}"},
     {"role": "user", "content": "那這邊先來介紹生活小物"},
    {"role": "assistant", "content": "{'Title':'生活小物','LittleTitle':[],'Content':[],'PIC':[]}"},
    {"role": "user", "content": "最推薦的就是小北百貨，雖然稱為五金百貨，但24小時營業，且店內商品琳瑯滿目，從五金、生活用品，到文具、零食、飲料都有，是你購買生活用品的好選擇。"},
    {"role": "assistant", "content": "{'Title':'生活小物','LittleTitle':['小北百貨'],'Content':['極力推薦小北百貨！雖然以五金百貨為名，但24小時營業，提供琳瑯滿目的商品，包括五金、生活用品、文具、零食、飲料等等，是你生活用品的最佳選擇。'],'PIC':['小北百貨']}"},
    {"role": "user", "content": "下一頁"},
    {"role": "assistant", "content": "{'Title':'','LittleTitle':[],'Content':[],'PIC':[]}"},
    {"role": "user", "content": "再來是美食補給"},
    {"role": "assistant", "content": "{'Title':'美食補給','LittleTitle':[],'Content':[],'PIC':[]}"},
    {"role": "user", "content": "首先推薦老師傅牛肉麵，牛肉的質地十分嫩滑，入口即化，同時保留了肉的原汁原味，麵湯混合著牛骨的鮮香和各種香料的濃郁，使整碗牛肉麵更加美味。"},
    {"role": "assistant", "content": "{'Title':'美食補給','LittleTitle':['老師傅牛肉麵'],'Content':['首先，我推薦嘗試老師傅牛肉麵。牛肉的質地非常嫩滑，幾乎在入口瞬間化開，同時還保持著肉的原汁原味。麵湯則融合了牛骨的鮮香和各種香料的濃郁風味，這使得整碗牛肉麵更加美味可口。'],'PIC':['老師傅牛肉麵']}"},
    {"role": "user", "content": "離開簡報模式"},
    {"role": "assistant", "content": "None"},
    {"role": "user", "content": "以上是某一個主題的訓練範本，接下來的主題會截然不同，請記得以上的回應模式，但不要將主題內容跟後面的主題混為一談"},
]   
@app.route("/get_ppt", methods=["POST"])
def get_ppt():
    openai.api_key = OPENAI_API_KEY
    
    status=1
    while status:
        input_param = request.get_json().get('inputParam')
        print('接收的逐字稿 ppt',input_param)
        if "結束簡報模式" in input_param:
            status=0
            return jsonify(response='None')
        
        # 添加使用者輸入到對話歷史中
        messages_db.append({"role": "user", "content": input_param})
        
        # 使用完整的對話歷史呼叫模型
        completion = openai.ChatCompletion.create(
            model="gpt-3.5-turbo-16k",
            messages=messages_db
        )
        
        # 提取助手回應並輸出
        assistant_response = completion.choices[0].message['content']
        # 添加助手回應到對話歷史中
        messages_db.append({"role": "assistant", "content": assistant_response})
        print(completion.choices[0].message.content)

        completed_text = completion.choices[0].message.content
        print(completed_text)
        return jsonify(response=completed_text)



map_initMessage="""
    你是一個地圖小幫手，
    使用者會輸入幾句話，你要負責找到對應的圖片名稱
    請用python的字典格式{'map':'','map_detail':''}來回答
    只有使用者輸入「開啟地圖」，map_detail才會為空，且map的value值開頭會加上「M」，會回傳{'map':'M地圖','map_detail':''}
    若使用者輸入「離開地圖模式」，則回傳"None"字串即可。
    """
map_messages_db = [
    {"role": "system", "content": map_initMessage},
    {"role": "user", "content": "開啟空白地圖"},
    {"role": "assistant", "content": "{'map':'M地圖','map_detail':''}"},
    {"role": "user", "content": "我想看教學大樓"},
    {"role": "assistant", "content": "{'map':'M教學大樓','map_detail':'教學大樓'}"},
    {"role": "user", "content": "看看資管樓"},
    {"role": "assistant", "content": "{'map':'M資管樓','map_detail':'資管樓'}"},
    {"role": "user", "content": "活動中心長怎樣"},
    {"role": "assistant", "content": "{'map':'M活動中心','map_detail':'活動中心'}"},
    {"role": "user", "content": "離開地圖模式"},
    {"role": "assistant", "content": "None"},

]   
@app.route("/get_map", methods=["POST"])
def get_map():
    openai.api_key = OPENAI_API_KEY
    
    status=1
    while status:
        input_param = request.get_json().get('inputParam')
        print('接收的逐字稿 map',input_param)
        if "結束地圖模式" in input_param:
            status=0
            return jsonify(response='None')
        
        # 添加使用者輸入到對話歷史中
        map_messages_db.append({"role": "user", "content": input_param})
        
        # 使用完整的對話歷史呼叫模型
        completion = openai.ChatCompletion.create(
            model="gpt-3.5-turbo-16k",
            messages=map_messages_db
        )
        
        # 提取助手回應並輸出
        assistant_response = completion.choices[0].message['content']
        # 添加助手回應到對話歷史中
        map_messages_db.append({"role": "assistant", "content": assistant_response})
        print(completion.choices[0].message.content)

        completed_text = completion.choices[0].message.content
        print(completed_text)
        return jsonify(response=completed_text)
        
        
       


    
    

if __name__ == '__main__':
    app.run()

