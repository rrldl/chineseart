#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
艺术品图像描述模块 - 基于本地 Ollama 与 Qwen-VL-Chat
"""
import base64
import os
import time
import requests
from dotenv import load_dotenv
from rich import print
from dashscope import MultiModalConversation
from http import HTTPStatus
import logging
import dashscope
from PIL import Image
import io
import base64

# 屏蔽 dashscope 库打印庞大的请求体
logging.getLogger("dashscope").setLevel(logging.WARNING)
# 屏蔽底层网络库的请求日志
logging.getLogger("urllib3").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)

# 加载 .env 文件中的环境变量
load_dotenv()

dashscope.api_key = os.getenv("DASHSCOPE_API_KEY")
print("KEY =", os.getenv("DASHSCOPE_API_KEY"))
ALI_MODEL1="qwen-vl-plus"
class ArtworkDescriptionService:
    """
    艺术品图像描述服务类 (Ollama + Qwen-7B-Chat 版本)
    """

    def __init__(self):
        """
        初始化服务，连接到通义千问 API。
        请确保您已在 .env 文件中配置了通义千问的 API Key 和模型名称。
        """
        self.ali_api_key = os.getenv("DASHSCOPE_API_KEY")
        self.ali_model1 = os.getenv("ALI_MODEL1", "qwen-vl-plus")# 多模态模型

        if not self.ali_api_key or not self.ali_model1:
            raise EnvironmentError("请在 .env 文件中设置 ALI_API_KEY 和 ALI_MODEL1")

        print("--- 艺术品图像描述服务 (通义千问) 初始化 ---")
        print(f"通义千问API模型 (图像): {self.ali_model1}")
        print(f"API Key 已加载: {self.ali_api_key[:4]}...{self.ali_api_key[-4:]} (部分显示)" if self.ali_api_key else "API Key 未加载")
        print("------------------------------------------")

    def encode_image_to_base64(self, image_path):
        """
        读取图像，缩小尺寸并压缩，最后转为 base64。
        解决 Exceeded limit on max bytes 错误。
        """
        try:
            # 打开图片
            with Image.open(image_path) as img:
                # 1. 统一转为 RGB 模式（JPEG 不支持透明层，必须转换）
                if img.mode in ("RGBA", "P", "CMYK"):
                    img = img.convert("RGB")
                
                # 2. 限制最大边长为 1440 像素 (足以看清细节，且体积小)
                max_size = 1440
                if max(img.size) > max_size:
                    img.thumbnail((max_size, max_size), Image.Resampling.LANCZOS)
                    print(f"图片尺寸已缩小至: {img.size}")

                # 3. 将图片保存到内存缓冲区
                buffer = io.BytesIO()
                # 使用 JPEG 格式和 80 的质量进行压缩
                img.save(buffer, format="JPEG", quality=80)
                
                # 4. 获取字节数据并编码
                encoded_string = base64.b64encode(buffer.getvalue()).decode('utf-8')
                
                # 打印一下编码后的大小，方便调试 (Base64 比原始字节大 33% 左右)
                print(f"Base64 编码后体积: {len(encoded_string) / 1024 / 1024:.2f} MB")
                return encoded_string
                
        except Exception as e:
            print(f"错误: 图像压缩编码失败 - {e}")
            return None

    # 🌟 修改点：把参数名从 segmented_image_path 改为 original_image_path
    # 明确告诉大模型，这是纯净的原图
    def describe_artwork_image(self, original_image_path):
        """
        描述艺术品图像（必须传入未分割的、纯净的原图！）
        Args:
            original_image_path: 纯净的原图路径
        Returns:
            tuple: (成功标志, 描述文本或错误信息)
        """
        try:
            print(f"\n🚨🚨🚨 警告：我现在真正喂给通义千问的图片是 ===> {original_image_path} 🚨🚨🚨\n")
            if not original_image_path or not os.path.exists(original_image_path):
                return False, "原图不存在"
                
            image_b64 = self.encode_image_to_base64(original_image_path)
            if not image_b64:
                return False, "图像编码失败"
                
            return self._call_ali_qwen_multimodal(image_b64, is_artwork=True)

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
            return self._call_ali_qwen_multimodal(image_b64, custom_prompt=custom_prompt, is_artwork=False)
        except Exception as e:
            return False, f"图像描述生成失败: {str(e)}"

    def _call_ali_qwen_multimodal(self, image_base64, custom_prompt=None, is_artwork=True):
        """
        Args:
            image_base64: Base64 编码的图像数据
            custom_prompt: 自定义提示词
            is_artwork: 是否为古画图像（决定使用专用提示词）
        Returns:
            tuple: (成功标志, 描述文本或错误信息)
        """
        if not self.ali_api_key or not self.ali_model1:
            return False, "通义千问API未配置或不可用。"

        # 构建提示词 (与之前类似)
        if is_artwork:
            prompt_content = """你是一位经验丰富的中国古代艺术史专家和书画鉴赏家。请以专业、严谨、结构化的方式，详细分析眼前这幅图像。

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
               prompt_content = custom_prompt or "请详细描述这张图像的内容和特征。"

        messages = [
            {
                "role": "user",
                "content": [
                    {"image": f"data:image/jpeg;base64,{image_base64}"},
                    {"text": prompt_content}
                ]
            }
        ]

        try:
            start_time = time.time()
            response = MultiModalConversation.call(
                model=self.ali_model1,
                api_key=self.ali_api_key,
                messages=messages,
            )
            end_time = time.time()
            print(f"通义千问API请求耗时: {end_time - start_time:.2f} 秒")

            if response.status_code == HTTPStatus.OK:
                content = response.output.choices[0].message.content[0]['text']
                if not content:
                    print("[red]通义千问API返回了空内容[/red]")
                    return False, "通义千问API返回了空内容"
                print("[green]✅ 图像描述生成成功[/green]")
                return True, content.strip()
            else:
                error_message = f"通义千问API返回错误状态码: {response.status_code}, " \
                                f"错误代码: {response.code}, 错误信息: {response.message}"
                print(f"[red]{error_message}[/red]")
                return False, error_message

        except Exception as e:
            print(f"[red]调用通义千问API时发生错误: {str(e)}[/red]")
            return False, f"调用通义千问API时发生错误: {str(e)}"
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
