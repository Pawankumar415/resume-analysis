from fpdf import FPDF
from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import FileResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session
from database import get_db
from models import User, InterviewReport
import os

router = APIRouter()

class ReportData(BaseModel):
    score: int
    strengths: list[str]
    weaknesses: list[str]

class PDFReport(FPDF):
    def header(self):
        self.set_font('Arial', 'B', 16)
        self.cell(0, 10, 'Interview Report', ln=True, align='C')
        self.ln(10)

    def chapter_title(self, title):
        self.set_font('Arial', 'B', 14)
        self.cell(0, 10, title, ln=True)
        self.ln(5)

    def chapter_body(self, body):
        self.set_font('Arial', '', 12)
        self.multi_cell(0, 10, body)
        self.ln()

@router.post("/generate/{user_id}")
async def generate_report(user_id: int, report_data: ReportData, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Check subscription or limit attempts
    if not user.is_subscribed:
        if user.remaining_attempts is None or user.remaining_attempts <= 0:
            raise HTTPException(status_code=403, detail="Free limit reached. Please subscribe.")
        user.remaining_attempts -= 1
        db.commit()

    # Create PDF Report
    pdf = PDFReport()
    pdf.add_page()
    pdf.chapter_title(f"Interview Report for {user.username}")
    pdf.chapter_body(f"Score: {report_data.score}")
    pdf.chapter_body(f"Strengths: {', '.join(report_data.strengths)}")
    pdf.chapter_body(f"Weaknesses: {', '.join(report_data.weaknesses)}")

    # Save PDF file
    report_dir = os.path.join(os.getcwd(), "uploaded_reports")
    os.makedirs(report_dir, exist_ok=True)
    report_path = os.path.join(report_dir, f"{user.username}_report.pdf")

    try:
        pdf.output(report_path)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating PDF: {str(e)}")

    # Save report in the database
    report_entry = InterviewReport(user_id=user.id, file_path=report_path)
    db.add(report_entry)
    db.commit()

    return {"message": "Report generated successfully.", "report_url": report_path}

@router.get("/download/{user_id}")
async def download_report(user_id: int, db: Session = Depends(get_db)):
    report = db.query(InterviewReport).filter(InterviewReport.user_id == user_id).first()
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")

    return FileResponse(report.file_path, headers={"Content-Disposition": "attachment"})
