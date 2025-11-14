"""
Kimi K2 Web Interface for Math-To-Manim (中文界面)
Complete Gradio interface with all features from Claude GUI
Powered by Kimi K2 thinking model from Moonshot AI
中文版本
"""

import os
import sys
from pathlib import Path
import asyncio
from typing import Optional

from dotenv import load_dotenv
import gradio as gr

# Load environment variables from project root
load_dotenv()

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from KimiK2Thinking.agents.prerequisite_explorer_kimi import KimiPrerequisiteExplorer
from KimiK2Thinking.agents.enrichment_chain import KimiEnrichmentPipeline
from KimiK2Thinking.kimi_client import KimiClient

# Import for video review (if available)
try:
    from src.agents import VideoReviewAgent, VideoReviewResult
except Exception:
    VideoReviewAgent = None
    VideoReviewResult = None


class KimiK2GUI:
    """完整的Web界面，集成Kimi K2所有功能"""

    def __init__(self):
        """初始化GUI和Kimi K2代理"""
        self.explorer = None
        self.pipeline = None
        self.manim_client = None
        self.current_tree = None
        self.chat_client = None

    def initialize_agents(self, use_tools=True, max_depth=3):
        """初始化Kimi K2代理"""
        try:
            self.explorer = KimiPrerequisiteExplorer(
                max_depth=max_depth,
                use_tools=use_tools
            )
            self.pipeline = KimiEnrichmentPipeline()
            self.manim_client = KimiClient()
            self.chat_client = KimiClient()
            return "✅ Kimi K2 代理初始化成功！"
        except Exception as e:
            return f"❌ 初始化代理时出错: {str(e)}"

    # ============================================================================
    # 聊天界面（来自Claude GUI）
    # ============================================================================

    def chat_with_kimi(self, message, history):
        """
        与Kimi K2聊天，生成Manim代码或讨论概念
        复刻Claude GUI的聊天功能
        """
        # 转换历史记录为API期望的格式
        messages = []
        for human, assistant in history:
            messages.append({"role": "user", "content": human})
            if assistant:
                messages.append({"role": "assistant", "content": assistant})
        messages.append({"role": "user", "content": message})

        system_prompt = """你是Manim动画专家和数学教育专家。

你能帮助用户：
1. 理解数学概念
2. 生成Manim社区版的动画代码
3. 创建详细的动画提示词
4. 调试Manim代码问题
5. 为数学概念提供可视化建议

生成Manim代码时：
- 使用正确的导入: from manim import *
- 定义带有construct()方法的Scene类
- 对数学表达式使用LaTeX（原始字符串）
- 提供解释动画逻辑的评论
- 使用适当的颜色和定位
- 包含时间信息（wait, play durations）

始终正确格式化LaTeX并使用MathTex()表示方程。"""

        # 调用Kimi K2 API
        try:
            response = self.chat_client.chat_completion(
                messages=messages,
                max_tokens=4000,
                system=system_prompt
            )

            answer = self.format_latex(self.chat_client.get_text_content(response))
            return answer
        except Exception as e:
            return f"错误: {str(e)}"

    # ============================================================================
    # 提示词扩展器（来自Claude GUI）
    # ============================================================================

    def format_latex(self, text):
        """格式化Gradio中的内联LaTeX表达式（来自Claude GUI）"""
        # 将单美元符号替换为双美元符号以获得更好的显示效果
        lines = text.split('\n')
        formatted_lines = []

        for line in lines:
            # 跳过已经包含双美元符号的行
            if '$$' in line:
                formatted_lines.append(line)
                continue

            # 格式化单美元符号表达式
            in_math = False
            new_line = ''
            for i, char in enumerate(line):
                if char == '$' and (i == 0 or line[i-1] != '\\'):
                    in_math = not in_math
                    new_line += '$$' if in_math else '$$'
                else:
                    new_line += char
            formatted_lines.append(new_line)

        return '\n'.join(formatted_lines)

    def process_simple_prompt(self, simple_prompt):
        """
        将简单的想法转化为详细的Manim提示词
        复刻Claude GUI的提示词扩展器
        """
        if not simple_prompt.strip():
            return "请输入要扩展的提示词。"

        system_prompt = """你是创建详细LaTeX丰富提示词的专家，专为Manim动画设计。

将用户的简单描述转化为全面、2000+词元的提示词，要求：
1. 指定每个视觉元素（颜色、位置、大小）
2. 对所有方程使用正确的LaTeX格式化
3. 提供顺序说明（"首先...", "接下来...", "然后..."）
4. 保持场景之间的视觉连续性
5. 包含时间信息
6. 指定相机运动
7. 对数学对象进行一致的颜色编码

输出应该足够详细，以便AI生成可运行的Manim社区版代码。"""

        try:
            response = self.manim_client.chat_completion(
                messages=[{"role": "user", "content": f"为以下内容创建详细的Manim动画提示词: {simple_prompt}"}],
                max_tokens=4000,
                system=system_prompt
            )

            return self.format_latex(self.manim_client.get_text_content(response))
        except Exception as e:
            return f"错误: {str(e)}"

    # ============================================================================
    # 知识树（Kimi K2原创功能）
    # ============================================================================

    def explore_concept(self, concept, max_depth=3, use_tools=True):
        """探索概念并构建知识树"""
        if not concept.strip():
            return "", "", "❌ 请输入要探索的概念"

        try:
            # 使用当前设置重新初始化
            self.initialize_agents(use_tools=use_tools, max_depth=max_depth)

            # 运行探索
            tree = asyncio.run(self.explorer.explore_async(concept, verbose=False))
            self.current_tree = tree

            # 格式化树以显示
            tree_text = self.format_tree_display(tree)

            return tree_text, f"✅ 成功探索'{concept}'", ""

        except Exception as e:
            return "", f"❌ 探索概念时出错: {str(e)}", ""

    def format_tree_display(self, node, prefix="", is_last=True):
        """格式化知识树以便文本显示"""
        connector = "└─ " if is_last else "├─ "
        foundation_marker = " [基础概念]" if node.is_foundation else ""
        result = f"{prefix}{connector}{node.concept} (深度 {node.depth}){foundation_marker}\n"

        if node.prerequisites:
            new_prefix = prefix + ("   " if is_last else "│  ")
            for i, prereq in enumerate(node.prerequisites):
                is_last_prereq = (i == len(node.prerequisites) - 1)
                result += self.format_tree_display(prereq, new_prefix, is_last_prereq)

        return result

    def run_enrichment(self):
        """在当前的树上运行丰富化管道"""
        if not self.current_tree:
            return "", "", "❌ 没有知识树可以丰富化。请先探索一个概念。"

        try:
            result = asyncio.run(self.pipeline.run_async(self.current_tree))
            enriched_tree = self.format_enriched_tree_display(self.current_tree)
            narrative = result.narrative.verbose_prompt if result.narrative else "未生成叙事"
            return enriched_tree, narrative, "✅ 丰富化完成！"
        except Exception as e:
            return "", "", f"❌ 丰富化过程中出错: {str(e)}"

    def format_enriched_tree_display(self, node, prefix="", is_last=True):
        """格式化包含数学内容的丰富化树"""
        connector = "└─ " if is_last else "├─ "
        foundation_marker = " [基础概念]" if node.is_foundation else ""
        result = f"{prefix}{connector}{node.concept} (深度 {node.depth}){foundation_marker}\n"

        if hasattr(node, 'equations') and node.equations:
            eq_prefix = prefix + ("   " if is_last else "│  ")
            result += f"{eq_prefix}  📐 方程: {len(node.equations)}\n"

        if hasattr(node, 'visual_spec') and node.visual_spec:
            eq_prefix = prefix + ("   " if is_last else "│  ")
            result += f"{eq_prefix}  🎨 视觉元素: {len(node.visual_spec.elements)}\n"

        if node.prerequisites:
            new_prefix = prefix + ("   " if is_last else "│  ")
            for i, prereq in enumerate(node.prerequisites):
                is_last_prereq = (i == len(node.prerequisites) - 1)
                result += self.format_enriched_tree_display(prereq, new_prefix, is_last_prereq)

        return result

    def generate_manim_prompt(self):
        """从丰富化的树生成Manim可用的提示词"""
        if not self.current_tree or not hasattr(self.current_tree, 'narrative'):
            return "", "❌ 没有可用的丰富化树。请先运行丰富化。"

        try:
            narrative = self.current_tree.narrative.verbose_prompt
            return narrative, "✅ Manim提示词已生成！"
        except Exception as e:
            return "", f"❌ 错误: {str(e)}"

    def save_narrative(self, narrative, filepath):
        """将叙事保存到文件"""
        if not narrative.strip():
            return "❌ 没有可保存的叙事"

        try:
            Path(filepath).parent.mkdir(parents=True, exist_ok=True)
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(narrative)
            return f"✅ 叙事已保存到 {filepath}"
        except Exception as e:
            return f"❌ 保存错误: {str(e)}"

    # ============================================================================
    # 视频审查（来自Claude GUI）
    # ============================================================================

    def run_video_review(self, video_path: str) -> str:
        """对已渲染的视频调用VideoReview代理（来自Claude GUI）"""
        if VideoReviewAgent is None:
            return "VideoReviewAgent不可用。请检查src/agents导入。"

        try:
            video_review_agent = VideoReviewAgent()
            result = video_review_agent.review(Path(video_path))
            return (
                "视频审查完成。\n\n"
                f"帧目录: {result.frames_dir}\n"
                f"网页播放器: {result.web_player_path}\n"
                f"元数据: {result.metadata}\n"
            )
        except Exception as exc:
            return f"视频审查失败: {exc}"


# ============================================================================
# GRADIO界面（复刻Claude GUI结构）
# ============================================================================

def create_interface():
    """创建复刻Claude GUI的Gradio界面"""
    gui = KimiK2GUI()

    with gr.Blocks(theme=gr.themes.Soft(), title="Math-To-Manim - Kimi K2") as iface:
        gr.Markdown("# Math-To-Manim 生成器")
        gr.Markdown("*由 Moonshot AI 的 Kimi K2 思考模型驱动*")

        with gr.Tab("标准模式"):
            gr.Markdown("""
            ### 与 Kimi K2 聊天

            获得以下方面的帮助：
            - 理解数学概念
            - 生成 Manim 代码
            - 创建动画创意
            - 调试问题

            Kimi K2 已针对数学可视化和 Manim 代码生成进行了优化。
            """)

            chat_interface = gr.ChatInterface(
                gui.chat_with_kimi,
                examples=[
                    "生成可视化勾股定理的 Manim 代码",
                    "解释如何在 Manim 中动画化傅里叶级数",
                    "创建旋转环面的3D可视化",
                    "展示如何使用正确的 LaTeX 显示数学方程"
                ],
                title="",
                description=""
            )

        with gr.Tab("提示词扩展器"):
            gr.Markdown("""
            ### 将简单的想法转化为详细的提示词

            此模式将您的简单描述扩展为全面、
            富含 LaTeX 的提示词，适合生成高质量的 Manim 动画。
            """)

            simple_input = gr.Textbox(
                label="简单描述",
                placeholder="示例：用可视化证明展示勾股定理",
                lines=3
            )
            simple_submit = gr.Button("扩展提示词", variant="primary")
            detailed_output = gr.Textbox(
                label="详细的 Manim 提示词",
                lines=15,
                show_copy_button=True
            )

            simple_submit.click(
                fn=gui.process_simple_prompt,
                inputs=simple_input,
                outputs=detailed_output
            )

            gr.Examples(
                examples=[
                    "可视化量子纠缠",
                    "用动画解释傅里叶变换",
                    "几何方式展示微积分导数如何工作",
                    "动画化特征向量和特征值的概念"
                ],
                inputs=simple_input
            )

        with gr.Tab("知识树"):
            gr.Markdown("""
            ### Kimi K2 知识树系统

            Kimi K2 使用反向知识树推理，从基础概念构建到高级主题的动画。

            1. 输入要探索的概念
            2. Kimi 递归地发现先决条件概念
            3. 运行丰富化以添加方程和视觉规范
            4. 生成全面的 Manim 提示词
            """)

            with gr.Row():
                with gr.Column(scale=1):
                    concept_input = gr.Textbox(
                        label="要探索的概念",
                        placeholder="例如：量子力学、狭义相对论、微积分",
                        lines=1
                    )
                    max_depth = gr.Slider(
                        minimum=1,
                        maximum=5,
                        value=3,
                        step=1,
                        label="最大探索深度",
                        info="探索先决条件的深度"
                    )
                    use_tools = gr.Checkbox(
                        label="使用工具调用",
                        value=True,
                        info="启用工具调用以获得结构化输出"
                    )

                    explore_btn = gr.Button("🔍 探索概念", variant="primary")
                    enrich_btn = gr.Button("✨ 运行丰富化", variant="secondary")
                    generate_btn = gr.Button("🎬 生成 Manim 提示词", variant="secondary")

                    save_btn = gr.Button("💾 保存叙事", variant="secondary")
                    output_path = gr.Textbox(
                        label="保存路径",
                        placeholder="output/narrative.txt",
                        value="output/narrative.txt"
                    )

                    status_message = gr.Textbox(
                        label="状态",
                        lines=1,
                        interactive=False
                    )

                with gr.Column(scale=2):
                    tree_output = gr.Textbox(
                        label="知识树",
                        lines=15,
                        max_lines=20,
                        interactive=False,
                        show_copy_button=True
                    )

                    narrative_output = gr.Textbox(
                        label="生成的 Manim 叙事",
                        lines=15,
                        max_lines=25,
                        interactive=False,
                        show_copy_button=True
                    )

            # 知识树的事件处理器
            explore_btn.click(
                fn=lambda concept, depth, tools: gui.explore_concept(concept, depth, tools),
                inputs=[concept_input, max_depth, use_tools],
                outputs=[tree_output, status_message, narrative_output]
            )

            enrich_btn.click(
                fn=lambda: gui.run_enrichment(),
                inputs=[],
                outputs=[tree_output, narrative_output, status_message]
            )

            generate_btn.click(
                fn=lambda: gui.generate_manim_prompt(),
                inputs=[],
                outputs=[narrative_output, status_message]
            )

            save_btn.click(
                fn=lambda narrative, path: gui.save_narrative(narrative, path),
                inputs=[narrative_output, output_path],
                outputs=[status_message]
            )

        with gr.Tab("视频审查"):
            gr.Markdown("""
            ### 使用 Kimi K2 自动化后期渲染质量检查

            将动画渲染为MP4后，您可以将VideoReview代理指向它。

            代理将：
            - 提取帧到 `media/review_frames/<scene>/`
            - 生成HTML5审查播放器
            - 从ffprobe收集视频元数据
            """)

            review_input = gr.Textbox(
                label="已渲染的MP4路径",
                placeholder="media/videos/bhaskara_epic_manim/480p15/BhaskaraEpic.mp4",
                lines=1,
            )
            review_button = gr.Button("运行视频审查", variant="primary")
            review_output = gr.Textbox(label="代理输出", lines=6)

            review_button.click(
                fn=gui.run_video_review,
                inputs=review_input,
                outputs=review_output
            )

        with gr.Tab("关于"):
            gr.Markdown("""
            ## Math-To-Manim - Kimi K2 版本

            使用Kimi K2思考模型将数学概念转化为美丽的动画。

            ### 技术栈

            - **AI模型**: Kimi K2 思考模型 (Moonshot AI)
            - **API格式**: OpenAI兼容API
            - **动画**: Manim社区版 v0.19.0
            - **界面**: Gradio

            ### 核心创新：Kimi K2的反向知识树

            与传统AI系统不同，Kimi K2使用**递归概念分解**：

            1. 问"在理解X之前我必须知道什么？"
            2. 从基础构建完整的知识树
            3. 逐步生成教学动画
            4. 不需要训练数据 - 纯推理！

            ### Kimi K2 优势

            - **OpenAI兼容API**: 更容易集成和工具调用
            - **思考模式**: 透明地显示推理步骤
            - **工具接口**: 通过函数调用进行结构化数据提取
            - **LaTeX专注**: 擅长数学内容和方程

            ### 资源

            - [GitHub主仓库](https://github.com/HarleyCoops/Math-To-Manim)
            - [Kimi K2文档](KimiK2Thinking/README.md)
            - [Moonshot AI平台](https://platform.moonshot.cn/)

            ### 需要的环境变量

            ```bash
            MOONSHOT_API_KEY=您的kimi_api_key
            MOONSHOT_BASE_URL=https://api.moonshot.cn/v1
            ```

            从以下地址获取API密钥: [https://platform.moonshot.cn/](https://platform.moonshot.cn/)
            """)

        # 在加载时初始化代理
        iface.load(
            fn=lambda: gui.initialize_agents(),
            inputs=[],
            outputs=[status_message]
        )

    return iface


if __name__ == "__main__":
    print("""
╔═══════════════════════════════════════════════════════════════════╗
║             Math-To-Manim Web界面 - Kimi K2                      ║
║                                                                   ║
║  驱动: Kimi K2 思考模型 (Moonshot AI)                           ║
║  API格式: OpenAI兼容                                              ║
║                                                                   ║
║  正在启动Gradio界面...                                           ║
╚═══════════════════════════════════════════════════════════════════╝
    """)

    iface = create_interface()
    iface.launch(
        share=False,
        server_name="127.0.0.1",
        server_port=7861,
        show_error=True
    )
