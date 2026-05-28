import streamlit as st
import google.generativeai as genai
import gspread
from google.oauth2.service_account import Credentials
import json

st.set_page_config(page_title="B2G EOY Parser Dashboard", layout="wide")
st.title("🦁 Boys 2 Gentlemen LLC — Data Pipeline")
st.write("Upload scanned survey images or PDF packets to automatically populate the LAUSD EOY Database sheets.")

# Safe administrative cloud engine connection keys
API_KEY = st.secrets["GEMINI_API_KEY"]
genai.configure(api_key=API_KEY)
model = genai.GenerativeModel('gemini-2.5-flash')

# Bind to Cloud Google Sheets API Workspace
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
google_creds = json.loads(st.secrets["GOOGLE_CREDENTIALS"])
creds = Credentials.from_service_account_info(google_creds, scopes=scope)
client = gspread.authorize(creds)

# Connect to the targeted workbook sheets
try:
    workbook = client.open("Boys 2 Gentlemen EOY Data")
    sheet_quant = workbook.worksheet("Quantitative Surveys")
    sheet_qual = workbook.worksheet("Qualitative Questions")
except Exception as e:
    st.error(f"Workbook structure link failure: {e}. Check tab names inside Google Sheets.")

# Ingestion Uploader Console
uploaded_files = st.file_uploader("Drop B2G Packets Here (PDF or Loose Photo Arrays)", type=["jpg", "jpeg", "png", "pdf"], accept_multiple_files=True)

if uploaded_files and st.button("🚀 Execute Comprehensive Analysis"):
    progress_bar = st.progress(0)
    
    for idx, file in enumerate(uploaded_files):
        st.write(f"Analyzing structure profile: **{file.name}**...")
        raw_bytes = file.read()
        
        # Super-prompt instructing AI to route data to respective sheets based on structural design rules
        prompt = """
        Analyze this Boys 2 Gentlemen LLC End-of-Year reporting packet completely. 
        First, determine if this document is the '9-Page Quantitative Data Collection Survey' or the '11-Page Qualitative Guide'.
        
        Extract information precisely into a single flat JSON block using the keys below. If a specific checkbox or response field is blank, evaluate it strictly as null.
         Do not include any formatting fences like ```json.
        
        Expected JSON Format structure:
        {
          "form_type": "QUANTITATIVE" or "QUALITATIVE",
          "employee_name": "string value or null",
          "school_site": "string value or null",
          "position_assignment": "string value or null",
          "reporting_period": "string value or null",
          
          # If QUANTITATIVE, extract these matching parameters:
          "q1_morning_arrival": "string value representing checked range choice, or null",
          "q2_afternoon_dismissal": "string value representing checked range choice, or null",
          "q3_bullying_incidents": integer count or null,
          "q4_fights_prevented": integer count or null,
          "q5_safety_incidents_reported": integer count or null,
          "q6_campus_safety_presence": "Yes", "No", "Somewhat", or null,
          "q7_safe_passage_example": "full text summary string or null",
          "q8_tardy_redirected": integer count or null,
          "q9_attendance_followups": integer count or null,
          
          # If QUALITATIVE, map corresponding narrative answers:
          "qual_component": "Safe Passage", "Peace Building", or "Community Development",
          "qual_topic": "string summary of section subheader topic",
          "qual_response": "full comprehensive transcribed reflection answer text block"
        }
        """
        
        try:
            response = model.generate_content([
                {'mime_type': file.type, 'data': raw_bytes},
                prompt
            ])
            
            extracted_json = json.loads(response.text.strip())
            
            # Smart Routeing Logic based on form structural context profile
            if extracted_json.get("form_type") == "QUANTITATIVE":
                sheet_quant.append_row([
                    file.name,
                    extracted_json.get("employee_name"),
                    extracted_json.get("school_site"),
                    extracted_json.get("position_assignment"),
                    extracted_json.get("reporting_period"),
                    extracted_json.get("q1_morning_arrival"),
                    extracted_json.get("q2_afternoon_dismissal"),
                    extracted_json.get("q3_bullying_incidents"),
                    extracted_json.get("q4_fights_prevented"),
                    extracted_json.get("q5_safety_incidents_reported"),
                    extracted_json.get("q6_campus_safety_presence"),
                    extracted_json.get("q7_safe_passage_example"),
                    extracted_json.get("q8_tardy_redirected"),
                    extracted_json.get("q9_attendance_followups")
                ])
                st.success(f"✅ Ingested Quantitative Record Matrix for {file.name}")
                
            else:
                sheet_qual.append_row([
                    file.name,
                    extracted_json.get("qual_component"),
                    extracted_json.get("qual_topic"),
                    extracted_json.get("qual_response")
                ])
                st.success(f"📝 Logged Qualitative Text Reflection Entry for {file.name}")
                
        except Exception as crash_error:
            st.error(f"Error parsing entity stack {file.name}: {crash_error}")
            
        progress_bar.progress((idx + 1) / len(uploaded_files))
        
    st.balloons()
