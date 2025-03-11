
import json
import os
import pdfplumber
import google.generativeai as genai
from dotenv import load_dotenv
from fastapi import FastAPI, UploadFile, File, HTTPException, Depends
from sqlalchemy.orm import Session
from database import get_db, engine, Base
from models import ResumeData

# Load environment variables
load_dotenv()

# Initialize FastAPI app
app = FastAPI()

genai.configure(api_key=os.getenv("YOUR_GEMINI_API_KEY"))

# Initialize Database Tables
Base.metadata.create_all(bind=engine)

# Extract text from PDF file
def extract_text_from_pdf(pdf_file) -> str:
    try:
        with pdfplumber.open(pdf_file) as pdf:
            text = " ".join(page.extract_text() or "" for page in pdf.pages)
        if not text.strip():
            raise ValueError("No readable text found in the PDF.")
        return text
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to extract text: {str(e)}")

# Analyze resume with Gemini API
def analyze_resume_with_gemini(text: str) -> str:
    prompt = (
        "Analyze this resume and provide the following details in JSON format:\n"
        "{"
        '"overall_score": <numeric value between 0 and 100>,\n'
        '"relevance": <numeric score between 0 and 10>,\n'
        '"skills_fit": <numeric score between 0 and 10>,\n'
        '"experience_match": <numeric score between 0 and 10>,\n'
        '"cultural_fit": <numeric score between 0 and 10>,\n'
        '"strengths": <list of key strengths>,\n'
        '"weaknesses": <list of key weaknesses or gaps>,\n'
        '"missing_elements": <list of key missing qualifications or experiences>,\n'
        '"recommendations": <list of suggestions for improvement>,\n'
        '"candidate_info": {'
        '    "name": "<candidate name>",\n'
        '    "gmail": "<candidate email>",\n'
        '    "phone": "<candidate phone number>"\n'
        '  }'
        "}"
        f"\nResume text:\n{text}"
    )

    model = genai.GenerativeModel("gemini-1.5-pro")
    try:
        response = model.generate_content(prompt)
        print("🔍 Gemini API Response:", response.text)  # Debugging output
        return response.text.strip()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Gemini API error: {str(e)}")

# Parse Gemini response into JSON
def parse_gemini_response(response_text: str) -> dict:
    cleaned_response = response_text.strip().strip("```").replace("json", "").strip()

    try:
        parsed_data = json.loads(cleaned_response)
        return parsed_data
    except json.JSONDecodeError as e:
        raise HTTPException(status_code=500, detail=f"Parsing error: {str(e)}")

@app.post("/analyze_resume/")
async def analyze_resume(file: UploadFile = File(...), db: Session = Depends(get_db)):
    if not file.filename.endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are supported")

    try:
        text = extract_text_from_pdf(file.file)
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

        return {"message": "Resume analyzed successfully", "data": parsed_data}

    except HTTPException as e:
        db.rollback()
        raise e
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred: {str(e)}")
