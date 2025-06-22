# OSS_final
smwu 24 OSS final team project

Topic: Question Bot for Delaying Symptom Progression in Dementia Patients

Objective: Implement and demonstrate the core conversational logic of a chatbot that records conversations about users' past memories, provides hints based on stored content, and induces memory recall.

Implementation Method: Since personal information must be used, users must authenticate with a dementia diagnosis certificate. After authentication, users input basic information such as family members, names, ages, phone numbers, etc. The system periodically asks users questions for a certain period to accumulate and store as much memory data as possible about what users remember. After a specific period, the system continues asking new questions to build memory data while intermittently re-questioning previously discussed content to help users recall memories. When users cannot remember, the system extracts labeled keywords and generates images to provide visual hints.

---

## How to set up and install

1. To install this project, clone the OSS_final repository

2. Install `requirements.txt`for module install

   `pip install -r requirements.txt`

3. Run `improved_klue_training_keywordLimit.py` with anaconda virtual environement. So that make the model for keyword

   ![모델 학습 결과](https://github.com/pradahk/OSS_final/blob/main/model_final_result.png)

   ```bash
   conda activate your_environment
   cd your_directory
   python extracting.improved_klue_training_keywordLimit.py

5. Run `main.py` in `OSS_final\main\UI` for streamlit UI.

   `streamlit run main.py`
   
---

## Examples of usage and execution results

1. When you open streamlit UI, you can meet first page of UI

  (그냥 첫 페이지)

2. On the side bar, you can upload diagnosis by PDF. Then, text in the diagnosis will be extracted.

  (진단서 업로드 완료 캡쳐)

3. Next, you can now have real-chat. You will meet two questions per day when your diagnosis date is under 30 days since current date.

   (기억 회상 단계 질문에 답변 입력한 화면 캡쳐)

4. When your diagnosis date is 30 days upper, you will meet memory-check phase. There, you can check your past memory with image and answer new questions.

   (기억 점검 단계에서 기억 점검 화면 캡쳐)

5. We've made 300 and more questions. If you done all questions, program will be end. Congratulations!

---

## License of this project

Please check `LICENSE` file.

---

## How to contribute to this project

You are welcome to open issues or submit PRs to improve this app, however, please note that we may not review all suggestions.

## Branch Structure

- Data Processing Branches

`KLUE_Labeling`

Purpose: BIO labeling data generation for KLUE-BERT model training

Function: Assign B-KEY/I-KEY/O labels to tokenized morpheme .json files

Key Files:
 KLUE_tokenized_answers#_labeled.json - Completed labeling data

`SelfLabelling`

Purpose: Manual labeling dataset

Function: Upload original answers and labeled answers

Key Files:
 example#_custom_token.csv - Labeled answer files


`gptapiTokenizing`

Purpose: Automatic tokenization based on GPT API

Function: Morphological analysis using GPT-3.5-turbo

Key Files:
 api_tokenizer_for github.py - GPT API calls
 example#_custom_token.csv - Morphologically tokenized example answer data


- Model Training Branches
  
`KLUE_train`

Purpose: KLUE-BERT model training and experimentation

Function: Model keyword extraction fine-tuning

Key Files:
 improved_klue_training_keywordLimit.py - Final model training file used


`model`

Purpose: Fine-tuning specialized for KLUE-BERT keyword extraction

Function:
 Tokenization process explanation for example answer data
 Validation process through test training
 
Key Files:
 klue_model_training.py - Model fine-tuning draft
 klue_bert_reprocessing - Convert KoBERT data to KLUE-BERT

`KobertTokenizing`

Purpose: Tokenization files for KoBERT model training

Function: KoBERT-specific tokenization and training

Key Files:
 tokenized_answers#.json - Tokenized answer files


- Application Branches

`streamlitUI_withModel`
Purpose: Final version code of the project
Features:
  - Automated Medical Report Analysis: 
    - PDF medical report upload and automatic information extraction
    - Automatic parsing of patient basic information (name, date of birth, diagnosis date)
    - Dementia diagnosis verification
  - Phased System:
    - Initial Recall Phase: 
      - Maximum of 2 new questions per day
      - Questions about personal memories and experiences
      - Secure storage of responses in database
    - Memory Check Phase: 
      - 1 new question + 1 memory check per day
      - Comparative analysis between past answers and current memory
      - Similarity measurement based on KoBERT model
  - AI Image Generation: 
    - OpenAI DALL-E powered memory-assist image generation for forgotten memories
    - Automatic keyword extraction from responses using model
    - Visual cue support for memory recovery
  - Progress Tracking: 
    - Daily/cumulative activity status monitoring
    - Memory check success rate statistics
    - Reusable question management system

`streamlitUI`
Purpose: Basic UI implementation version
Features:
 Automated medical report analysis
 Phased system
 AI image generation
 Progress tracking

`streamlitUI_수정`
Purpose: Code modifications uploaded during model integration process
Features: 
 Error fixes and optimization work that occurred during model integration
