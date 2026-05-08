from flask import Flask, render_template, request
from openai import OpenAI
from dotenv import load_dotenv
from datetime import datetime
import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication
from fpdf import FPDF

# Load env
load_dotenv()

app = Flask(__name__)

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
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    safe_content = content.encode("latin-1", "replace").decode("latin-1")
    pdf.multi_cell(0, 10, txt=safe_content)
    pdf.output(filename)


@app.route("/")
def home():
    return render_template("index.html", questions=questions)


@app.route("/submit", methods=["POST"])
def submit():
    try:
        # Get Key and check if it exists
        api_key = os.getenv("OPENROUTER_API_KEY")
        if not api_key:
            return "<h1>❌ Configuration Error</h1><p>API Key is missing from Railway Variables.</p>"

        intern_name = request.form.get("intern_name") or "Unknown"
        project_name = request.form.get("project_name") or "Project"

        answers = []
        for i, q in enumerate(questions):
            answer = request.form.get(f"q{i}") or ""
            answers.append((q, answer))

        prompt = f"Create a professional internship handover document.\nIntern Name: {intern_name}\nProject Name: {project_name}\nQuestions and Answers:\n"
        for q, a in answers:
            prompt += f"\nQuestion: {q}\nAnswer: {a}\n"

        # -----------------------------
        # OPENROUTER AI CALL (FORCED)
        # -----------------------------
        # Initialize inside the route to ensure it catches the env variable
        client = OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=api_key,
        )

        response = client.chat.completions.create(
            model="openrouter/free",
            messages=[
                {"role": "system", "content": "You create clear, professional internship handover documents."},
                {"role": "user", "content": prompt}
            ],
            extra_headers={
                "HTTP-Referer": "https://railway.app",
                "X-Title": "Intern Handover App"
            },
            timeout=60.0  # Don't wait forever
        )
        ai_summary = response.choices[0].message.content

        # Create outputs directory
        os.makedirs("outputs", exist_ok=True)
        date = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        pdf_filename = f"outputs/handover_{intern_name}_{date}.pdf"

        generate_pdf(ai_summary, pdf_filename)

        # Email
        try:
            send_email(intern_name, pdf_filename)
            email_status = "Email sent successfully."
        except Exception as e:
            email_status = f"Email failed: {str(e)}"

        return f"""
        <h1>✅ Handover Submitted Successfully!</h1>
        <p>AI document generated successfully.</p>
        <p><strong>{email_status}</strong></p>
        <a href='/'>Submit another</a>
        """

    except Exception as e:
        return f"<h1>❌ AI Error</h1><p>{str(e)}</p>"


def send_email(intern_name, pdf_filename):
    msg = MIMEMultipart()
    msg["Subject"] = f"Handover Document - {intern_name}"
    msg["From"] = EMAIL_ADDRESS
    msg["To"] = RECEIVER_EMAIL

    body = f"Please find the attached handover document for {intern_name}."
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
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
