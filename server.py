import base64
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Dict, Any, Literal, Optional, List
import os
from dotenv import load_dotenv
from openai import OpenAI
import json

# Import your schema
from schemas import OfficeInquiry, OfficeChangesForm

# Load environment variables
load_dotenv()

app = FastAPI()

# Add CORS middleware to allow frontend requests
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins in development
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

client = OpenAI()

class ConversationState(BaseModel):
    next_question: str
    inquiry_state: Dict[str, Any]
    conversation_completed: bool = False

class UserMessage(BaseModel):
    message: str
    conversation_state: ConversationState
    
class OfficeRecommendation(BaseModel):
    building_match: str
    building_images: List[str]
    office_match: str
    office_images: List[str]
    recommendation_text: str
    is_short_term: bool

def prepare_empty_form(schema: type[BaseModel]):
    inquiry = schema.model_json_schema()['properties']
    for k in inquiry:
        inquiry[k]['value'] = None
    return inquiry

def create_next_inquiry_question(inquiry: Dict[str, Any]) -> str:
    messages = [
        {
            "role": "system", 
            "content": "Jesteś pomocnym asystentem użytkownika, który pomaga wypełnić formularz zapytania ofertowego dotyczącego wynajmu przestrzeni biurowej. Na podstawie aktualnego stanu formularza zadaj pytanie użytkownikowi, aby uzyskać część brakujących informacji. Nie pytaj o zbyt wiele informacji na raz (max 2-3 logicznie powiązane pytania, jeśli możliwe jest sformułowanie ich w jednym pytaniu). Nie informuj użytkownika o tym, że wypełnia formularz. Zadawaj jedynie pytania."
        },
        {
            "role": "developer",
            "content": str(inquiry)
        }
    ]

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=messages
    )
    
    return response.choices[0].message.content

def extract_inquiry_fields(inquiry: Dict[str, Any], user_answer: str) -> Dict[str, Any]:
    messages = [
        {
            "role": "system", 
            "content": "Jesteś pomocnym asystentem użytkownika, który pomaga wypełnić formularz zapytania ofertowego dotyczącego wynajmu przestrzeni biurowej. Na podstawie odpowiedzi użytkownika wypełnij odpowiednie pola formularza. Zwróć tylko pola, na które użytkownik udzielił informacji w formacie JSON. Nie zwracaj żadnych dodatkowych informacji ani komunikatów."
        },
        {
            "role": "developer",
            "content": str(inquiry)
        },
        {
            "role": "user",
            "content": user_answer
        }
    ]

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=messages,
        response_format={"type": "json_object"}
    )
    
    return json.loads(response.choices[0].message.content)

def update_form(form_state: Dict[str, Any], response_dict: Dict[str, Any]) -> Dict[str, Any]:
    for k in response_dict:
        if k in form_state:
            form_state[k]['value'] = response_dict[k]
    return form_state

def is_form_complete(form_state: Dict[str, Any]) -> bool:
    # Check if all required fields have values
    for field in form_state:
        if form_state[field]['value'] is None:
            return False
    return True

def find_inquiry_match(inquiry, towers_data, type=Literal['office', 'building']):
    # Format the inquiry data for the prompt
    inquiry_description = format_inquiry_for_prompt(inquiry)
    
    # Format offices data for the prompt
    towers_formatted = json.dumps(towers_data, ensure_ascii=False, indent=2)
    
    prompt = f"""
    Jesteś ekspertem ds. nieruchomości specjalizującym się w powierzchniach biurowych. Twoim zadaniem jest dopasowanie zapytania klienta do najlepiej pasującego {'budynku' if type=='building' else 'biura'} z dostępnej bazy.

    ## Wymagania zapytania dotyczącego {'budynku' if type=='building' else 'biura'}:
    {inquiry_description}
    
    ## Dostępne {'budynki' if type=='building' else 'biura'}:
    {towers_formatted}
    
    Przeanalizuj zapytanie klienta i znajdź najlepiej dopasowany {'budynek' if type=='building' else 'biuro'} spośród dostępnych. Weź pod uwagę wszystkie czynniki, takie jak lokalizacja, metraż, cena, dostępność oraz konkretne wymagania.

    Twoja odpowiedź powinna być sformatowana jako JSON i zawierać następujące pola:
    1. "best_match": {'Nazwa najlepiej dopasowanego budynku' if type=='building' else 'Numer piętra najlepiej dopasowanego biura'}
    2. "match_score": Wynik od 0 do 100, określający jak dobrze {'budynek' if type=='building' else 'biuro'} spełnia wymagania
    3. "reasoning": Szczegółowe wyjaśnienie, dlaczego wybrano ten {'budynek' if type=='building' else 'biuro'}
    4. "recommendation": Rekomendacja w języku naturalnym, jaką przekazałbyś klientowi

    Zwróć tylko odpowiedź w formacie JSON, bez dodatkowych komentarzy.
    """
    
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        response_format={"type": "json_object"}
    )
    
    result = json.loads(response.choices[0].message.content)
    return result

def format_inquiry_for_prompt(inquiry):
    description = []
    
    if inquiry.get('office_area_m2', {}):
        description.append(f"- Wymagana powierzchnia biurowa: {inquiry['office_area_m2']} m²")
    
    if inquiry.get('number_of_employees', {}):
        description.append(f"- Liczba pracowników: {inquiry['number_of_employees']}")
    
    if inquiry.get('preferred_district_or_area', {}):
        description.append(f"- Preferowana lokalizacja: {inquiry['preferred_district_or_area']}")
    
    if inquiry.get('preferred_floor', {}):
        description.append(f"- Preferowane piętro: {inquiry['preferred_floor']}")
    
    if inquiry.get('monthly_budget_net_PLN', {}):
        description.append(f"- Miesięczny budżet (netto): {inquiry['monthly_budget_net_PLN']} PLN")
    
    if inquiry.get('office_type', {}):
        description.append(f"- Typ biura: {inquiry['office_type']}")
    
    # Add other fields as needed
    
    return "\n".join(description)

def extract_building_info(data):
    buildings = []
    for building in data:
        building_info = {
            "nazwa": building.get("budynek", {}).get("nazwa"),
            "adres": building.get("budynek", {}).get("adres"),
            "miasto": building.get("budynek", {}).get("miasto"),
            "lokalizacja": building.get("budynek", {}).get("lokalizacja"),
            "opis_okolicy": building.get("budynek", {}).get("opis_okolicy"),
            "udogodnienia": building.get("udogodnienia"),
            "transport": building.get("transport"),
            "sasiedztwo": building.get("sasiedztwo"),
            "uslugi_w_budynku": building.get("uslugi_w_budynku"),
            "dostepnosc_dla_osob_niepelnosprawnych": building.get("dostepnosc_dla_osob_niepelnosprawnych"),
            "powierzchnia_magazynowa": building.get("powierzchnia_magazynowa"),
            "liczba_miejsc_parkingowych": building.get("liczba_miejsc_parkingowych"),
            "typ_parkingu": building.get("typ_parkingu"),
            "typ_biur": building.get("typ_biur"),
            "wysokosc_kondygnacji": building.get("wysokosc_kondygnacji")
        }
        buildings.append(building_info)
    return buildings

def extract_office_info(data):
    offices = []
    
    for floor in data.get("pietra", []):
        info = {
            "numer_pietra": floor.get("numer"),
            "dostepnosc_od": floor.get("dostepnosc_od"),
            "powierzchnia": floor.get("powierzchnia"),
            "cena_za_m2": floor.get("cena"),
            "najkrotszy_okres_wynajmu": floor.get("najkrotszy_okres_wynajmu"),
            "mozliwe_wydzielenia": floor.get("wydzielenia")
        }
        offices.append(info)

    return offices

def load_office_database(directory_path="towers"):
    buildings = []
    for filename in os.listdir(directory_path):
        if filename.endswith('.json'):
            with open(os.path.join(directory_path, filename), 'r', encoding='utf-8') as f:
                buildings.append(json.load(f))
    return buildings

def parse_inquiry_dict(inquiry_state: Dict[str, Any]):
    return {k: v['value'] for k, v in inquiry_state.items()}

def get_floor_images(towers, building_name, floor_number):
    base64_images = []
    
    if building_name == 'Quattro Business Park':
    
        for building in towers:
            if building['budynek']['nazwa'] == building_name:
                for floor in building['pietra']:
                    if floor['numer'] == floor_number:
                        image_paths = floor.get('zdjecia', [])
                        
                        return image_paths
                        
                        # for path in image_paths:
                        #     path = os.path.join(os.getcwd(), path)
                        #     try:
                        #         with open(path, "rb") as image_file:
                        #             encoded_string = base64.b64encode(image_file.read()).decode('utf-8')
                        #             base64_images.append(f"data:image/jpeg;base64,{encoded_string}")
                        #     except FileNotFoundError:
                        #         print(f"File not found: {path}")
                        #         continue
                        # return base64_images
    else:
        image_paths = [
            'office_mocks/space1/empty_office_3_1.png',
            'office_mocks/space2/empty_office_3_2.png',
            'office_mocks/space3/empty_office_3_3.png'
        ]
        return image_paths
        # for path in image_paths:
        #     try:
        #         with open(path, "rb") as image_file:
        #             encoded_string = base64.b64encode(image_file.read()).decode('utf-8')
        #             base64_images.append(f"data:image/jpeg;base64,{encoded_string}")
        #     except FileNotFoundError:
        #         print(f"File not found: {path}")
        #         continue
                    
        # return base64_images
                
def get_building_images(towers, building_name):
    base64_images = []
    
    for building in towers:
        if building['budynek']['nazwa'] == building_name:
            image_paths = building['zdjecia'].get("zewnetrzne", [])
            if not isinstance(image_paths, list):
                image_paths = [image_paths]
                
            return image_paths
            
    #         for path in image_paths:
    #             try:
    #                 path = os.path.join(os.getcwd(), path)
    #                 with open(path, "rb") as image_file:
    #                     encoded_string = base64.b64encode(image_file.read()).decode('utf-8')
    #                     base64_images.append(f"data:image/jpeg;base64,{encoded_string}")
    #             except FileNotFoundError:
    #                 print(f"File not found: {path}")
    #                 continue
    #         break
            
    # return base64_images
        
def create_next_design_question(form_state: Dict[str, Any]) -> str:
    messages = [
        {
            "role": "system", 
            "content": """Jesteś pomocnym asystentem projektanta wnętrz, który pomaga klientowi określić preferencje dotyczące aranżacji biura. Na podstawie aktualnego stanu formularza zadaj pytanie użytkownikowi, aby uzyskać część brakujących informacji. Nie pytaj o zbyt wiele informacji na raz. Nie informuj użytkownika o tym, że wypełnia formularz. Zadawaj jedynie pytania."""
        },
        {
            "role": "developer",
            "content": str(form_state)
        }
    ]

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=messages
    )
    
    return response.choices[0].message.content

def extract_design_fields(form_state: Dict[str, Any], user_answer: str) -> Dict[str, Any]:
    messages = [
        {
            "role": "system", 
            "content": """Jesteś pomocnym asystentem projektanta wnętrz, który pomaga klientowi określić preferencje dotyczące aranżacji biura. Na podstawie odpowiedzi użytkownika wypełnij odpowiednie pola formularza. Zwróć tylko pola, na które użytkownik udzielił informacji w formacie JSON. Nie zwracaj żadnych dodatkowych informacji ani komunikatów."""
        },
        {
            "role": "developer",
            "content": str(form_state)
        },
        {
            "role": "user",
            "content": user_answer
        }
    ]

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=messages,
        response_format={"type": "json_object"}
    )
    
    return json.loads(response.choices[0].message.content)

@app.post("/get-initial-design/")
async def get_initial_design(design_preferences: Dict[str, Any]):
    office_images = design_preferences.pop('office_images', [])
    if not office_images:
        raise HTTPException(status_code=400, detail="No office images provided.")
    
    try:
        # Format preferences
        preferences_json = json.dumps(design_preferences, ensure_ascii=False, indent=2)

        # Build initial prompt content
        content = [
            {
                "type": "text",
                "text": f"""
    You are an experienced interior designer specializing in office spaces.

    I'm showing you {len(office_images)} empty office spaces that need to be designed according to the following requirements:

    # DESIGN PREFERENCES
    {preferences_json}

    # TASK
    Create a detailed visualization description for each space, distributing the requested elements logically across the images while maintaining a cohesive Scandinavian design style.

    Important guidelines:

    1. Don't duplicate major functional areas (e.g., don't put the chill-out room in more than one image).
    2. Some ares should appear simillar if there is enought space (e.g. work space if design prefferences mentioned only work space and chill-out room).
    3. Maintain the preffered style consistently across all spaces.
    4. Distribute the requested equipment and features logically between the spaces based on what would work in each area.
    5. Consider the actual architecture and features visible in each image.
    6. Include specific details about colors, materials, furniture placement, and lighting.
    7. Include office equipement that was mentioned in the preferences.

    # RESPONSE FORMAT
    Return a JSON array with one object per image, each with:
    - "space_name": Name of the functional space
    - "design_description": Detailed description of the design
    - "layout_description": Detailed description of the layout and items (for further visualization purposes)
    - "key_elements": List of key elements included in the space

    Return only the JSON array, no extra explanation.
    """

            }
        ]

        # Add each image to the content
        for i, base64_image in enumerate(office_images):
            content.append({
                "type": "image_url",
                "image_url": {
                    "url": f"{base64_image}",
                    "detail": "high"
                }
            })
            content.append({
                "type": "text",
                "text": f"Image {i + 1}: Empty office space to be designed."
            })

        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "user",
                    "content": content
                }
            ],
            response_format={"type": "json_object"}
        )

        result = json.loads(response.choices[0].message.content)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/start-design/")
async def start_design():
    try:
        empty_form = prepare_empty_form(OfficeChangesForm)
        initial_question = create_next_design_question(empty_form)
        
        initial_state = ConversationState(
            next_question=initial_question,
            inquiry_state=empty_form,
            conversation_completed=False
        )
        
        return initial_state
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
@app.post("/parse-design-message/")
async def parse_design_message(user_input: UserMessage):
    try:
        # Extract current state
        conversation_state = user_input.conversation_state
        current_form = conversation_state.inquiry_state
        
        # Extract information from user message
        extracted_fields = extract_design_fields(current_form, user_input.message)
        
        # Update form state
        updated_form = update_form(current_form, extracted_fields)
        conversation_state.inquiry_state = updated_form
        
        # Check if form is complete
        if is_form_complete(updated_form):
            conversation_state.conversation_completed = True
        else:
            # Generate next question
            next_question = create_next_design_question(updated_form)
            conversation_state.next_question = next_question
        
        return conversation_state
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/find-best-inquiry-match/")
async def find_best_inquiry_match(inquiry_state: Dict[str, Any]):
    try:
        inquiry_dict = parse_inquiry_dict(inquiry_state)
        towers = load_office_database()
        
        is_short_term = inquiry_dict.get('short_term_rental', False)
        
        # Get building match
        bmatches = find_inquiry_match(inquiry_dict, towers, "building")
        best_building = bmatches['best_match']
        building_text = bmatches['recommendation']
        building_match = [tower for tower in towers if tower['budynek']['nazwa'] == best_building][0]
        building_images = get_building_images(towers, best_building)
        
        # Get office match
        offices = extract_office_info(building_match)
        omatches = find_inquiry_match(inquiry_dict, offices, "office")
        best_office = omatches['best_match']
        office_text = omatches['recommendation']
        office_images = get_floor_images(towers, best_building, best_office)
        
        response = OfficeRecommendation(
            building_match=str(best_building),
            building_images=building_images,
            
            office_match=str(best_office),
            office_images=office_images,
            
            recommendation_text=building_text + office_text,
            is_short_term=is_short_term
        )
        return response
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    

@app.post("/start-inquiry/")
async def start_inquiry():
    try:
        empty_inquiry = prepare_empty_form(OfficeInquiry)
        initial_question = create_next_inquiry_question(empty_inquiry)
        
        initial_state = ConversationState(
            next_question=initial_question,
            inquiry_state=empty_inquiry,
            inquiry_completed=False
        )
        
        return initial_state
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/parse-inquiry-message/")
async def parse_inquiry_message(user_input: UserMessage):
    try:
        # Extract current state
        conversation_state = user_input.conversation_state
        current_inquiry = conversation_state.inquiry_state
        
        # Extract information from user message
        extracted_fields = extract_inquiry_fields(current_inquiry, user_input.message)
        
        # Update inquiry state
        updated_inquiry = update_form(current_inquiry, extracted_fields)
        conversation_state.inquiry_state = updated_inquiry
        
        # Check if inquiry is complete
        if is_form_complete(updated_inquiry):
            conversation_state.conversation_completed = True
        else:
            # Generate next question
            next_question = create_next_inquiry_question(updated_inquiry)
            conversation_state.next_question = next_question
        
        return conversation_state
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)