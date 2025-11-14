"""
Kimi K2 Web Interface for Math-To-Manim
Complete Gradio interface with all features from Claude GUI
Powered by Kimi K2 thinking model from Moonshot AI
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
    """Complete web interface for Kimi K2 integration with all features"""

    def __init__(self):
        """Initialize the GUI with Kimi K2 agents"""
        self.explorer = None
        self.pipeline = None
        self.manim_client = None
        self.current_tree = None
        self.chat_client = None

    def initialize_agents(self, use_tools=True, max_depth=3):
        """Initialize Kimi K2 agents"""
        try:
            self.explorer = KimiPrerequisiteExplorer(
                max_depth=max_depth,
                use_tools=use_tools
            )
            self.pipeline = KimiEnrichmentPipeline()
            self.manim_client = KimiClient()
            self.chat_client = KimiClient()
            return "✅ Kimi K2 agents initialized successfully!"
        except Exception as e:
            return f"❌ Error initializing agents: {str(e)}"

    # ============================================================================
    # CHAT INTERFACE (from Claude GUI)
    # ============================================================================

    def chat_with_kimi(self, message, history):
        """
        Chat with Kimi K2 for generating Manim code or discussing concepts.
        Mirrors Claude GUI's chat functionality.
        """
        # Convert history to the format expected by the API
        messages = []
        for human, assistant in history:
            messages.append({"role": "user", "content": human})
            if assistant:
                messages.append({"role": "assistant", "content": assistant})
        messages.append({"role": "user", "content": message})

        system_prompt = """You are an expert Manim animator and mathematics educator.

You help users:
1. Understand mathematical concepts
2. Generate Manim Community Edition code for animations
3. Create detailed animation prompts
4. Debug Manim code issues
5. Suggest visual representations for mathematical ideas

When generating Manim code:
- Use proper imports: from manim import *
- Define Scene classes with construct() method
- Use LaTeX for mathematical expressions (raw strings)
- Provide comments explaining the animation logic
- Use appropriate colors and positioning
- Include timing information (wait, play durations)

Always format LaTeX with proper escaping and use MathTex() for equations."""

        # Call the Kimi K2 API
        try:
            response = self.chat_client.chat_completion(
                messages=messages,
                max_tokens=4000,
                system=system_prompt
            )

            answer = self.format_latex(self.chat_client.get_text_content(response))
            return answer
        except Exception as e:
            return f"Error: {str(e)}"

    # ============================================================================
    # PROMPT EXPANDER (from Claude GUI)
    # ============================================================================

    def format_latex(self, text):
        """Format inline LaTeX expressions for proper rendering in Gradio (from Claude GUI)"""
        # Replace single dollar signs with double for better display
        lines = text.split('\n')
        formatted_lines = []

        for line in lines:
            # Skip lines that already have double dollars
            if '$$' in line:
                formatted_lines.append(line)
                continue

            # Format single dollar expressions
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
        Transform simple ideas into detailed Manim prompts.
        Mirrors Claude GUI's Prompt Expander.
        """
        if not simple_prompt.strip():
            return "Please enter a prompt to expand."

        system_prompt = """You are an expert at creating detailed, LaTeX-rich prompts for Manim animations.

Transform the user's simple description into a comprehensive, 2000+ token prompt that:
1. Specifies every visual element (colors, positions, sizes)
2. Uses proper LaTeX formatting for all equations
3. Provides sequential instructions ("Begin by...", "Next...", "Then...")
4. Maintains visual continuity between scenes
5. Includes timing information
6. Specifies camera movements
7. Color-codes mathematical objects consistently

The output should be detailed enough for an AI to generate working Manim Community Edition code."""

        try:
            response = self.manim_client.chat_completion(
                messages=[{"role": "user", "content": f"Create a detailed Manim animation prompt for: {simple_prompt}"}],
                max_tokens=4000,
                system=system_prompt
            )

            return self.format_latex(self.manim_client.get_text_content(response))
        except Exception as e:
            return f"Error: {str(e)}"

    # ============================================================================
    # KNOWLEDGE TREE (original Kimi K2 feature)
    # ============================================================================

    def explore_concept(self, concept, max_depth=3, use_tools=True):
        """Explore a concept and build knowledge tree"""
        if not concept.strip():
            return "", "", "❌ Please enter a concept to explore"

        try:
            # Reinitialize with current settings
            self.initialize_agents(use_tools=use_tools, max_depth=max_depth)

            # Run exploration
            tree = asyncio.run(self.explorer.explore_async(concept, verbose=False))
            self.current_tree = tree

            # Format tree for display
            tree_text = self.format_tree_display(tree)

            return tree_text, f"✅ Successfully explored '{concept}'", ""

        except Exception as e:
            return "", f"❌ Error exploring concept: {str(e)}", ""

    def format_tree_display(self, node, prefix="", is_last=True):
        """Format knowledge tree for text display"""
        connector = "└─ " if is_last else "├─ "
        foundation_marker = " [FOUNDATION]" if node.is_foundation else ""
        result = f"{prefix}{connector}{node.concept} (depth {node.depth}){foundation_marker}\n"

        if node.prerequisites:
            new_prefix = prefix + ("   " if is_last else "│  ")
            for i, prereq in enumerate(node.prerequisites):
                is_last_prereq = (i == len(node.prerequisites) - 1)
                result += self.format_tree_display(prereq, new_prefix, is_last_prereq)

        return result

    def run_enrichment(self):
        """Run enrichment pipeline on current tree"""
        if not self.current_tree:
            return "", "", "❌ No knowledge tree to enrich. Please explore a concept first."

        try:
            result = asyncio.run(self.pipeline.run_async(self.current_tree))
            enriched_tree = self.format_enriched_tree_display(self.current_tree)
            narrative = result.narrative.verbose_prompt if result.narrative else "No narrative generated"
            return enriched_tree, narrative, "✅ Enrichment completed!"
        except Exception as e:
            return "", "", f"❌ Error during enrichment: {str(e)}"

    def format_enriched_tree_display(self, node, prefix="", is_last=True):
        """Format enriched tree with mathematical content"""
        connector = "└─ " if is_last else "├─ "
        foundation_marker = " [FOUNDATION]" if node.is_foundation else ""
        result = f"{prefix}{connector}{node.concept} (depth {node.depth}){foundation_marker}\n"

        if hasattr(node, 'equations') and node.equations:
            eq_prefix = prefix + ("   " if is_last else "│  ")
            result += f"{eq_prefix}  📐 Equations: {len(node.equations)}\n"

        if hasattr(node, 'visual_spec') and node.visual_spec:
            eq_prefix = prefix + ("   " if is_last else "│  ")
            result += f"{eq_prefix}  🎨 Visual elements: {len(node.visual_spec.elements)}\n"

        if node.prerequisites:
            new_prefix = prefix + ("   " if is_last else "│  ")
            for i, prereq in enumerate(node.prerequisites):
                is_last_prereq = (i == len(node.prerequisites) - 1)
                result += self.format_enriched_tree_display(prereq, new_prefix, is_last_prereq)

        return result

    def generate_manim_prompt(self):
        """Generate Manim-ready prompt from enriched tree"""
        if not self.current_tree or not hasattr(self.current_tree, 'narrative'):
            return "", "❌ No enriched tree available. Please run enrichment first."

        try:
            narrative = self.current_tree.narrative.verbose_prompt
            return narrative, "✅ Manim prompt generated!"
        except Exception as e:
            return "", f"❌ Error: {str(e)}"

    def save_narrative(self, narrative, filepath):
        """Save narrative to file"""
        if not narrative.strip():
            return "❌ No narrative to save"

        try:
            Path(filepath).parent.mkdir(parents=True, exist_ok=True)
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(narrative)
            return f"✅ Narrative saved to {filepath}"
        except Exception as e:
            return f"❌ Error saving: {str(e)}"

    # ============================================================================
    # VIDEO REVIEW (from Claude GUI)
    # ============================================================================

    def run_video_review(self, video_path: str) -> str:
        """Invoke the VideoReview agent on a rendered video (from Claude GUI)"""
        if VideoReviewAgent is None:
            return "VideoReviewAgent not available. Please check src/agents imports."

        try:
            video_review_agent = VideoReviewAgent()
            result = video_review_agent.review(Path(video_path))
            return (
                "Video review completed.\n\n"
                f"Frames directory: {result.frames_dir}\n"
                f"Web player: {result.web_player_path}\n"
                f"Metadata: {result.metadata}\n"
            )
        except Exception as exc:
            return f"Video review failed: {exc}"


# ============================================================================
# GRADIO INTERFACE (mirroring Claude GUI structure)
# ============================================================================

def create_interface():
    """Create Gradio interface mirroring Claude GUI"""
    gui = KimiK2GUI()

    with gr.Blocks(theme=gr.themes.Soft(), title="Math-To-Manim - Kimi K2") as iface:
        gr.Markdown("# Math-To-Manim Generator")
        gr.Markdown("*Powered by Kimi K2 Thinking Model from Moonshot AI*")

        with gr.Tab("Standard Mode"):
            gr.Markdown("""
            ### Chat with Kimi K2

            Get help with:
            - Understanding mathematical concepts
            - Generating Manim code
            - Creating animation ideas
            - Debugging issues

            Kimi K2 has been optimized for mathematical visualization and Manim code generation.
            """)

            chat_interface = gr.ChatInterface(
                gui.chat_with_kimi,
                examples=[
                    "Generate Manim code to visualize the Pythagorean theorem",
                    "Explain how to animate a Fourier series in Manim",
                    "Create a 3D visualization of a rotating torus",
                    "Show me how to display mathematical equations with proper LaTeX"
                ],
                title="",
                description=""
            )

        with gr.Tab("Prompt Expander"):
            gr.Markdown("""
            ### Transform Simple Ideas into Detailed Prompts

            This mode takes your simple description and expands it into a comprehensive,
            LaTeX-rich prompt suitable for generating high-quality Manim animations.
            """)

            simple_input = gr.Textbox(
                label="Simple Description",
                placeholder="Example: Show the Pythagorean theorem with a visual proof",
                lines=3
            )
            simple_submit = gr.Button("Expand Prompt", variant="primary")
            detailed_output = gr.Textbox(
                label="Detailed Manim Prompt",
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
                    "Visualize quantum entanglement",
                    "Explain the Fourier transform with animations",
                    "Show how calculus derivatives work geometrically",
                    "Animate the concept of eigenvectors and eigenvalues"
                ],
                inputs=simple_input
            )

        with gr.Tab("Knowledge Tree"):
            gr.Markdown("""
            ### Kimi K2 Knowledge Tree System

            Kimi K2 uses reverse knowledge tree reasoning to build animations from foundational concepts up to advanced topics.

            1. Enter a concept to explore
            2. Kimi discovers prerequisite concepts recursively
            3. Run enrichment to add equations and visual specs
            4. Generate comprehensive Manim prompts
            """)

            with gr.Row():
                with gr.Column(scale=1):
                    concept_input = gr.Textbox(
                        label="Concept to Explore",
                        placeholder="e.g., quantum mechanics, special relativity, calculus",
                        lines=1
                    )
                    max_depth = gr.Slider(
                        minimum=1,
                        maximum=5,
                        value=3,
                        step=1,
                        label="Max Exploration Depth",
                        info="How deep to explore prerequisites"
                    )
                    use_tools = gr.Checkbox(
                        label="Use Tool Calling",
                        value=True,
                        info="Enable tool calling for structured output"
                    )

                    explore_btn = gr.Button("🔍 Explore Concept", variant="primary")
                    enrich_btn = gr.Button("✨ Run Enrichment", variant="secondary")
                    generate_btn = gr.Button("🎬 Generate Manim Prompt", variant="secondary")

                    save_btn = gr.Button("💾 Save Narrative", variant="secondary")
                    output_path = gr.Textbox(
                        label="Save Path",
                        placeholder="output/narrative.txt",
                        value="output/narrative.txt"
                    )

                    status_message = gr.Textbox(
                        label="Status",
                        lines=1,
                        interactive=False
                    )

                with gr.Column(scale=2):
                    tree_output = gr.Textbox(
                        label="Knowledge Tree",
                        lines=15,
                        max_lines=20,
                        interactive=False,
                        show_copy_button=True
                    )

                    narrative_output = gr.Textbox(
                        label="Generated Manim Narrative",
                        lines=15,
                        max_lines=25,
                        interactive=False,
                        show_copy_button=True
                    )

            # Event handlers for knowledge tree
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

        with gr.Tab("Video Review"):
            gr.Markdown("""
            ### Automate Post-Render QA with Kimi K2

            Once your animation is rendered to MP4, you can point the VideoReview agent at it.

            The agent will:
            - extract frames into `media/review_frames/<scene>/`
            - generate an HTML5 review player
            - collect video metadata from ffprobe
            """)

            review_input = gr.Textbox(
                label="Path to rendered MP4",
                placeholder="media/videos/bhaskara_epic_manim/480p15/BhaskaraEpic.mp4",
                lines=1,
            )
            review_button = gr.Button("Run Video Review", variant="primary")
            review_output = gr.Textbox(label="Agent Output", lines=6)

            review_button.click(
                fn=gui.run_video_review,
                inputs=review_input,
                outputs=review_output
            )

        with gr.Tab("About"):
            gr.Markdown("""
            ## Math-To-Manim - Kimi K2 Edition

            Transform mathematical concepts into beautiful animations using Kimi K2 thinking model.

            ### Technology Stack

            - **AI Model**: Kimi K2 Thinking Model (Moonshot AI)
            - **API Format**: OpenAI-compatible API
            - **Animation**: Manim Community Edition v0.19.0
            - **Interface**: Gradio

            ### Key Innovation: Reverse Knowledge Tree with Kimi K2

            Unlike traditional AI systems, Kimi K2 uses **recursive conceptual decomposition**:

            1. Ask "What must I understand BEFORE X?"
            2. Build a complete knowledge tree from foundations
            3. Generate animations that teach progressively
            4. No training data required - pure reasoning!

            ### Kimi K2 Advantages

            - **OpenAI-compatible API**: Easier integration and tool calling
            - **Thinking Mode**: Shows reasoning steps transparently
            - **Tool Interface**: Structured data extraction via function calling
            - **LaTeX Focus**: Excellent at mathematical content and equations

            ### Resources

            - [Main GitHub Repository](https://github.com/HarleyCoops/Math-To-Manim)
            - [Kimi K2 Documentation](KimiK2Thinking/README.md)
            - [Moonshot AI Platform](https://platform.moonshot.cn/)

            ### Environment Variables Required

            ```bash
            MOONSHOT_API_KEY=your_kimi_api_key_here
            MOONSHOT_BASE_URL=https://api.moonshot.cn/v1
            ```

            Get your API key from: [https://platform.moonshot.cn/](https://platform.moonshot.cn/)
            """)

        # Initialize agents on load
        iface.load(
            fn=lambda: gui.initialize_agents(),
            inputs=[],
            outputs=[status_message]
        )

    return iface


if __name__ == "__main__":
    print("""
╔═══════════════════════════════════════════════════════════════════╗
║             Math-To-Manim Web Interface - Kimi K2                ║
║                                                                   ║
║  Powered by: Kimi K2 Thinking Model (Moonshot AI)               ║
║  API Format: OpenAI-compatible                                   ║
║                                                                   ║
║  Starting Gradio interface...                                    ║
╚═══════════════════════════════════════════════════════════════════╝
    """)

    iface = create_interface()
    iface.launch(
        share=False,
        server_name="127.0.0.1",
        server_port=7861,
        show_error=True
    )
