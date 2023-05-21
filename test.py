import openai

# 設定OpenAI API金鑰
openai.api_key = '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'

def generate_summary(text):
    # 使用OpenAI GPT模型進行文本生成
    response = openai.Completion.create(
        engine='text-davinci-003',  # 選擇適合的模型引擎
        prompt=text,
        max_tokens=100,  # 生成的最大令牌數
        temperature=0.7,  # 控制生成的多樣性，0.0為最保守，1.0為最自由
        n=1,  # 生成的示例數量
        stop=None,  # 生成結束的條件
        echo=True  # 顯示生成的回應
    )

    # 提取生成的摘要
    summary = response.choices[0].text.strip()

    return summary

# 要進行摘要的對話
dialogue = """
王乙己一到DC，所有點投降的人都對著他笑，有的叫道：「林子佑要被扁囉～欸嘿！」
他不回答，對著麥說：「這些人是有病是不是啊？」便開始噴垃圾話。
他們又故意的高聲嚷道：「我們怎麼知道大家都會點啊！」
王乙己生氣地說大家是在玩什麼遊戲，這是積分嗎？
有人解釋史博宇先投降，然後大家都跟著投降，只是開個玩笑而已。
王乙己越來越生氣，開始發表激烈的言論，指責大家浪費他的時間。
人們紛紛引起嘲笑，玩笑話不斷，氣氛歡快。
DC內外充滿了快活的空氣。
"""

summary = generate_summary(dialogue)
print("摘要：", summary)
