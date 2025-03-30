import json

SYSTEM_PROMPT = """
Jesteś pomocnym asystentem użytkownika. Na podstawie podanego słownika wyślij 
wygeneruj 3 opisy zagospodoarowania pustej przestrzeni biurowej. Zadbaj o to 
aby opisy te nieco różniły się od siebie, jak najwięcej elementów z opisu zostało 
uwzględnionych. Zwróć tylko pola, na które użytkownik udzielił informacji w formacie 
JSON. Nie zwracaj żadnych dodatkowych informacji ani komunikatów. JSON powinien składać
się z klucza 'description' a w nim powinna się znajdować lista 3 opisów. Postaraj się,
żeby opisy nie były dłuższe niż 77 znaków.
"""


def get_inpainting_prompts(client, data):
    data = data.model_copy()
    del data.images
    openai_request = str(data.model_dump())
    response = _get_room_descriptions(client, openai_request)
    response = json.loads(response)
    prompts = response["description"]
    return prompts


def _get_room_descriptions(client, prompt):
    messages = [
        {
            "role": "system", 
            "content": SYSTEM_PROMPT
        },
        {
            "role": "user",
            "content": prompt
        }
    ]
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=messages,
        temperature=0.2,
        response_format={"type": "json_object"}
    )
    return response.choices[0].message.content
