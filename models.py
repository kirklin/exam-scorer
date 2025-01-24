from typing import List, Optional
from pydantic import BaseModel

class QuestionPart(BaseModel):
    number: int
    keywords: Optional[List[str]] = None  # 每个空的关键词列表
    keyword: Optional[str] = None  # 单个关键词
    note: Optional[str] = None  # 评分说明
    blanks_count: Optional[int] = 1  # 该小题的空格数量，默认为1

class Question(BaseModel):
    number: int
    parts: List[QuestionPart]

class AnswerSheet(BaseModel):
    score: int
    questions: List[Question]

class StudentAnswer(BaseModel):
    question_number: int
    part_number: int
    blank_number: int  # 在同一小题中的第几个空
    content: str
    confidence: float  # 模型对识别结果的置信度
    is_crossed_out: bool  # 是否被划掉
    is_blurry: bool  # 是否模糊不清 
