import streamlit as st
import google.generativeai as genai
import gspread
from google.oauth2.service_account import Credentials
import json
import re

st.set_page_config(page_title="B2G EOY Single-Record Parser", layout="wide")
st.title("🦁 B2G Single-Submission Pipeline")
st.write("Upload ALL pages (JPEGs or PDF) for **ONE person's submission**. The AI will bundle them, read them together, and create ONE row of data.")

# Set up AI and Google Sheets API connections securely
API_KEY = st.secrets["GEMINI_API_KEY"]
genai.configure(api_key=API_KEY)
model = genai.GenerativeModel('gemini-2.5-flash')

scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
google_creds = json.loads(st.secrets["GOOGLE_CREDENTIALS"])
creds = Credentials.from_service_account_info(google_creds, scopes=scope)
client = gspread.authorize(creds)

# Connect to the database workbook
try:
    workbook = client.open("Boys 2 Gentlemen EOY Data")
    sheet_data = workbook.worksheet("END OF YEAR DATA")
    sheet_questions = workbook.worksheet("END OF YEAR QUESTIONS")
except Exception as e:
    st.error(f"Could not connect to Google Sheets: {e}")

# The user uploads the whole packet for ONE person
uploaded_files = st.file_uploader("Drop all pages for ONE submission here", type=["jpg", "jpeg", "png", "pdf"], accept_multiple_files=True)

if uploaded_files and st.button("🚀 Process Submission as ONE Record"):
    with st.spinner("Bundling pages and analyzing the complete packet. This may take 15-20 seconds..."):
        
        # 1. BUNDLE ALL PAGES TOGETHER
        ai_payload = []
        for file in uploaded_files:
            ai_payload.append({'mime_type': file.type, 'data': file.read()})
            
        # 2. THE COMPREHENSIVE PROMPT FOR BOTH DOCUMENTS
        prompt = """
        You are analyzing a complete submission packet consisting of multiple pages for ONE employee.
        Look at all the provided pages together as a single document.
        
        Task 1: Identify which document this is. It will be either:
        - "DATA" (The 9-page End of Year Data form with checkboxes and 46 specific numerical/short answers)
        - "QUESTIONS" (The 11-page End of Year Questions form featuring narrative questions across Safe Passage, Peace Building, and Community Development)
        
        Task 2: Extract the data from across ALL pages into a single flat JSON object.
        If a question is blank, skipped, or missing from the photos, return null. 
        For checkbox questions that ask to "check all that apply", return a single string of the checked items separated by commas.
        Transcribe all handwritten responses exactly as written.
        
        Expected JSON Format:
        {
          "document_type": "DATA" or "QUESTIONS",
          "employee_name": "string or null",
          "school_site": "string or null",
          "position_assignment": "string or null",
          "reporting_period": "string or null",
          
          # IF DOCUMENT TYPE IS "DATA", FILL THESE 46 FIELDS (Otherwise null):
          "data_q1": "string or null", "data_q2": "string or null", "data_q3": integer or null, "data_q4": integer or null, "data_q5": integer or null,
          "data_q6": "string or null", "data_q7": "string or null", "data_q8": integer or null, "data_q9": integer or null, "data_q10": integer or null,
          "data_q11": integer or null, "data_q12": "string or null", "data_q13": "string or null", "data_q14": integer or null, "data_q15": "string or null",
          "data_q16": integer or null, "data_q17": "string or null", "data_q18": integer or null, "data_q19": integer or null, "data_q20": "string or null",
          "data_q21": "string or null", "data_q22": integer or null, "data_q23": integer or null, "data_q24": "string or null", "data_q25": "string or null",
          "data_q26": integer or null, "data_q27": "string or null", "data_q28": "string or null", "data_q29": integer or null, "data_q30": integer or null,
          "data_q31": integer or null, "data_q32": integer or null, "data_q33": "string or null", "data_q34": "string or null", "data_q35": integer or null,
          "data_q36": integer or null, "data_q37": integer or null, "data_q38": integer or null, "data_q39": "string or null", "data_q40": integer or null,
          "data_q41": "string or null", "data_q42": "string or null", "data_q43": "string or null", "data_q44": "string or null", "data_q45": "string or null",
          "data_q46": "string or null",
          
          # IF DOCUMENT TYPE IS "QUESTIONS", FILL THESE 54 FIELDS (Otherwise null):
          "sp_1a": "string or null", "sp_1b": "string or null", "sp_1c": "string or null", "sp_2a": "string or null", "sp_2b": "string or null", "sp_2c": "string or null", "sp_3a": "string or null", "sp_3b": "string or null", "sp_4a": "string or null", "sp_4b": "string or null", "sp_4c": "string or null", "sp_4d": "string or null", "sp_4e": "string or null", "sp_4f": "string or null", "sp_5a": "string or null", "sp_5b": "string or null", "sp_6": "string or null",
          "pb_1a": "string or null", "pb_1b": "string or null", "pb_1c": "string or null", "pb_1d": "string or null", "pb_2a": "string or null", "pb_2b": "string or null", "pb_3a": "string or null", "pb_3b": "string or null", "pb_4a": "string or null", "pb_4b": "string or null", "pb_4c": "string or null", "pb_4d": "string or null", "pb_4e": "string or null", "pb_5a": "string or null", "pb_5b": "string or null", "pb_5c": "string or null", "pb_5d": "string or null", "pb_5e": "string or null", "pb_6": "string or null", "pb_7a": "string or null", "pb_7b": "string or null", "pb_8a": "string or null", "pb_8b": "string or null",
          "comm_1": "string or null", "comm_2a": "string or null", "comm_2b": "string or null", "comm_3a": "string or null", "comm_3b": "string or null", "comm_4a": "string or null", "comm_4b": "string or null", "comm_5a": "string or null", "comm_5b": "string or null", "comm_5c": "string or null", "comm_5d": "string or null", "comm_5e": "string or null", "comm_6": "string or null"
        }
        """
        
        ai_payload.append(prompt)
        
        try:
            # Send the entire bundled payload to the AI at once
            response = model.generate_content(ai_payload)
            
            # Clean the output to ensure it only reads the JSON bracket data
            text_response = response.text
            json_match = re.search(r'\{.*\}', text_response, re.DOTALL)
            
            if json_match:
                data = json.loads(json_match.group(0))
                
                # 3. WRITE EXACTLY ONE MASSIVE ROW TO THE CORRECT SHEET
                if data.get("document_type") == "DATA":
                    sheet_data.append_row([
                        data.get("employee_name"), data.get("school_site"), data.get("position_assignment"), data.get("reporting_period"),
                        data.get("data_q1"), data.get("data_q2"), data.get("data_q3"), data.get("data_q4"), data.get("data_q5"), 
                        data.get("data_q6"), data.get("data_q7"), data.get("data_q8"), data.get("data_q9"), data.get("data_q10"), 
                        data.get("data_q11"), data.get("data_q12"), data.get("data_q13"), data.get("data_q14"), data.get("data_q15"), 
                        data.get("data_q16"), data.get("data_q17"), data.get("data_q18"), data.get("data_q19"), data.get("data_q20"), 
                        data.get("data_q21"), data.get("data_q22"), data.get("data_q23"), data.get("data_q24"), data.get("data_q25"), 
                        data.get("data_q26"), data.get("data_q27"), data.get("data_q28"), data.get("data_q29"), data.get("data_q30"), 
                        data.get("data_q31"), data.get("data_q32"), data.get("data_q33"), data.get("data_q34"), data.get("data_q35"), 
                        data.get("data_q36"), data.get("data_q37"), data.get("data_q38"), data.get("data_q39"), data.get("data_q40"), 
                        data.get("data_q41"), data.get("data_q42"), data.get("data_q43"), data.get("data_q44"), data.get("data_q45"), 
                        data.get("data_q46")
                    ])
                    st.success("✅ Successfully wrote ONE complete row of 50 data points to the 'DATA' sheet.")
                    
                else:
                    filename = uploaded_files[0].name if uploaded_files else "Unknown"
                    sheet_questions.append_row([
                        filename,
                        data.get("sp_1a"), data.get("sp_1b"), data.get("sp_1c"), data.get("sp_2a"), data.get("sp_2b"), data.get("sp_2c"), data.get("sp_3a"), data.get("sp_3b"), data.get("sp_4a"), data.get("sp_4b"), data.get("sp_4c"), data.get("sp_4d"), data.get("sp_4e"), data.get("sp_4f"), data.get("sp_5a"), data.get("sp_5b"), data.get("sp_6"),
                        data.get("pb_1a"), data.get("pb_1b"), data.get("pb_1c"), data.get("pb_1d"), data.get("pb_2a"), data.get("pb_2b"), data.get("pb_3a"), data.get("pb_3b"), data.get("pb_4a"), data.get("pb_4b"), data.get("pb_4c"), data.get("pb_4d"), data.get("pb_4e"), data.get("pb_5a"), data.get("pb_5b"), data.get("pb_5c"), data.get("pb_5d"), data.get("pb_5e"), data.get("pb_6"), data.get("pb_7a"), data.get("pb_7b"), data.get("pb_8a"), data.get("pb_8b"),
                        data.get("comm_1"), data.get("comm_2a"), data.get("comm_2b"), data.get("comm_3a"), data.get("comm_3b"), data.get("comm_4a"), data.get("comm_4b"), data.get("comm_5a"), data.get("comm_5b"), data.get("comm_5c"), data.get("comm_5d"), data.get("comm_5e"), data.get("comm_6")
                    ])
                    st.success("📝 Successfully wrote ONE complete row of 54 data points to the 'QUESTIONS' sheet.")
            else:
                 st.error("Failed to extract readable JSON from the AI response. Please ensure photos are legible.")
                 
        except Exception as crash_error:
            st.error(f"Error processing packet: {crash_error}")
            
    st.balloons()
