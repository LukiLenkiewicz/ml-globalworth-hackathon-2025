from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Dict, Any, Optional, List
import os
from dotenv import load_dotenv
from openai import OpenAI
import json

# Import your schema
from schemas import OfficeInquiry

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

def prepare_empty_inquiry(schema: type[BaseModel]):
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

def update_inquiry(inquiry: Dict[str, Any], response_dict: Dict[str, Any]) -> Dict[str, Any]:
    for k in response_dict:
        if k in inquiry:
            inquiry[k]['value'] = response_dict[k]
    return inquiry

def is_inquiry_complete(inquiry: Dict[str, Any]) -> bool:
    # Check if all required fields have values
    for field in inquiry:
        if inquiry[field]['value'] is None:
            return False
    return True

@app.post("/start-inquiry/")
async def start_inquiry():
    try:
        empty_inquiry = prepare_empty_inquiry(OfficeInquiry)
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
        updated_inquiry = update_inquiry(current_inquiry, extracted_fields)
        conversation_state.inquiry_state = updated_inquiry
        
        # Check if inquiry is complete
        if is_inquiry_complete(updated_inquiry):
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