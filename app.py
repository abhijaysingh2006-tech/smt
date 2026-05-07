from flask import Flask, render_template, request
from google import genai
from google.genai import types
from dotenv import load_dotenv
from datetime import datetime
import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication
from fpdf import FPDF

# Load environment variables
load_dotenv()

app = Flask(__name__)

<<<<<<< Updated upstream
# Initialize the NEW Gemini Client
# It automatically picks up the GEMINI_API_KEY from your environment variables
client = genai.Client()
=======
# Configure Gemini API
genai.configure(api_key=os.getenv("OPENROUTER_API_KEY"))

# Initialize the model using the current supported version
model = genai.GenerativeModel(
    model_name="gemini-2.5-flash",
    system_instruction="You create professional project handover documents."
)
>>>>>>> Stashed changes

# Email config
EMAIL_ADDRESS = os.getenv("EMAIL_ADDRESS")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")
RECEIVER_EMAIL = os.getenv("RECEIVER_EMAIL")

questions = [
    "What were you mainly working on?",
    "What important decisions were made and why?",
    "What tools or websites were used?",
    "What logins or accounts are needed?",
    "What bugs or problems happened often?",
    "What unfinished work remains?",
    "What files or folders are important?",
    "Who should the next intern contact?",
    "What should the next intern learn first?",
    "Any tips, warnings, or shortcuts?"
]


def generate_pdf(content, filename):
    """Helper function to create a PDF from text"""
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)

    safe_content = content.encode('latin-1', 'replace').decode('latin-1')
    pdf.multi_cell(0, 10, txt=safe_content)
    pdf.output(filename)


@app.route("/")
def home():
    return render_template("index.html", questions=questions)


@app.route("/submit", methods=["POST"])
def submit():
    intern_name = request.form.get("intern_name")
    project_name = request.form.get("project_name")

    answers = []

    for i, q in enumerate(questions):
        answer = request.form.get(f"q{i}")
        answers.append((q, answer))

    # Build AI prompt
    prompt = f"""
    Create a professional internship handover summary.

    Intern Name: {intern_name}
    Project Name: {project_name}

    Questions and Answers:
    """

    for q, a in answers:
        prompt += f"\nQuestion: {q}\nAnswer: {a}\n"

    # AI Summary using the NEW Gemini SDK
    response = client.models.generate_content(
        model='gemini-2.5-flash',
        contents=prompt,
        config=types.GenerateContentConfig(
            system_instruction="You create professional project handover documents.",
        ),
    )
    ai_summary = response.text

    # Ensure the outputs directory exists
    os.makedirs("outputs", exist_ok=True)
    date = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")

    # 1. Save Text File
    txt_filename = f"outputs/handover_{intern_name}_{date}.txt"
    with open(txt_filename, "w", encoding="utf-8") as file:
        file.write(ai_summary)

    # 2. Save PDF File
    pdf_filename = f"outputs/handover_{intern_name}_{date}.pdf"
    generate_pdf(ai_summary, pdf_filename)

    # 3. Send Email with PDF Attachment
    try:
        send_email(ai_summary, intern_name, pdf_filename)
        email_status = "Email sent successfully with PDF attached."
    except Exception as e:
        email_status = f"Failed to send email: {e}"

    return f"""
    <h1>✅ Handover Submitted Successfully!</h1>
    <p>Document saved to outputs folder as TXT and PDF.</p>
    <p>{email_status}</p>
    """


def send_email(content, intern_name, pdf_filename):
    subject = f"Handover Document - {intern_name}"

    msg = MIMEMultipart()
    msg["Subject"] = subject
    msg["From"] = EMAIL_ADDRESS
    msg["To"] = RECEIVER_EMAIL

    body = f"Please find the attached handover document for {intern_name}.\n\n"
    msg.attach(MIMEText(body, "plain"))

    with open(pdf_filename, "rb") as f:
        attach = MIMEApplication(f.read(), _subtype="pdf")
        attach.add_header('Content-Disposition', 'attachment',
                          filename=os.path.basename(pdf_filename))
        msg.attach(attach)

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
        smtp.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
        smtp.send_message(msg)


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
