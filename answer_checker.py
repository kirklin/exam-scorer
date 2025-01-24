from typing import List, Tuple, Dict
from models import AnswerSheet, StudentAnswer

class AnswerChecker:
    def __init__(self, standard_answer: AnswerSheet):
        self.standard_answer = standard_answer

    def get_standard_answer_text(self, part, blank_number: int) -> str:
        """获取标准答案文本"""
        if part.keywords and blank_number <= len(part.keywords):
            return part.keywords[blank_number - 1]
        elif part.keyword:
            base_answer = part.keyword
            if part.note and "也可得分" in part.note:
                # 提取"也可得分"的答案
                alt_answers = []
                for ans in part.note.split("'"):
                    ans = ans.strip()
                    if ans and "也可得分" not in ans and "不得分" not in ans:
                        alt_answers.append(ans)
                if alt_answers:
                    base_answer += f"（或 {alt_answers[0]}）"
            return base_answer
        return "未知"

    def check_answer_correctness(self, student_answer: str, part, blank_number: int) -> bool:
        """检查答案是否正确"""
        if part.keywords and blank_number <= len(part.keywords):
            # 检查特定空的关键词
            keyword = part.keywords[blank_number - 1]
            return keyword.lower() in student_answer.lower()
        elif part.keyword:
            # 如果只有一个关键词
            answer_content = student_answer.lower()
            keyword = part.keyword.lower()
            is_correct = keyword in answer_content
            
            # 检查特殊说明
            if part.note:
                if "不得分" in part.note and any(
                    ans.strip("'").lower() in answer_content
                    for ans in part.note.split("'")
                    if ans.strip("'") and "不得分" in part.note
                ):
                    return False
                
                if "也可得分" in part.note and not is_correct:
                    alt_answers = [
                        ans.strip("'") for ans in part.note.split("'")
                        if ans.strip("'") and "也可得分" not in ans
                    ]
                    is_correct = any(
                        alt.lower() in answer_content
                        for alt in alt_answers
                    )
            return is_correct
        return False

    def check_answer(self, student_answers: List[StudentAnswer]) -> Tuple[float, List[str]]:
        """
        检查学生答案，返回得分和评价意见
        
        Args:
            student_answers: 学生答案列表
            
        Returns:
            Tuple[float, List[str]]: (得分, 评价意见列表)
        """
        total_score = 0
        total_possible_score = 0  # 添加总分变量
        comments = []
        
        # 按题号和小题号分组处理学生答案
        for question in self.standard_answer.questions:
            question_answers = [
                ans for ans in student_answers 
                if ans.question_number == question.number
            ]
            
            # 按小题号分组
            answers_by_part: Dict[int, List[StudentAnswer]] = {}
            for ans in question_answers:
                if ans.part_number not in answers_by_part:
                    answers_by_part[ans.part_number] = []
                answers_by_part[ans.part_number].append(ans)
            
            # 检查每个小题
            for part in question.parts:
                part_answers = answers_by_part.get(part.number, [])
                
                if not part_answers:
                    comments.append(f"第{question.number}题第{part.number}小题未作答")
                    continue
                
                # 检查该小题的所有空
                blanks_count = len(part.keywords or [1])
                total_possible_score += blanks_count  # 累加可能的总分
                
                if len(part_answers) < blanks_count:
                    comments.append(f"第{question.number}题第{part.number}小题答案不完整")
                    continue
                
                part_score = 0
                part_comments = []
                
                # 检查每个空的答案
                for blank_number in range(1, blanks_count + 1):
                    blank_answers = [
                        ans for ans in part_answers 
                        if ans.blank_number == blank_number
                    ]
                    
                    if not blank_answers:
                        part_comments.append(f"第{blank_number}空未作答")
                        continue
                        
                    student_answer = blank_answers[0]  # 取第一个答案
                    standard_answer = self.get_standard_answer_text(part, blank_number)
                    
                    # 如果答案被划掉，记为0分
                    if student_answer.is_crossed_out:
                        part_comments.append(
                            f"第{blank_number}空：答案「{student_answer.content}」被划掉，"
                            f"标准答案为「{standard_answer}」"
                        )
                        continue
                    
                    # 检查答案是否正确
                    is_correct = self.check_answer_correctness(
                        student_answer.content, part, blank_number
                    )
                    
                    if is_correct:
                        part_score += 1
                        part_comments.append(
                            f"第{blank_number}空：答案「{student_answer.content}」正确 (1分)"
                        )
                    else:
                        part_comments.append(
                            f"第{blank_number}空：答案「{student_answer.content}」错误，"
                            f"标准答案为「{standard_answer}」 (0分)"
                        )
                
                # 添加该小题的评价意见
                score_text = f"得分：{part_score}/{blanks_count}分"
                comments.append(
                    f"第{question.number}题第{part.number}小题（{score_text}）：\n" + 
                    "\n".join(f"  {comment}" for comment in part_comments)
                )
                
                # 累加得分
                total_score += part_score
        
        # 在评价意见开头添加总分信息
        comments.insert(0, f"=== 评分结果 ===\n总分: {total_score}/{total_possible_score}")
        
        return total_score, comments 
