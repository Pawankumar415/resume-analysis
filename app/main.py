import json
import os
import pdfplumber
import google.generativeai as genai
from dotenv import load_dotenv
from fastapi import FastAPI, UploadFile, File, HTTPException, Depends
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from pathlib import Path
from database import get_db, engine, Base
from models import ResumeData
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from routes import report_routes, subscription_routes, user_routes
from fastapi.openapi.utils import get_openapi

# ==================== FASTAPI APP CONFIGURATION ====================
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/users/login")
app = FastAPI()

# Include your routes
app.include_router(report_routes.router, prefix="/reports", tags=["Reports"])
app.include_router(subscription_routes.router, prefix="/subscriptions", tags=["Subscriptions"])
app.include_router(user_routes.router, prefix="/users", tags=["Users"])

# ==================== ANALYZE RESUME ENDPOINT ====================
UPLOAD_FOLDER = "uploaded_resumes"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)  # Ensure folder exists

def extract_text_from_pdf(pdf_file) -> str:
    try:
        with pdfplumber.open(pdf_file) as pdf:
            text = " ".join(page.extract_text() or "" for page in pdf.pages)
        if not text.strip():
            raise ValueError("No readable text found in the PDF.")
        return text
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to extract text: {str(e)}")

def analyze_resume_with_gemini(text: str) -> str:
    prompt = (
        "Analyze this resume and provide details in JSON format:\n"
        "{"
        '"overall_score": <numeric value>,\n'
        '"relevance": <numeric value>,\n'
        '"skills_fit": <numeric value>,\n'
        '"experience_match": <numeric value>,\n'
        '"cultural_fit": <numeric value>,\n'
        '"strengths": <list of key strengths>,\n'
        '"weaknesses": <list of key weaknesses>,\n'
        '"missing_elements": <list of missing qualifications>,\n'
        '"recommendations": <list of suggestions>,\n'
        '"candidate_info": { "name": "<candidate name>", "gmail": "<email>", "phone": "<phone>" }\n'
        "}"
        f"\nResume text:\n{text}"
    )

    model = genai.GenerativeModel("gemini-1.5-pro")
    try:
        response = model.generate_content(prompt)
        return response.text.strip()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Gemini API error: {str(e)}")

def parse_gemini_response(response_text: str) -> dict:
    cleaned_response = response_text.strip().strip("```").replace("json", "").strip()
    try:
        return json.loads(cleaned_response)
    except json.JSONDecodeError as e:
        raise HTTPException(status_code=500, detail=f"Parsing error: {str(e)}")

@app.post("/analyze_resume/", tags=["Resume Analysis"])
async def analyze_resume(file: UploadFile = File(...), db: Session = Depends(get_db)):
    if not file.filename.endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are supported")

    try:
        file_path = Path(UPLOAD_FOLDER) / file.filename
        with open(file_path, "wb") as f:
            f.write(file.file.read())

        resume_url = f"http://localhost:8000/resumes/{file.filename}"

        text = extract_text_from_pdf(file_path)
        analyzed_data = analyze_resume_with_gemini(text)
        parsed_data = parse_gemini_response(analyzed_data)

        resume_entry = ResumeData(
            filename=file.filename,
            overall_score=float(parsed_data["overall_score"]),
            relevance=float(parsed_data["relevance"]),
            skills_fit=float(parsed_data["skills_fit"]),
            experience_match=float(parsed_data["experience_match"]),
            cultural_fit=float(parsed_data["cultural_fit"]),
            strengths=", ".join(parsed_data.get("strengths", [])),
            weaknesses=", ".join(parsed_data.get("weaknesses", [])),
            missing_elements=", ".join(parsed_data.get("missing_elements", [])),
            recommendations=", ".join(parsed_data.get("recommendations", [])),
            candidate_name=parsed_data["candidate_info"]["name"],
            candidate_gmail=parsed_data["candidate_info"]["gmail"],
            candidate_phone=parsed_data["candidate_info"]["phone"]
        )

        db.add(resume_entry)
        db.commit()
        db.refresh(resume_entry)

        parsed_data["resume_url"] = resume_url
        return {"message": "Resume analyzed successfully", "data": parsed_data}

    except HTTPException as e:
        db.rollback()
        raise e
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")

@app.get("/resumes/{filename}")
async def get_resume_file(filename: str):
    file_path = Path(UPLOAD_FOLDER) / filename
    if file_path.exists():
        return FileResponse(file_path)
    raise HTTPException(status_code=404, detail="File not found")

# ================== SWAGGER UI SECURITY CONFIGURATION ==================
def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema
    openapi_schema = get_openapi(
        title="Resume Analysis API",
        version="1.0.0",
        description="API for analyzing resumes and generating reports",
        routes=app.routes,
    )
    openapi_schema["components"]["securitySchemes"] = {
        "BearerAuth": {
            "type": "http",
            "scheme": "bearer",
            "bearerFormat": "JWT"
        }
    }
    openapi_schema["security"] = [{"BearerAuth": []}]
    app.openapi_schema = openapi_schema
    return app.openapi_schema

app.openapi = custom_openapi

@app.get("/secure-data", dependencies=[Depends(oauth2_scheme)])
async def secure_data():
    return {"message": "You have access to secure data."}

# ================= DATABASE INITIALIZATION ==================
load_dotenv()
genai.configure(api_key=os.getenv("YOUR_GEMINI_API_KEY"))
Base.metadata.create_all(bind=engine)
