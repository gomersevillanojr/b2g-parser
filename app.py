import streamlit as st
import google.generativeai as genai
import gspread
from google.oauth2.service_account import Credentials
import json
import re # We added this tool to help find the JSON

st.set_page_config(page_title="B2G EOY Parser Dashboard", layout="wide")
st.title("🦁 Boys 2 Gentlemen LLC — Data Pipeline")
st.write("Upload scanned survey images or PDF packets to automatically populate the LAUSD EOY Database sheets.")

API_KEY = st.secrets["GEMINI_API_KEY"]
genai.configure(api_key=API_KEY)
model = genai.GenerativeModel('gemini-2.5-flash')

scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
google_creds = json.loads(st.secrets["GOOGLE_CREDENTIALS"])
creds = Credentials.from_service_account_info(google_creds, scopes=scope)
client = gspread.authorize(creds)

try:
    workbook = client.open("Boys 2 Gentlemen EOY Data")
    sheet_quant = workbook.worksheet("Quantitative Surveys")
    sheet_qual = workbook.worksheet("Qualitative Questions")
except Exception as e:
    st.error(f"Workbook structure link failure: {e}. Check tab names inside Google Sheets.")

uploaded_files = st.file_uploader("Drop B2G Packets Here (PDF or Loose Photo Arrays)", type=["jpg", "jpeg", "png", "pdf"], accept_multiple_files=True)

if uploaded_files and st.button("🚀 Execute Comprehensive Analysis"):
    progress_bar = st.progress(0)
    
    for idx, file in enumerate(uploaded_files):
        st.write(f"Analyzing structure profile: **{file.name}**...")
        raw_bytes = file.read()
        
        prompt = """
        Analyze this Boys 2 Gentlemen LLC End-of-Year reporting packet completely. 
        Determine if this document is the '9-Page Quantitative Data Collection Survey' or the '11-Page Qualitative Guide'.
        
        Extract information precisely into a single flat JSON block.
        Return ONLY valid JSON. No conversational text.
        
        Expected JSON Format structure:
        {
          "form_type": "QUANTITATIVE" or "QUALITATIVE",
          "employee_name": "string value or null",
          "school_site": "string value or null",
          "position_assignment": "string value or null",
          "reporting_period": "string value or null",
          "q1_morning_arrival": "string value representing checked range choice, or null",
          "q2_afternoon_dismissal": "string value representing checked range choice, or null",
          "q3_bullying_incidents": integer count or null,
          "q4_fights_prevented": integer count or null,
          "q5_safety_incidents_reported": integer count or null,
          "q6_campus_safety_presence": "Yes", "No", "Somewhat", or null,
          "q7_safe_passage_example": "full text summary string or null",
          "q8_tardy_redirected": integer count or null,
          "q9_attendance_followups": integer count or null,
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
            
            # --- THE FIX IS HERE ---
            # We strip away everything that isn't inside the JSON brackets
            text_response = response.text
            json_match = re.search(r'\{.*\}', text_response, re.DOTALL)
            
            if json_match:
                clean_json_string = json_match.group(0)
                extracted_json = json.loads(clean_json_string)
            else:
                 # If we still can't find JSON, we skip this photo and warn you, but keep the app running.
                 st.warning(f"Could not read the data format for {file.name}. Moving to the next file.")
                 continue 
            # -----------------------

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
                st.success(f"✅ Ingested Quantitative Record for {file.name}")
                
            else:
                sheet_qual.append_row([
                    file.name,
                    extracted_json.get("qual_component"),
                    extracted_json.get("qual_topic"),
                    extracted_json.get("qual_response")
                ])
                st.success(f"📝 Logged Qualitative Entry for {file.name}")
                
        except Exception as crash_error:
             # This prevents one bad photo from crashing the whole batch
            st.error(f"Error processing {file.name}: {crash_error}")
            
        progress_bar.progress((idx + 1) / len(uploaded_files))
        
    st.balloons()
