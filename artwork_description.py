#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
艺术品图像描述模块 - 基于本地 Ollama 与 Qwen-VL-Chat
"""
import base64
import os
import requests
import time
from dotenv import load_dotenv

# 加载 .env 文件中的环境变量
load_dotenv()


class ArtworkDescriptionService:
    """
    艺术品图像描述服务类 (Ollama + Qwen-7B-Chat 版本)
    """

    def __init__(self):
        """
        初始化服务，连接到本地 Ollama 实例。
        请确保您已在 .env 文件中配置了 Ollama 的 URL 和模型名称。
        """
        # 从环境变量获取 Ollama 的配置，如果不存在则使用默认值
        self.base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
        self.model = os.getenv("OLLAMA_MODEL", "qwen2.5:7b")  # 确保你已通过 `ollama pull qwen:7b-chat` 下载此模型

        if not self.base_url:
            raise EnvironmentError("请在 .env 文件中设置 OLLAMA_BASE_URL")

        print("--- 艺术品图像描述服务 (Ollama) 初始化 ---")
        print(f"Ollama URL: {self.base_url}")
        print(f"使用模型: {self.model}")
        print("-----------------------------------------")

    def encode_image_to_base64(self, image_path):
        """
        将图像文件编码为 base64 字符串。
        (此函数无需修改，功能通用)
        """
        try:
            with open(image_path, "rb") as f:
                return base64.b64encode(f.read()).decode('utf-8')
        except Exception as e:
            print(f"错误: 图像编码失败 - {e}")
            return None

    def describe_artwork_image(self, segmented_image_path):
        """
        描述图像（仅处理分割后的图像）
        Args:
            segmented_image_path: 分割后图像路径
        Returns:
            tuple: (成功标志, 描述文本或错误信息)
        """
        try:
            # 检查图像是否存在
            if not segmented_image_path or not os.path.exists(segmented_image_path):
                return False, "分割后图像不存在"
            # 编码图像为 Base64
            image_b64 = self.encode_image_to_base64(segmented_image_path)
            if not image_b64:
                return False, "图像编码失败"
            return self._call_ollama(image_b64, is_artwork=True)

        except Exception as e:
            return False, f"图像描述生成失败: {str(e)}"

    def describe_single_image(self, image_path, custom_prompt=None):
        """
        描述单张图像（通用版）
        Args:
            image_path: 图像文件路径
            custom_prompt: 自定义提示词
        Returns:
            tuple: (成功标志, 描述文本或错误信息)
        """
        try:
            if not os.path.exists(image_path):
                return False, "图像文件不存在"
            image_b64 = self.encode_image_to_base64(image_path)
            if not image_b64:
                return False, "图像编码失败"
            return self._call_ollama(image_b64, custom_prompt=custom_prompt, is_artwork=False)
        except Exception as e:
            return False, f"图像描述生成失败: {str(e)}"

    def _call_ollama(self, image_base64, custom_prompt=None, is_artwork=True):
        """
        Args:
            image_base64: Base64 编码的图像数据
            custom_prompt: 自定义提示词
            is_artwork: 是否为古画图像（决定使用专用提示词）
        Returns:
            tuple: (成功标志, 描述文本或错误信息)
        """
         # 构建提示词
        if is_artwork:
            prompt = """你是一位经验丰富的中国古代艺术史专家和书画鉴赏家。请以专业、严谨、结构化的方式，详细分析眼前这幅图像。

**分析要求：**
1.  **客观描述优先**：首先对画面进行客观的视觉描述，不加入主观推测。
2.  **逻辑推断**：在描述的基础上，结合艺术史知识进行推断。

**请从以下几个核心角度展开分析：**

1.  主题与内容 (Theme & Content)
    - 视觉描述：画面描绘了什么？是山水、人物、花鸟，还是书法？
    - 细节解读：如果有人物，他们在做什么？如果是山水，描绘的是何种景致（如寒林、雪景、江景）？

2.  风格与技法 (Style & Technique)
    - 笔墨 (Brushwork)：线条是刚劲、柔和、粗放还是细致？
    - 皴法 (Texture Strokes)：如果是山水画，主要使用了哪种皴法（如斧劈皴、披麻皴、牛毛皴等）？
    - 设色 (Use of Color)：是水墨画还是设色画？色彩运用有何特点（如青绿、浅绛）？

3.  构图与布局 (Composition)
    - 章法：画面元素是如何安排的？是全景式、边角式，还是一河两岸式？
    - 空间处理：画面是否有明显的视觉焦点？空间感（高远、深远、平远）处理得如何？

4.  印章与题跋 (Seals & Inscriptions)
    - 现状：画面上是否有可见的印章或文字？
    - 辨识与推断：如果有，请尝试辨认其内容和字体；若无法辨认，仅描述其位置和颜色（如朱文/白文）；若不能非常确定，不要说。

5.  作者与朝代推断 (Artist & Dynasty Attribution)
    - 时代特征：它的风格最符合哪个朝代（如唐、宋、元、明、清）的特征？
    - 流派/画家：综合以上分析，你认为这幅作品最有可能出自哪个流派或哪位画家之手？若不能非常确定，就说明只是猜测**请说明具体的风格依据**。

6.  情感与意境 (Mood & Atmosphere)
    - 氛围：这幅画作传达了怎样的情感或氛围？是雄伟、壮阔、宁静、高雅，还是荒寒、萧瑟？

请用专业术语进行描述，并以清晰的结构输出你的分析报告。
        
        """
        else:
               prompt = custom_prompt or "请详细描述这张图像的内容和特征。"
        url = f"{self.base_url}/api/chat"
        headers = {"Content-Type": "application/json"}
         # 构建 Ollama 的请求体 (Payload)
         # 注意：Qwen模型通过 'images' 字段接收 base64 图像列表
        data = {
            "model": self.model,
            "messages": [
                {
                    "role": "user",
                    "content": prompt,
                    "images": [image_base64]
                }
            ],
            "stream": False,  # 我们需要一次性获得完整响应
            "options": {
                "temperature": 0.2  # 较低的温度，使分析更具确定性和专业性
            }
        }

        try:
            start_time = time.time()
            response = requests.post(url, headers=headers, json=data, timeout=500)  # 延长超时时间以应对复杂图像分析
            end_time = time.time()
            print(f"Ollama 请求耗时: {end_time - start_time:.2f} 秒")

            response.raise_for_status()  # 如果状态码不是 2xx，则抛出 HTTPError

            result = response.json()

        # 提取 Ollama 返回的核心内容
            if 'message' in result and 'content' in result['message']:
                content = result['message']['content']
                content = content.replace('**', '')
                import re
                
                # 处理标题标记，将#标题转换为HTML标题
                lines = content.split('\n')
                formatted_lines = []
                empty_line_count = 0

                for line in lines:
                    line = line.strip()
                    if line:
                        # 检查是否是标题行
                        title_match = re.match(r'^(#{1,3})\s*(.+)$', line)
                        if title_match:
                            title_text = title_match.group(2)
                            formatted_lines.append(f'<h3>{title_text}</h3>')
                        elif len(line) < 15 and (line.endswith('：') or line.endswith(':') or 
                                                line.endswith('说明') or line.endswith('定位') or 
                                                line.endswith('宗旨') or line.endswith('基')):
                            title_text = line.rstrip('：:')
                            formatted_lines.append(f'<h3>{title_text}</h3>')
                        else:
                            formatted_lines.append(line)
                        
                        empty_line_count = 0
                    else:
                        empty_line_count += 1
                        if empty_line_count == 1 and formatted_lines:
                            formatted_lines.append('')

                # 清理开头和结尾的空行
                while formatted_lines and not formatted_lines[0]:
                    formatted_lines.pop(0)
                while formatted_lines and not formatted_lines[-1]:
                    formatted_lines.pop()

                result = '\n'.join(formatted_lines)
                return True, result.strip()
            else:
                return False, f"响应格式异常，无法提取描述内容。原始响应: {result}"

        except requests.exceptions.Timeout:
            return False, "请求 Ollama 服务超时，请确认 Ollama 是否正在运行，并考虑延长超时时间。"
        except requests.exceptions.RequestException as e:
            return False, f"网络请求异常: 无法连接到 Ollama 服务于 {self.base_url}。请检查服务是否启动。错误: {str(e)}"
        except Exception as e:
            return False, f"调用 Ollama 时发生未知错误: {str(e)}"

# 全局图像描述服务实例
image_description_service = ArtworkDescriptionService()

# --- 主程序入口，用于独立测试 ---
if __name__ == "__main__":
    # --- 使用前请确认 ---
    # 1. Ollama 服务已在本地运行。
    # 2. 您已通过 `ollama pull qwen:7b-chat` 下载了所需的模型。
    # 3. 您的 .env 文件已正确配置 (如果您的Ollama不在默认地址)。

    # 实例化服务
    artwork_service = ArtworkDescriptionService()

    # <<< 请将此路径替换为您自己的古代书画图片路径 >>>
    test_image_path = "千里江山图_局部.jpg"

    if os.path.exists(test_image_path):
        print(f"\n正在分析艺术品图像: {test_image_path}")

        # 调用核心方法
        success, description = artwork_service.describe_artwork_image(test_image_path)

        if success:
            print("\n--- 鉴赏报告 ---")
            print("=" * 80)
            print(description)
            print("=" * 80)
        else:
            print(f"\n[分析失败]: {description}")
    else:
        print(f"\n[测试警告]: 测试图片 '{test_image_path}' 不存在。")
        print("请将脚本中的 'test_image_path' 替换为您电脑上一张真实的书画图片路径，然后重新运行。")
