# OSS_final
smwu 24 OSS final team project

Topic: Question Bot for Delaying Symptom Progression in Dementia Patients

Objective: Implement and demonstrate the core conversational logic of a chatbot that records conversations about users' past memories, provides hints based on stored content, and induces memory recall.

Implementation Method: Since personal information must be used, users must authenticate with a dementia diagnosis certificate. After authentication, users input basic information such as family members, names, ages, phone numbers, etc. The system periodically asks users questions for a certain period to accumulate and store as much memory data as possible about what users remember. After a specific period, the system continues asking new questions to build memory data while intermittently re-questioning previously discussed content to help users recall memories. When users cannot remember, the system extracts labeled keywords and generates images to provide visual hints.

---

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

----------------------------------------

<Python and Module Versions for Virtual Environments>

python              3.10.16

accelerate          1.7.0  > 0.5.0

datasets            3.6.0  > 1.18.0

huggingface-hub     0.32.0  > 0.32.0

kobert-transformers 0.6.0  > 0.6.0

matplotlib          3.10.3  > 3.10.3

numpy               2.2.6  > 2.2.6

tokenizers          0.21.1  > 0.11.6

torch               2.7.0  > 2.7.0

transformers        4.52.3  > 4.18.0

sentencepiece       0.2.0  > 0.1.96

---
---

<Modules for model learning>

-CPU version

torch==2.0.1+cpu

torchvision==0.15.2+cpu

-GPU version PyTorch (CUDA 11.8)
torch==2.0.1+cu118

torchvision==0.15.2+cu118

torchaudio==2.0.2+cu118

---

<Common version>

transformers==4.30.2

scikit-learn==1.6.1

huggingface-hub==0.33.0

pandas==1.5.3

numpy==1.24.3

scipy==1.13.1

matplotlib==3.9.2

seaborn==0.13.2

streamlit

requests==2.28.1

tokenizers==0.13.3

safetensors==0.5.3

tqdm==4.67.1

pyyaml==6.0.2

regex==2024.11.6

filelock==3.13.1

fsspec==2025.5.1

sympy==1.13.3

mpmath==1.3.0

networkx==3.2.1

jinja2==3.1.4

markupsafe==2.1.5
