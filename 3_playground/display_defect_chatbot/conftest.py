# conftest.py
import sys
import os

# ai_server 패키지를 import 가능하게 경로 추가
# __file__은 display_defect_chatbot/conftest.py이므로 dirname이 곧 패키지 루트
sys.path.insert(0, os.path.dirname(__file__))
