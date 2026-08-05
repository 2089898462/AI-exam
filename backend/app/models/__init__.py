"""
数据模型统一导出
"""
from app.models.user import User
from app.models.exam import Exam
from app.models.question import Question
from app.models.exam_record import ExamRecord
from app.models.answer_record import AnswerRecord
from app.models.ai_report import AiReport

__all__ = [
    "User",
    "Exam",
    "Question",
    "ExamRecord",
    "AnswerRecord",
    "AiReport",
]