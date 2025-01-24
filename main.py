import json
import os
from typing import List, Dict

import requests
from rich.console import Console
from rich.table import Table

from answer_checker import AnswerChecker
from api_client import ScoringAPIClient
from image_processor import ImageProcessor
from models import AnswerSheet, StudentAnswer

console = Console()

def load_standard_answer(file_path: str) -> AnswerSheet:
    """加载标准答案"""
    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    return AnswerSheet(**data)

def save_image(url: str, kaohao: str) -> str:
    """下载并保存图片到data/images目录"""
    # 创建images目录
    images_dir = os.path.join("data", "images")
    os.makedirs(images_dir, exist_ok=True)
    
    # 直接用考号作为文件名
    image_name = f"{kaohao}.png"
    image_path = os.path.join(images_dir, image_name)
    
    # 下载并保存图片
    response = requests.get(url)
    response.raise_for_status()
    
    with open(image_path, 'wb') as f:
        f.write(response.content)
    
    return image_path

def extract_part_score(comments: List[str], question_number: int, part_number: int) -> int:
    """从评分意见中提取某一小题的得分"""
    for comment in comments:
        if f"第{question_number}题第{part_number}小题（得分：" in comment:
            # 提取得分，格式如："得分：2/3分"
            score_part = comment.split("得分：")[1].split("/")[0]
            return int(score_part)
    return 0

def convert_to_api_scores(score: float, comments: List[str], question_number: int) -> List[Dict[str, str]]:
    """将我们的评分结果转换为API所需的格式"""
    return [
        {
            "key": f"{question_number}.{part_number}",
            "score": str(extract_part_score(comments, question_number, part_number))
        }
        for part_number in range(1, 4)  # 假设有3个小问
    ]

def display_scoring_info(
    student_answers: List[StudentAnswer],
    standard_answer: AnswerSheet,
    score: float,
    comments: List[str],
    api_scores: List[Dict[str, str]]
):
    """显示评分信息"""
    # 创建表格显示答案对比
    table = Table(title="答案对比")
    table.add_column("题号", style="cyan")
    table.add_column("学生答案", style="yellow")
    table.add_column("标准答案", style="green")
    table.add_column("得分", style="magenta")

    # 创建AnswerChecker实例用于获取标准答案
    checker = AnswerChecker(standard_answer)

    # 添加答案对比
    for answer in student_answers:
        question = next(
            (q for q in standard_answer.questions if q.number == answer.question_number),
            None
        )
        if question:
            part = next(
                (p for p in question.parts if p.number == answer.part_number),
                None
            )
            if part:
                # 使用AnswerChecker的方法获取标准答案
                standard = checker.get_standard_answer_text(part, answer.blank_number)
                is_correct = checker.check_answer_correctness(answer.content, part, answer.blank_number)
                table.add_row(
                    f"{answer.question_number}.{answer.part_number}.{answer.blank_number}",
                    answer.content,
                    standard,
                    "✓" if is_correct else "✗"
                )

    console.print(table)
    
    # 显示评分意见
    console.print("\n[bold cyan]评分意见:[/bold cyan]")
    for comment in comments:
        console.print(f"- {comment}")
    
    # 显示准备提交的数据
    console.print("\n[bold cyan]准备提交的数据:[/bold cyan]")
    console.print(api_scores)

def process_answer_sheet(image_path: str, question_numbers: List[int]) -> List[StudentAnswer]:
    """处理答题卡图片"""
    processor = ImageProcessor()
    all_answers = []
    for question_number in question_numbers:
        answers = processor.process_image(image_path, question_number)
        all_answers.extend(answers)
    return all_answers

def main(
    api_client: ScoringAPIClient,
    subject_id: str,
    block_id: str,
    standard_answer_path: str,
    question_numbers: List[int]
):
    """主程序入口"""
    try:
        # 加载标准答案
        console.print("[bold cyan]正在加载标准答案...[/bold cyan]")
        standard_answer = load_standard_answer(standard_answer_path)
        
        while True:
            # 获取待阅试卷
            tasks = api_client.get_tasks(subject_id, block_id)
            if not tasks:
                console.print("[yellow]没有更多待阅试卷[/yellow]")
                break
                
            for task in tasks:
                try:
                    console.print(f"\n[bold cyan]处理试卷 {task.kaohao}...[/bold cyan]")
                    
                    # 保存试卷图片
                    image_path = save_image(task.block_img, task.kaohao)
                    console.print(f"[green]图片已保存: {image_path}[/green]")
                    
                    # 处理答题卡图片
                    student_answers = process_answer_sheet(image_path, question_numbers)
                    
                    if not student_answers:
                        console.print("[red]警告：未能识别到任何答案[/red]")
                        continue
                    
                    # 检查答案
                    console.print("\n[bold cyan]正在评分...[/bold cyan]")
                    checker = AnswerChecker(standard_answer)
                    score, comments = checker.check_answer(student_answers)
                    
                    # 准备API评分数据
                    api_scores = convert_to_api_scores(score, comments, question_numbers[0])
                    
                    # 显示评分信息
                    display_scoring_info(
                        student_answers,
                        standard_answer,
                        score,
                        comments,
                        api_scores
                    )
                    
                    # 等待用户确认或自动提交
                    import sys
                    import select
                    import time
                    
                    console.print("\n[yellow]3秒后自动提交，按N进行手动评分...[/yellow]")
                    
                    # 实现3秒倒计时，同时监听输入
                    start_time = time.time()
                    while time.time() - start_time < 3:
                        remaining = 3 - int(time.time() - start_time)
                        print(f"\r倒计时: {remaining}秒...", end="", flush=True)
                        
                        # 检查是否有输入
                        if sys.stdin in select.select([sys.stdin], [], [], 0)[0]:
                            user_input = sys.stdin.readline().strip().upper()
                            if user_input == 'N':
                                print("\n")  # 清除倒计时行
                                # 手动输入分数
                                try:
                                    console.print("[cyan]请依次输入三个小题的分数（用空格分隔，如：3 3 1）：[/cyan]")
                                    scores = input().strip().split()
                                    if len(scores) != 3:
                                        raise ValueError("必须输入3个分数")
                                    scores = [int(s) for s in scores]
                                    # 更新api_scores
                                    for i, score in enumerate(scores, 1):
                                        api_scores[i-1]["score"] = str(score)
                                except ValueError as e:
                                    console.print(f"[red]输入错误：{str(e)}[/red]")
                                    continue
                            break
                        time.sleep(0.1)
                    
                    print("\n")  # 清除倒计时行
                    
                    # 提交分数
                    try:
                        result = api_client.submit_score(
                            subject_id=subject_id,
                            block_id=block_id,
                            task_key=task.task_key,
                            scores=api_scores
                        )
                        console.print(f"\n[green]分数提交成功，已阅数量: {result.get('available', 0)}[/green]")
                    except Exception as e:
                        console.print(f"[red]提交分数时发生错误: {str(e)}[/red]")
                    
                except Exception as e:
                    console.print(f"[red]处理试卷时发生错误: {str(e)}[/red]")
                    continue
                    
    except Exception as e:
        console.print(f"[red]发生错误: {str(e)}[/red]")
        import traceback
        console.print(traceback.format_exc())

if __name__ == "__main__":
    # API配置
    base_url = "https://yue.haofenshu.com"
    cookies = {
        "yx_sid": ""  # 需要替换为实际的cookie
    }
    
    # 创建API客户端
    api_client = ScoringAPIClient(base_url, cookies)
    
    # 阅卷参数
    subject_id = "阅卷参数subject_id"
    block_id = "阅卷参数block_id"
    standard_answer_path = "./data/standard_answer.json"
    question_numbers = [28]
    
    main(api_client, subject_id, block_id, standard_answer_path, question_numbers) 
