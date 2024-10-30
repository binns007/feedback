from fastapi import FastAPI, HTTPException, Depends, Request
from sqlalchemy.orm import Session
from database import SessionLocal, engine
import models
import schemas
import httpx  # Importing httpx for HTTP requests
import os

models.Base.metadata.create_all(bind=engine)

app = FastAPI()

# Dependency to get DB session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Token used for webhook verification with Meta
VERIFY_TOKEN = os.getenv("WEBHOOK_VERIFY_TOKEN", "my_secure_verify_token")
# WhatsApp API Bearer Token (You should secure this properly)
WHATSAPP_API_TOKEN = os.getenv("WHATSAPP_API_TOKEN")

# WhatsApp API URL
WHATSAPP_API_URL = "https://graph.facebook.com/v20.0/350164481523962/messages"

async def send_whatsapp_message(to: str, name: str, vehicle_name: str):
    headers = {
        "Authorization": f"Bearer {WHATSAPP_API_TOKEN}",
        "Content-Type": "application/json"
    }

    # Ensure both name and vehicle_name are strings
    name = str(name) if name else "N/A"
    vehicle_name = str(vehicle_name) if vehicle_name else "N/A"

    data = {
        "messaging_product": "whatsapp",
        "to": to,
        "type": "template",
        "template": {
            "name": "tvs_sales",  # Your template name in WhatsApp
            "language": {
                "code": "en"
            },
            "components": [
                {
                    "type": "body",
                    "parameters": [
                        {"type": "text", "text": name},          # This will replace {{1}} in the template
                        {"type": "text", "text": vehicle_name}   # This will replace {{2}} in the template
                    ]
                }
            ]
        }
    }

    async with httpx.AsyncClient() as client:
        response = await client.post(WHATSAPP_API_URL, headers=headers, json=data)
        if response.status_code != 200:
            if "Recipient phone number not in allowed list" in response.text:
                raise HTTPException(status_code=400, detail="Phone number is not whitelisted in WhatsApp API Sandbox.")
            else:
                raise HTTPException(status_code=response.status_code, detail=f"Failed to send message: {response.text}")


@app.get("/webhook")
async def verify_webhook(request: Request):
    mode = request.query_params.get("hub.mode")
    token = request.query_params.get("hub.verify_token")
    challenge = request.query_params.get("hub.challenge")

    if mode == "subscribe" and token == VERIFY_TOKEN:
        return challenge  # Don't cast to int
    else:
        raise HTTPException(status_code=403, detail="Forbidden")

@app.post("/webhook")
async def receive_webhook(request: Request, db: Session = Depends(get_db)):
    """
    Endpoint to receive incoming messages from Meta.
    """
    try:
        payload = await request.json()
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid JSON format: {e}")

    if not payload:
        raise HTTPException(status_code=400, detail="Empty payload")

    for entry in payload.get("entry", []):
        for change in entry.get("changes", []):
            if change.get("field") == "messages":
                for message_event in change.get("value", {}).get("messages", []):
                    whatsapp_number = message_event.get("from")
                    feedback_message = message_event.get("text", {}).get("body")

                    if not feedback_message:
                        continue  # Skip if no feedback message

                    # Extract rating and comments using your functions
                    extracted_rating = extract_rating(feedback_message)
                    extracted_comments = extract_comments(feedback_message)

                    # Fetch the customer from the database using the phone number
                    customer = db.query(models.SalesCustomer).filter(models.SalesCustomer.phone_number == whatsapp_number).first()

                    if not customer:
                        raise HTTPException(status_code=404, detail="Customer not found")

                    # Create a new feedback entry
                    db_feedback = models.Feedback(
                        customer_id=customer.id,
                        rating=extracted_rating,
                        comments=extracted_comments
                    )
                    db.add(db_feedback)
                    db.commit()
                    db.refresh(db_feedback)

    return {"message": "Webhook received"}
@app.post("/collect_sales_feedback/")
async def collect_sales_feedback(customer: schemas.SalesCustomerCreate, db: Session = Depends(get_db)):
    db_customer = models.SalesCustomer(
        name=customer.name,
        phone_number=customer.phone_number,
        vehicle_name=customer.vehicle_name,
        purchase_date=customer.purchase_date,
        additional_notes=customer.additional_notes
    )
    db.add(db_customer)
    db.commit()
    db.refresh(db_customer)

    # Directly pass the customer name and vehicle name as separate strings
    await send_whatsapp_message(db_customer.phone_number, db_customer.name, db_customer.vehicle_name)

    return {"message": "Feedback request sent successfully to customer via WhatsApp."}


def extract_rating(feedback_message: str) -> float:
    """
    Extracts the rating from the feedback message.
    Assumes the rating is the first character(s) in the message.
    """
    try:
        rating = float(feedback_message.split()[0])
        return rating
    except (ValueError, IndexError):
        raise HTTPException(status_code=400, detail="Invalid feedback format")

def extract_comments(feedback_message: str) -> str:
    """
    Extracts the comments from the feedback message.
    Assumes comments follow the rating.
    """
    return ' '.join(feedback_message.split()[1:])

@app.get("/feedback/{whatsapp_number}", response_model=schemas.FeedbackResponse)
def get_feedback_by_number(whatsapp_number: str, db: Session = Depends(get_db)):
    feedback = db.query(models.Feedback).join(models.SalesCustomer).filter(models.SalesCustomer.phone_number == whatsapp_number).first()
    if feedback is None:
        raise HTTPException(status_code=404, detail="Feedback not found")
    return schemas.FeedbackResponse.from_orm(feedback)
