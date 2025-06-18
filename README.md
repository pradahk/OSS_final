# OSS_final
smwu 24 OSS final team project

주제 : 치매 환자를 위한 증상 진행 지연 질문봇

목표: 사용자의 과거 기억에 대한 대화를 기록하고, 저장된 내용 기반으로 힌트를 제공하며 기억 회상을 유도하는 챗봇의 핵심 대화 로직 구현 및 시연

구현 방법 : 개인 정보를 사용해야하므로 사용자는 치매 진단서를 인증해야하고 인증 후, 사용자는 가족 구성원, 이름, 나이, 휴대폰번호 등의 기본 정보를 입력한다. 사용자에게 일부 기간 동안은 주기적으로 질문하면서 사용자가 기억하고 있는 추억 데이터를 최대한 쌓아서 저장하고 있는다. 특정 기간 이후부터는 추억 데이터를 쌓기 위한 새로운 질문도 하면서 중간중간에 이전에 대화했던 내용을 재질문하며 기억해낼 수 있도록 한다. 사용자가 기억을 못하면 라벨링한 키워드를 뽑아 이미지 생성을 하여 시각적 힌트를 제공한다.


----------------------------------------

가상환경 파이썬 및 모듈 버전

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

05.24 / 23:02 / 강다온 / [README] / 모듈 버전 변경사항 저장

---
---

model 학습을 위한 모듈

-CPU 버젼

torch==2.0.1+cpu

torchvision==0.15.2+cpu

-GPU 버전 PyTorch (CUDA 11.8)
torch==2.0.1+cu118

torchvision==0.15.2+cu118

torchaudio==2.0.2+cu118

---

cpu, gpu 상관 없이 공통

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
