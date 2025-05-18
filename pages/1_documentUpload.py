import streamlit as st
from datetime import datetime
import fitz  # PyMuPDF
import re

st.header("📄 1단계: 진단서 업로드")

uploaded_file = st.file_uploader("PDF 진단서를 업로드하세요", type=["pdf"])

if 'user_info' not in st.session_state:
    st.session_state.user_info = {}

def extract_text_from_pdf(pdf_file):
    text = ""
    with fitz.open(stream=pdf_file.read(), filetype="pdf") as doc:
        for page in doc:
            text += page.get_text()
    return text

def parse_info(text):
    info = {}
    # info['이름'] = re.search(r'이름[:：]?\s*([가-힣]+)', text).group(1) if re.search(r'이름[:：]?\s*([가-힣]+)', text) else "미상"
    name_match = re.search(r'(이름|성명)\s*[:：]?\s*([가-힣]{2,4})', text)
    info['이름'] = name_match.group(2) if name_match else "미상"

    info['성별'] = re.search(r'성별[:：]?\s*(남|여)', text).group(1) if re.search(r'성별[:：]?\s*(남|여)', text) else "미상"
    
    dob_raw = re.search(r'생년월일[:：]?\s*([\d]{4}[.\-\s년]?[\d]{1,2}[.\-\s월]?[\d]{1,2}[일]?)', text)
    if dob_raw:
        dob = re.sub(r'[^\d]', '', dob_raw.group(1))
        info['생년월일'] = datetime.strptime(dob, "%Y%m%d").date()
        today = datetime.today().date()
        info['나이'] = today.year - info['생년월일'].year - ((today.month, today.day) < (info['생년월일'].month, info['생년월일'].day))

    diagnosis_raw = re.search(r'진단일[:：]?\s*([\d]{4}[.\-\s년]?[\d]{1,2}[.\-\s월]?[\d]{1,2}[일]?)', text)
    if diagnosis_raw:
        diagnosis = re.sub(r'[^\d]', '', diagnosis_raw.group(1))
        info['진단일'] = datetime.strptime(diagnosis, "%Y%m%d").date()

    disease = re.search(r'(알츠하이머[^\n]*)', text)
    info['병명'] = disease.group(1) if disease else "정보 없음"
    info['치매 여부'] = "✅ 치매 환자입니다" if disease else "❌ 치매 여부 불확실"
    
    return info

if uploaded_file:
    with st.spinner("진단서 분석 중..."):
        raw_text = extract_text_from_pdf(uploaded_file)
        parsed_info = parse_info(raw_text)
        st.session_state.user_info.update(parsed_info)
        st.success("사용자 정보가 추출되었습니다.")

if st.session_state.user_info:
    st.subheader("👤 사용자 정보")
    for key, value in st.session_state.user_info.items():
        st.write(f"- **{key}**: {value}")
