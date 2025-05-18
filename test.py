import streamlit as st
from io import BytesIO
import fitz  # PyMuPDF

st.title("PDF 업로드 테스트")

uploaded_file = st.file_uploader("PDF 업로드", type=["pdf"])

if uploaded_file:
    try:
        file_bytes = BytesIO(uploaded_file.read())
        doc = fitz.open(stream=file_bytes, filetype="pdf")
        text = ""
        for page in doc:
            text += page.get_text()
        st.success("PDF 텍스트 추출 성공")
        st.text_area("내용 미리보기", text[:1000])
    except Exception as e:
        st.error(f"PDF 처리 중 오류 발생: {e}")
