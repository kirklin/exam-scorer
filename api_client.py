import requests
from typing import List, Dict, Optional
from pydantic import BaseModel, Field

class ScoringTask(BaseModel):
    task_key: str = Field(..., alias='taskKey')
    kaohao: str
    block_img: str = Field(..., alias='blockImg')
    pos: List[Dict]
    review_records: List[Dict] = Field(default_factory=list, alias='reviewRecords')
    student_paper_img: Optional[str] = Field(None, alias='stuPaperImg')
    template_id: Optional[int] = Field(0, alias='templateid')
    reviewer_id: Optional[int] = Field(None, alias='reviewerId')

    class Config:
        populate_by_name = True
        from_attributes = True

class ScoringAPIClient:
    def __init__(self, base_url: str, cookies: Dict[str, str]):
        self.base_url = base_url
        self.cookies = cookies
        self.headers = {
            "accept": "application/json, text/plain, */*",
            "content-type": "application/json;charset=UTF-8",
            "sec-ch-ua": "\"Microsoft Edge\";v=\"131\", \"Chromium\";v=\"131\", \"Not_A Brand\";v=\"24\"",
            "sec-ch-ua-platform": "\"macOS\""
        }

    def get_tasks(self, subject_id: str, block_id: str, count: int = 4) -> List[ScoringTask]:
        """获取待阅试卷列表"""
        url = f"{self.base_url}/filter/yue/v400/subject/block/review/task"
        params = {
            "subjectId": subject_id,
            "blockId": block_id,
            "type": "normal",
            "count": count,
            "blockVersion": "0",
            "isQuiz": "false"
        }
        
        response = requests.get(
            url,
            params=params,
            headers=self.headers,
            cookies=self.cookies
        )
        response.raise_for_status()
        
        data = response.json()
        if data["code"] != 0:
            raise Exception(f"API错误: {data['message']}")
        
        # 调试输出
        print("\nAPI返回数据:")
        print(data)
            
        try:
            return [ScoringTask.model_validate(task) for task in data["data"]]
        except Exception as e:
            print(f"\n数据验证错误: {str(e)}")
            print("\n实际数据示例:")
            if data["data"]:
                print(data["data"][0])
            raise

    def submit_score(
        self,
        subject_id: str,
        block_id: str,
        task_key: str,
        scores: List[Dict[str, str]],
        delay: int = 5000
    ) -> Dict:
        """提交评分结果"""
        url = f"{self.base_url}/filter/yue/v353/subject/block/review/task"
        params = {
            "subjectId": subject_id,
            "blockId": block_id,
            "type": "normal",
            "taskKey": task_key
        }
        
        data = {
            "delay": delay,
            "scores": scores,
            "marks": [{
                "type": 6,
                "i": 0,
                "x": 930,
                "y": 170.26845637583892
            }],
            "isExcellent": False,
            "isSpecialWrong": False,
            "blockVersion": "0"
        }
        
        response = requests.post(
            url,
            params=params,
            json=data,
            headers=self.headers,
            cookies=self.cookies
        )
        response.raise_for_status()
        
        result = response.json()
        if result["code"] != 0:
            raise Exception(f"提交分数失败: {result['message']}")
            
        return result["data"] 
