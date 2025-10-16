import os

import requests

API_KEY = os.environ.get("OPEN_AI_KEY_STUDENT")
if API_KEY is None:
    print("NO OPEN APi KEY")


def prompt(content):
    url = "https://api.openai.com/v1/chat/completions"
    headers = {"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"}
    data = {
        "model": "gpt-4o-mini",  # or gpt-4o, gpt-3.5-turbo, etc.
        "messages": [{"role": "user", "content": content}],
        "temperature": 0.7,
    }

    response = requests.post(url, headers=headers, json=data)

    if response.status_code == 200:
        result = response.json()
        # print(response.text)
        print(result["choices"][0]["message"]["content"])
    else:
        print(f"Error {response.status_code}: {response.text}")


def create_data_uri(base64_str, image_type="jpeg"):
    return f"data:image/{image_type};base64,{base64_str}"


def prompt_img(img, tresc, logger):
    #logger.info(f"Running prompt {tresc}")
    zapytanie = f"Jesteś patologicznym studentem warszawskim. Napisz śmieszną reakcje na posta składającego z załączonego zdjęcia i treści:'{tresc}'. Max 150 liter. Możesz udawać że jesteś studentem specyficznego kierunku jeśli jest to śmieszne w kontekście. Używaj emoji dużo. "
    url = "https://api.openai.com/v1/chat/completions"
    headers = {"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"}
    if img:
        data = {
            "model": "gpt-4o-mini",
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": zapytanie},
                        {
                            "type": "image_url",
                            "image_url": {"url": f"data:image/jpeg;base64,{img}"},
                        },
                    ],
                }
            ],
            "max_tokens": 300,
        }
    else:
        data = {
            "model": "gpt-4o-mini",
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": zapytanie},
                    ],
                }
            ],
            "max_tokens": 300,
        }

    response = requests.post(url, headers=headers, json=data)
    #logger.info(f"Result status code: {response.status_code}, Text: {response.text}")
    if response.status_code == 200:
        result = response.json()
        # print(response.text)
        return result["choices"][0]["message"]["content"]
    else:
        logger.error(f"{response.status_code}: {response.text}")


if __name__ == "__main__":
    print("hello")
    # all_posts = requests.get("http://localhost:5000/api/post")
    # Create list of Post contents
    # text_contents = "\n".join([x["tresc"] for x in all_posts.json()])
    # prompt_txt = f"Podsumuj treści postów stworzonych przez studentów. Każda nowa treść jest w nowej linii \n {text_contents}"
    # prompt(prompt_txt)
    # print(prompt_img(all_posts.json()[2]))
