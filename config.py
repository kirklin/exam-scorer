from dotenv import load_dotenv
import os
from zhipuai import ZhipuAI

# 加载环境变量
load_dotenv()

# 获取API密钥
ZHIPUAI_API_KEY = os.getenv("ZHIPUAI_API_KEY")

# 初始化智谱AI客户端
client = ZhipuAI(api_key=ZHIPUAI_API_KEY)

# 模型配置
MODEL_NAME = "glm-4v-plus-0111"
