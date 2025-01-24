import base64
import json
from typing import List
from config import client, MODEL_NAME
from models import StudentAnswer

class ImageProcessor:
    @staticmethod
    def encode_image(image_path: str) -> str:
        """将图片转换为base64编码"""
        with open(image_path, 'rb') as img_file:
            return base64.b64encode(img_file.read()).decode('utf-8')

    @staticmethod
    def clean_json_string(json_str: str) -> str:
        """清理JSON字符串，去除markdown格式"""
        # 去除可能的markdown代码块标记
        if "```json" in json_str:
            json_str = json_str.split("```json")[1]
        if "```" in json_str:
            json_str = json_str.split("```")[0]
        return json_str.strip()

    @staticmethod
    def process_image(image_path: str, question_number: int) -> List[StudentAnswer]:
        """处理答题图片，返回识别结果"""
        # 编码图片
        img_base64 = ImageProcessor.encode_image(image_path)
        
        # 构建提示词
        prompt = f"""
        你擅长精确分析答题卡,并能准确识别各种手写体答案及其状态。
        请你从左往右，从上往下阅读卷子
        请仔细分析这张答题卡图片中第{question_number}题的所有答案。

        要求：
        1. 识别每个小题中所有空(下划线)的答案内容
        2. 每个小题可能包含多个空（下划线）这份卷子一共7个空
        3. 判断每个答案是否有删除线或涂改
        4. 评估每个答案的字迹是否清晰
        5. 对每个答案给出置信度评分(0-1)

        请以JSON格式返回结果，格式如下：
        {{
            "question_number": 28,
            "parts": [
                {{
                    "part_number": 1,
                    "answers": [
                        {{
                            "blank_number": 1,
                            "content": "答案内容",
                            "is_crossed_out": <是否有删除线与涂抹>,
                            "is_blurry": <是否模糊>,
                            "confidence": <可信度评分>
                        }},
                        ...
                    ]
                }},
                ...
            ]
        }}
        """
        
        # 调用模型
        response = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{img_base64}"
                            }
                        },
                        {
                            "type": "text",
                            "text": prompt
                        }
                    ]
                }
            ]
        )
        
        # 解析响应
        result = response.choices[0].message.content
        print("模型返回结果:", result)  # 调试输出
        
        try:
            # 清理并解析JSON
            cleaned_json = ImageProcessor.clean_json_string(result)
            data = json.loads(cleaned_json)
            student_answers = []
            
            # 转换为StudentAnswer对象列表
            for part in data.get("parts", []):
                part_number = part.get("part_number")
                for answer in part.get("answers", []):
                    student_answer = StudentAnswer(
                        question_number=question_number,
                        part_number=part_number,
                        blank_number=answer.get("blank_number", 1),
                        content=answer.get("content", ""),
                        confidence=answer.get("confidence", 0.0),
                        is_crossed_out=answer.get("is_crossed_out", False),
                        is_blurry=answer.get("is_blurry", True)
                    )
                    student_answers.append(student_answer)
            
            return student_answers
            
        except json.JSONDecodeError as e:
            print(f"JSON解析错误: {str(e)}")
            print("清理后的JSON字符串:", cleaned_json)  # 调试输出
            return []
        except Exception as e:
            print(f"处理答案时发生错误: {str(e)}")
            return [] 
