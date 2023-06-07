const { Configuration, OpenAIApi } = require("openai");

const configuration = new Configuration({
  apiKey: 'api key',
});
const openai = new OpenAIApi(configuration);

async function chatWithGPT(prompt) {
  try {
    const response = await openai.createCompletion({
      model: "text-davinci-003",
      prompt: prompt,
      temperature: 1,
      max_tokens: 256,
      top_p: 1,
      frequency_penalty: 0,
      presence_penalty: 0,
    });
    console.log(response);
    if (response.data && response.data.choices && response.data.choices.length > 0) {
      console.log(response.data.choices[0].text);
    } else {
      console.log('API 回應格式錯誤');
    }
  } catch (error) {
    console.error(error);
  }
}


// 使用範例
const prompt = "你好，如何使用 OpenAI GPT 进行聊天？";
chatWithGPT(prompt);
