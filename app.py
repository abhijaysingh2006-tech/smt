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
        intern_name = request.form.get("intern_name") or "Unknown"
        project_name = request.form.get("project_name") or "Project"

        answers = []
        for i, q in enumerate(questions):
            answer = request.form.get(f"q{i}") or ""
            answers.append((q, answer))

        prompt = f"""
Create a professional internship handover document.

Intern Name: {intern_name}
Project Name: {project_name}

Questions and Answers:
"""

        for q, a in answers:
            prompt += f"\nQuestion: {q}\nAnswer: {a}\n"

        # -----------------------------
        # OPENROUTER AI CALL
        # -----------------------------
        # Initialize the OpenAI client pointed at OpenRouter
        client = OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=os.getenv("OPENROUTER_API_KEY"),
        )

        # Make the request to OpenRouter
        response = client.chat.completions.create(
            # OpenRouter uses format: "provider/model-name"
            # You can change this to "anthropic/claude-3-haiku" or "meta-llama/llama-3-8b-instruct"
            model="google/gemini-2.0-flash",
            messages=[
                {"role": "system", "content": "You create clear, professional internship handover documents."},
                {"role": "user", "content": prompt}
            ],
            # Optional but recommended OpenRouter headers
            extra_headers={
                "HTTP-Referer": "http://localhost:5000",  # Change to your Railway URL later
                "X-Title": "Intern Handover App"
            }
        )
        ai_summary = response.choices[0].message.content

        os.makedirs("outputs", exist_ok=True)
        date = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")

        txt_filename = f"outputs/handover_{intern_name}_{date}.txt"
        pdf_filename = f"outputs/handover_{intern_name}_{date}.pdf"

        with open(txt_filename, "w", encoding="utf-8") as f:
            f.write(ai_summary)

        generate_pdf(ai_summary, pdf_filename)

        # Email (safe)
        try:
            send_email(intern_name, pdf_filename)
            email_status = "Email sent successfully."
        except Exception as e:
            email_status = f"Email failed: {str(e)}"

        return f"""
        <h1>✅ Handover Submitted Successfully!</h1>
        <p>Files generated successfully.</p>
        <p>{email_status}</p>
        """

    except Exception as e:
        return f"<h1>❌ Server Error</h1><p>{str(e)}</p>"


def send_email(intern_name, pdf_filename):
    msg = MIMEMultipart()
    msg["Subject"] = f"Handover Document - {intern_name}"
    msg["From"] = EMAIL_ADDRESS
    msg["To"] = RECEIVER_EMAIL

    body = f"Please find the attached handover document for {intern_name}."
    msg.attach(MIMEText(body, "plain"))

    with open(pdf_filename, "rb") as f:
        attach = MIMEApplication(f.read(), _subtype="pdf")
        attach.add_header(
            "Content-Disposition",
            "attachment",
            filename=os.path.basename(pdf_filename)
        )
        msg.attach(attach)

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
        smtp.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
        smtp.send_message(msg)


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
