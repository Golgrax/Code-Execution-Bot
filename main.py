import asyncio
import logging
import os
import sys
from typing import Optional

import discord
from discord.ext import commands
from dotenv import load_dotenv

from analyzer.ast_analyzer import analyze_python_code
from analyzer.formatter import format_code
from analyzer.multi_analyzer import analyze_code_generic
from bot.parser import extract_code_and_language, normalize_language
from bot.ui import (
    COLOR_INFO,
    COLOR_WARNING,
    ExecutionActionView,
    create_analysis_embed,
    create_execution_embed,
)
from executor.manager import execute_code, get_available_languages
from keep_alive import keep_alive

# Load environment variables
load_dotenv()

# Setup formal logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("CodeExecutionBot")

# Configure Discord Intents
intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(
    command_prefix=commands.when_mentioned_or("!"),
    intents=intents,
    help_command=None,
)


def resolve_message_content(ctx: commands.Context, raw_input: str) -> str:
    """
    Extract raw code content preserving accurate multi-line indentation.
    Handles message replies and commands where code begins on subsequent lines.
    """
    if not raw_input.strip() and ctx.message.reference:
        ref_msg = ctx.message.reference.resolved
        if isinstance(ref_msg, discord.Message):
            return ref_msg.content

    full_msg = ctx.message.content
    lines = full_msg.splitlines()
    if lines:
        first_line = lines[0].lstrip()
        parts = first_line.split(None, 1)
        if parts:
            cmd_token = parts[0]
            idx = first_line.find(cmd_token) + len(cmd_token)
            rest_of_first = first_line[idx:]
            if rest_of_first.strip():
                # Content begins on the first line (e.g. !code python print(1))
                return rest_of_first + ("\n" + "\n".join(lines[1:]) if len(lines) > 1 else "")
            elif len(lines) > 1:
                # Content begins on subsequent line (e.g. !code\n        def primes(n):)
                # Preserves all leading indentation of lines 1 onwards
                return "\n".join(lines[1:])

    return raw_input


@bot.event
async def on_ready():
    logger.info(f"Bot connected as {bot.user} (ID: {bot.user.id})")
    try:
        synced = await bot.tree.sync()
        logger.info(f"Synchronized {len(synced)} application commands.")
    except Exception as e:
        logger.error(f"Failed to synchronize application commands: {e}")

    activity = discord.Activity(
        type=discord.ActivityType.watching,
        name="code executions | !help or /code",
    )
    await bot.change_presence(status=discord.Status.online, activity=activity)
    logger.info("Bot is ready and operational.")


# ==============================================================================
# Prefix Commands: !code / !run
# ==============================================================================
@bot.command(name="code", aliases=["run", "exec"])
async def cmd_code(ctx: commands.Context, *, content: str = ""):
    """Execute code in a sandboxed runtime environment."""
    raw_text = resolve_message_content(ctx, content)
    if not raw_text.strip():
        embed = discord.Embed(
            title="Code Execution Usage",
            description=(
                "**Command Syntax:**\n"
                "`!code <language> <code>`\n"
                "`!code ```<language>\n<code>\n``` `\n\n"
                "**Local Sandbox Runtimes:**\n"
                "Python, JavaScript (Node.js), Bash, C, C++, Go, PHP, Java\n\n"
                "Use `!langs` to inspect all supported runtimes."
            ),
            color=COLOR_INFO,
        )
        await ctx.reply(embed=embed, mention_author=False)
        return

    lang, code = extract_code_and_language(raw_text)

    # Markup beautifiers
    if lang in ("html", "xml", "svg", "css", "json"):
        ok, res = format_code(lang, code)
        if ok:
            embed = discord.Embed(title=f"Formatted {lang.upper()}", color=COLOR_INFO)
            embed.description = f"```{lang}\n{res[:1900]}\n```"
            await ctx.reply(embed=embed, mention_author=False)
            return

    async with ctx.typing():
        result = await execute_code(language=lang, code=code)
        embed, file_att = create_execution_embed(result, ctx.author)
        view = ExecutionActionView(language=lang, code=code, author_id=ctx.author.id)
        
        kwargs = {"embed": embed, "view": view, "mention_author": False}
        if file_att:
            kwargs["file"] = file_att
        await ctx.reply(**kwargs)


# ==============================================================================
# Prefix Command: !analyze / !inspect
# ==============================================================================
@bot.command(name="analyze", aliases=["inspect", "ast", "explain"])
async def cmd_analyze(ctx: commands.Context, *, content: str = ""):
    """Perform static code inspection without external language models."""
    raw_text = resolve_message_content(ctx, content)
    if not raw_text.strip():
        embed = discord.Embed(
            title="Static Code Analysis",
            description=(
                "Performs structural static analysis and linting without external APIs or LLMs:\n"
                "• Exact line and column syntax error verification\n"
                "• Abstract Syntax Tree mapping (Functions, Classes, Methods, Imports)\n"
                "• Algorithmic complexity and loop nesting heuristics\n"
                "• Static anti-pattern and bug warning detection\n\n"
                "**Usage:** `!analyze <language> <code>` or reply to a code block with `!analyze`."
            ),
            color=COLOR_INFO,
        )
        await ctx.reply(embed=embed, mention_author=False)
        return

    lang, code = extract_code_and_language(raw_text)
    report = analyze_code_generic(lang, code)
    embed = create_analysis_embed(report, ctx.author)
    await ctx.reply(embed=embed, mention_author=False)


# ==============================================================================
# Prefix Command: !format / !beautify
# ==============================================================================
@bot.command(name="format", aliases=["beautify", "fmt"])
async def cmd_format(ctx: commands.Context, *, content: str = ""):
    """Format and prettify markup or source code."""
    raw_text = resolve_message_content(ctx, content)
    if not raw_text.strip():
        embed = discord.Embed(
            title="Code Formatter",
            description="Usage: `!format <html|json|python|css> <code>`",
            color=COLOR_INFO,
        )
        await ctx.reply(embed=embed, mention_author=False)
        return

    lang, code = extract_code_and_language(raw_text)
    ok, res = format_code(lang, code)
    if not ok:
        await ctx.reply(f"Error: {res}", mention_author=False)
        return

    embed = discord.Embed(title=f"Formatted {lang.upper()}", color=COLOR_INFO)
    if len(res) > 1900:
        res = res[:1900] + "\n... (Truncated)"
    embed.description = f"```{lang}\n{res}\n```"
    await ctx.reply(embed=embed, mention_author=False)


# ==============================================================================
# Prefix Command: !langs / !languages
# ==============================================================================
@bot.command(name="langs", aliases=["languages"])
async def cmd_langs(ctx: commands.Context):
    """Catalog of available execution environments."""
    langs = get_available_languages()
    embed = discord.Embed(
        title="Supported Programming Languages",
        description="Local execution operates in native sandbox isolation without API requirements.",
        color=COLOR_INFO,
    )
    embed.add_field(
        name="Local Sandbox Runtimes",
        value=", ".join(f"`{l}`" for l in langs["local"]) or "None",
        inline=False,
    )
    embed.add_field(
        name="Cloud Runtimes",
        value=", ".join(f"`{l}`" for l in langs["cloud_free"][:20]) + "...",
        inline=False,
    )
    embed.add_field(
        name="Supported Formatters",
        value="`html`, `json`, `css`, `xml`, `python`",
        inline=False,
    )
    await ctx.reply(embed=embed, mention_author=False)


# ==============================================================================
# Prefix Command: !ping
# ==============================================================================
@bot.command(name="ping")
async def cmd_ping(ctx: commands.Context):
    """Report bot gateway latency."""
    latency_ms = round(bot.latency * 1000, 2)
    embed = discord.Embed(
        title="Gateway Latency",
        description=f"Heartbeat: `{latency_ms} ms`\nExecution Engine: `Active`",
        color=COLOR_INFO,
    )
    await ctx.reply(embed=embed, mention_author=False)


# ==============================================================================
# Prefix Command: !help
# ==============================================================================
@bot.command(name="help")
async def cmd_help(ctx: commands.Context):
    """Display bot command manual."""
    embed = discord.Embed(
        title="Code Execution and Static Analysis Manual",
        description="Execution, inspection, and formatting environment.",
        color=COLOR_INFO,
    )
    embed.add_field(
        name="Code Execution",
        value=(
            "`!code <language> <code>` or `/code`\n"
            "Runs code in an isolated sandbox.\n"
            "Example: `!code python print(2 ** 10)`"
        ),
        inline=False,
    )
    embed.add_field(
        name="Static Code Analysis",
        value=(
            "`!analyze <language> <code>` or `/analyze`\n"
            "Inspects AST, functions, classes, loop depth, complexity, and warnings without LLMs."
        ),
        inline=False,
    )
    embed.add_field(
        name="Code Formatting",
        value=(
            "`!format <html|json|css|py> <code>` or `/format`\n"
            "Structures and prettifies code or markup."
        ),
        inline=False,
    )
    embed.add_field(
        name="Utilities",
        value="`!langs` - Inspect supported runtimes\n`!ping` - Report latency\n`!help` - Display this manual",
        inline=False,
    )
    embed.set_footer(text="Message replies are supported for !code and !analyze.")
    await ctx.reply(embed=embed, mention_author=False)


# ==============================================================================
# Slash Commands (/code, /analyze, /format, /langs, /ping, /help)
# ==============================================================================
@bot.tree.command(name="code", description="Execute code in a sandboxed runtime")
async def slash_code(
    interaction: discord.Interaction,
    language: str,
    code: str,
    stdin: Optional[str] = "",
):
    await interaction.response.defer()
    result = await execute_code(language=language, code=code, stdin=stdin or "")
    embed, file_att = create_execution_embed(result, interaction.user)
    view = ExecutionActionView(language=language, code=code, author_id=interaction.user.id)
    
    kwargs = {"embed": embed, "view": view}
    if file_att:
        kwargs["file"] = file_att
    await interaction.followup.send(**kwargs)


@bot.tree.command(name="analyze", description="Perform static code analysis without LLMs")
async def slash_analyze(interaction: discord.Interaction, language: str, code: str):
    await interaction.response.defer()
    report = analyze_code_generic(language, code)
    embed = create_analysis_embed(report, interaction.user)
    await interaction.followup.send(embed=embed)


@bot.tree.command(name="format", description="Format HTML, JSON, CSS, or Python code")
async def slash_format(interaction: discord.Interaction, language: str, code: str):
    ok, res = format_code(language, code)
    if not ok:
        await interaction.response.send_message(f"Error: {res}", ephemeral=True)
        return
    embed = discord.Embed(title=f"Formatted {language.upper()}", color=COLOR_INFO)
    embed.description = f"```{language}\n{res[:1900]}\n```"
    await interaction.response.send_message(embed=embed)


@bot.tree.command(name="langs", description="Catalog of supported programming languages")
async def slash_langs(interaction: discord.Interaction):
    langs = get_available_languages()
    embed = discord.Embed(
        title="Supported Programming Languages",
        description="Local execution operates in native sandbox isolation without API requirements.",
        color=COLOR_INFO,
    )
    embed.add_field(
        name="Local Sandbox Runtimes",
        value=", ".join(f"`{l}`" for l in langs["local"]) or "None",
        inline=False,
    )
    embed.add_field(
        name="Cloud Runtimes",
        value=", ".join(f"`{l}`" for l in langs["cloud_free"][:20]) + "...",
        inline=False,
    )
    await interaction.response.send_message(embed=embed)


@bot.tree.command(name="ping", description="Report gateway latency")
async def slash_ping(interaction: discord.Interaction):
    latency_ms = round(bot.latency * 1000, 2)
    await interaction.response.send_message(f"Heartbeat latency: {latency_ms} ms. Engine: Active.")


@bot.tree.command(name="help", description="Show bot commands and documentation")
async def slash_help(interaction: discord.Interaction):
    embed = discord.Embed(
        title="Code Execution and Static Analysis Manual",
        description="Execution, inspection, and formatting environment.",
        color=COLOR_INFO,
    )
    embed.add_field(
        name="Commands",
        value=(
            "`/code <language> <code>` - Execute code snippet\n"
            "`/analyze <language> <code>` - Perform static code analysis\n"
            "`/format <language> <code>` - Format source or markup\n"
            "`/langs` - List all supported runtimes"
        ),
        inline=False,
    )
    await interaction.response.send_message(embed=embed)


# ==============================================================================
# Error Handler
# ==============================================================================
@bot.event
async def on_command_error(ctx: commands.Context, error: Exception):
    if isinstance(error, commands.CommandNotFound):
        return
    elif isinstance(error, commands.MissingRequiredArgument):
        await ctx.reply(f"Missing required argument: `{error.param.name}`. Type `!help` for manual.", mention_author=False)
    else:
        logger.error(f"Command error: {error}", exc_info=True)
        await ctx.reply(f"An error occurred during execution: `{error}`", mention_author=False)


# ==============================================================================
# Main Entry Point
# ==============================================================================
def main():
    token = os.getenv("DISCORD_TOKEN")
    if not token or token == "your_discord_bot_token":
        logger.error("DISCORD_TOKEN environment variable is not defined.")
        sys.exit(1)

    keep_alive()

    logger.info("Starting Code Execution Bot...")
    try:
        bot.run(token)
    except discord.errors.LoginFailure:
        logger.critical("Authentication failure: Invalid Discord bot token.")
        sys.exit(1)
    except Exception as e:
        logger.critical(f"Fatal error during runtime: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
