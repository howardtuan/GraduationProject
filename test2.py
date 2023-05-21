from textrank4zh import TextRank4Sentence

def generate_summary(text):
    tr4s = TextRank4Sentence()
    tr4s.analyze(text=text, lower=True, source='all_filters')
    summary = []
    for item in tr4s.get_key_sentences(num=3):
        summary.append(item.sentence)
    return ' '.join(summary)

text = """
在這個世界上，有許多不同的動物。狗是人類最好的朋友之一。狗是一種忠誠、友好且可愛的動物。牠們可以成為家庭的一員並提供無條件的愛和陪伴。狗有很多品種，例如黃金獵犬、柴犬和哈士奇等。每個品種都有自己獨特的特點和特徵。狗可以幫助人們守護家園、尋找失蹤的人，以及提供情感支持。總的來說，狗是非常特別和重要的動物。
"""

summary = generate_summary(text)
print(summary)
