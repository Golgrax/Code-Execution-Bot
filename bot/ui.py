import io
from typing import Optional, Tuple
import discord
from executor.models import ExecutionResult, ExecutionStatus
from analyzer.ast_analyzer import CodeAnalysisReport
from analyzer.multi_analyzer import analyze_code_generic

# Professional muted palette
COLOR_SUCCESS = discord.Color.from_rgb(46, 204, 113)     # Green
COLOR_ERROR = discord.Color.from_rgb(231, 76, 60)        # Red
COLOR_WARNING = discord.Color.from_rgb(230, 126, 34)     # Orange
COLOR_INFO = discord.Color.from_rgb(52, 73, 94)          # Formal Slate/Navy


def create_execution_embed(
    result: ExecutionResult,
    author: Optional[discord.User] = None,
) -> Tuple[discord.Embed, Optional[discord.File]]:
    """Build a formal, professional Discord Embed for execution results."""
    file_attachment = None

    lang_display = result.language.capitalize()

    if result.status == ExecutionStatus.SUCCESS:
        color = COLOR_SUCCESS
        title = f"Execution Result: {lang_display}"
        status_text = f"Completed (Exit Code: {result.exit_code if result.exit_code is not None else 0})"
    elif result.status == ExecutionStatus.TIMEOUT:
        color = COLOR_WARNING
        title = f"Execution Timeout: {lang_display}"
        status_text = "Timed Out (Time limit exceeded)"
    elif result.status == ExecutionStatus.COMPILATION_ERROR:
        color = COLOR_ERROR
        title = f"Compilation Error: {lang_display}"
        status_text = "Compilation Failed"
    elif result.status == ExecutionStatus.UNSUPPORTED:
        color = COLOR_WARNING
        title = f"Unsupported Language: {result.language}"
        status_text = "Language Not Supported"
    else:
        color = COLOR_ERROR
        title = f"Runtime Error: {lang_display}"
        status_text = f"Error (Exit Code: {result.exit_code if result.exit_code is not None else 1})"

    embed = discord.Embed(title=title, color=color)

    # Metadata fields
    embed.add_field(name="Status", value=status_text, inline=True)
    if result.execution_time_ms > 0:
        embed.add_field(name="Duration", value=f"{result.execution_time_ms:.1f} ms", inline=True)
    embed.add_field(name="Engine", value=result.engine, inline=True)

    # Standard Output / Standard Error
    output_text = result.stdout.strip()
    error_text = result.stderr.strip()

    if output_text:
        if len(output_text) > 1000:
            embed.add_field(
                name="Standard Output",
                value=f"```\n{output_text[:950]}\n... (Truncated. Full output attached)\n```",
                inline=False,
            )
            file_bytes = io.BytesIO(output_text.encode("utf-8"))
            file_attachment = discord.File(file_bytes, filename=f"output_{result.language}.txt")
        else:
            embed.add_field(
                name="Standard Output",
                value=f"```\n{output_text}\n```",
                inline=False,
            )

    if error_text:
        if len(error_text) > 1000:
            embed.add_field(
                name="Standard Error",
                value=f"```\n{error_text[:950]}\n... (Truncated. Full output attached)\n```",
                inline=False,
            )
            if not file_attachment:
                file_bytes = io.BytesIO(error_text.encode("utf-8"))
                file_attachment = discord.File(file_bytes, filename=f"error_{result.language}.txt")
        else:
            embed.add_field(
                name="Standard Error",
                value=f"```\n{error_text}\n```",
                inline=False,
            )

    if not output_text and not error_text:
        embed.add_field(
            name="Output",
            value="*(No output produced)*",
            inline=False,
        )

    if author:
        embed.set_footer(
            text=f"Requested by {author.display_name}",
            icon_url=author.display_avatar.url if author.display_avatar else None,
        )

    return embed, file_attachment


def create_analysis_embed(
    report: CodeAnalysisReport,
    author: Optional[discord.User] = None,
) -> discord.Embed:
    """Build a formal Discord embed presenting static code analysis."""
    color = COLOR_INFO if report.is_valid_syntax else COLOR_ERROR
    title = f"Static Code Analysis: {report.language.capitalize()}"
    embed = discord.Embed(title=title, description=report.summary_text, color=color)

    # Quantitative metrics
    embed.add_field(name="Lines of Code", value=f"{report.loc_code} code / {report.loc_total} total", inline=True)
    embed.add_field(name="Estimated Complexity", value=f"`{report.estimated_complexity}`", inline=True)
    embed.add_field(name="Branch Complexity", value=f"Score {report.cyclomatic_complexity}", inline=True)

    if not report.is_valid_syntax and report.syntax_error:
        embed.add_field(
            name="Syntax Error",
            value=f"```\n{report.syntax_error[:1000]}\n```",
            inline=False,
        )

    if report.classes:
        cls_text = "\n".join([f"• `{c.name}` ({len(c.methods)} methods)" for c in report.classes[:6]])
        embed.add_field(name="Classes and Structures", value=cls_text, inline=False)

    if report.functions:
        fn_text = "\n".join([
            f"• `{'async ' if f.is_async else ''}{f.name}({', '.join(f.args[:4])})`"
            + (" [recursive]" if f.is_recursive else "")
            for f in report.functions[:8]
        ])
        embed.add_field(name="Functions and Methods", value=fn_text, inline=False)

    if report.imports:
        embed.add_field(name="Dependencies", value=f"`{', '.join(report.imports[:8])}`", inline=False)

    if report.warnings:
        warn_text = "\n".join([f"• {w}" for w in report.warnings[:6]])
        embed.add_field(name="Static Warnings", value=warn_text, inline=False)

    if author:
        embed.set_footer(
            text=f"Requested by {author.display_name} • Static Analysis Engine",
            icon_url=author.display_avatar.url if author.display_avatar else None,
        )

    return embed


class ExecutionActionView(discord.ui.View):
    """Action controls for execution results."""

    def __init__(self, language: str, code: str, author_id: int):
        super().__init__(timeout=180)
        self.language = language
        self.code = code
        self.author_id = author_id

    @discord.ui.button(label="Analyze Code", style=discord.ButtonStyle.secondary)
    async def analyze_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        report = analyze_code_generic(self.language, self.code)
        embed = create_analysis_embed(report, interaction.user)
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @discord.ui.button(label="Dismiss", style=discord.ButtonStyle.secondary)
    async def delete_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        is_author = interaction.user.id == self.author_id
        can_manage = getattr(interaction.user.guild_permissions, "manage_messages", False) if interaction.guild else False

        if is_author or can_manage:
            await interaction.message.delete()
        else:
            await interaction.response.send_message("Only the command author may dismiss this result.", ephemeral=True)
