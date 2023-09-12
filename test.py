import urllib.request
from serpapi import GoogleSearch
import json

def serpapi_get_google_images(keyword, maxSearch = 1):
    image_results = []
    if type(keyword) != list:
        keyword = [keyword]
    for query in keyword:
        # search query parameters
        params = {
            "engine": "google",               # search engine. Google, Bing, Yahoo, Naver, Baidu...
            "q": query,                       # search query
            "tbm": "isch",                    # image results
            "num": "5",                     # number of images per page
            "ijn": 0,                         # page number: 0 -> first page, 1 -> second...
            "api_key": "d20b6b2e50b081f56b410d26b6b8267060fbbb9da0d8eb91261de463a1666efa",                 # https://serpapi.com/manage-api-key
            # other query parameters: hl (lang), gl (country), etc  
        }
    
        search = GoogleSearch(params)         # where data extraction happens
    
        images_is_present = True
        cnt = 0
        while images_is_present:
            results = search.get_dict()       # JSON -> Python dictionary
            
            # checks for "Googl e hasn't returned any results for this query."
            if "error" not in results:
                for idx, image in enumerate(results["images_results"]):
                    if image["original"] not in image_results:
                        # print(image["original"], idx) # print
                        image_results.append(image["original"])
                    if idx == maxSearch - 1:
                        images_is_present = False
                        break
                # update to the next page
                params["ijn"] += 1
            else:
                print(results["error"])
                images_is_present = False
            if cnt == maxSearch:
                images_is_present = False
            cnt += 1
            
    
    # Downloading

    for index, image in enumerate(results["images_results"], start=1):
        print(f"Downloading {index} image...")
        
        opener=urllib.request.build_opener()
        opener.addheaders=[("User-Agent","Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/103.0.5060.114 Safari/537.36")]
        urllib.request.install_opener(opener)

        urllib.request.urlretrieve(image["original"], f"imgs/original_size_img_{index}.jpg")
        if index == maxSearch:
            break

    print(json.dumps(image_results, indent=2))
    # print(len(image_results))

if __name__ == "__main__":
    serpapi_get_google_images(["中原大學 方緯翔"])