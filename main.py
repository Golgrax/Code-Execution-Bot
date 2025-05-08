import discord
import io
import traceback
import re
import requests
import os
import jsbeautifier
import js2py
from contextlib import redirect_stdout
from dotenv import load_dotenv
from keep_alive import keep_alive

load_dotenv()

# Environment variables
CLIENT_SECRET = os.getenv("CLIENT_SECRET")
CLIENT_ID = os.getenv("CLIENT_ID")
BOT_TOKEN = os.getenv("BOT_TOKEN")

# Discord intents
intents = discord.Intents.default()
intents.message_content = True
bot = discord.Client(intents=intents)

# Send output, handling large content
async def send_output(message, output, language):
    if len(output) > 1900:  # Discord limit ~2000 chars
        with io.StringIO(output) as f:
            await message.channel.send(file=discord.File(f, f"output.{language}"))
    else:
        await message.channel.send(f"Output:\n```{language}\n{output}\n```")

# Execute code via JDoodle API
async def execute_jdoodle(language, code):
    url = "https://api.jdoodle.com/v1/execute"
    data = {
        "clientId": CLIENT_ID,
        "clientSecret": CLIENT_SECRET,
        "script": code,
        "language": language,
        "versionIndex": "0"
    }
    try:
        response = requests.post(url, json=data)
        response_data = response.json()
        if response_data['statusCode'] == 200:
            return response_data['output']
        else:
            return f"Error: {response_data.get('message', 'Unknown error')}"
    except Exception as e:
        return f"JDoodle API Error: {str(e)}"

# Language handlers
async def handle_python(message, code):
    try:
        with io.StringIO() as buf, redirect_stdout(buf):
            exec(code)
            output = buf.getvalue().strip()
        if output:
            await send_output(message, output, 'python')
        else:
            await message.channel.send("No output.")
    except SyntaxError as e:
        await message.channel.send(f"Syntax Error: {e}\nSuggestion: Check for typos or incorrect syntax.")
    except NameError as e:
        await message.channel.send(f"Name Error: {e}\nSuggestion: Ensure all variables are defined.")
    except Exception as e:
        await message.channel.send(f"Error:\n```{traceback.format_exc()}```")

async def handle_javascript(message, code):
    try:
        result = js2py.eval_js(code)
        await send_output(message, str(result), 'javascript')
    except Exception as e:
        await message.channel.send(f"Error:\n```{traceback.format_exc()}```")

async def handle_html(message, code):
    try:
        beautified = jsbeautifier.beautify(code, {"indent_size": 2})
        await send_output(message, beautified, 'html')
    except Exception as e:
        await message.channel.send(f"Error:\n```{traceback.format_exc()}```")

async def handle_css(message, code):
    try:
        beautified = jsbeautifier.beautify(code, {"indent_size": 2})
        await send_output(message, beautified, 'css')
    except Exception as e:
        await message.channel.send(f"Error:\n```{traceback.format_exc()}```")

async def handle_java(message, code):
    output = await execute_jdoodle('java', code)
    await send_output(message, output, 'java')

async def handle_ruby(message, code):
    output = await execute_jdoodle('ruby', code)
    await send_output(message, output, 'ruby')

async def handle_go(message, code):
    output = await execute_jdoodle('go', code)
    await send_output(message, output, 'go')

# Handler mapping
handlers = {
    'python': handle_python,
    'javascript': handle_javascript,
    'html': handle_html,
    'css': handle_css,
    'java': handle_java,
    'ruby': handle_ruby,
    'go': handle_go,
}

@bot.event
async def on_message(message):
    if message.author.bot:
        return

    if message.content.startswith('!code'):
        content = message.content[5:].strip()
        if content == 'help':
            help_message = """
            **Usage**: `!code`
            ```
            language
            your code here
            ```
            **Supported languages**: python, javascript, html, css, java, ruby, go
            **Example**:
            ```
            !code
            ```python
            print("Hello, World!")
            ```
            ```
            """
            await message.channel.send(help_message)
            return

        match = re.search(r'```(\w+)\n([\s\S]*?)\n```', content)
        if match:
            language = match.group(1).lower()
            code = match.group(2)
            if language in handlers:
                await handlers[language](message, code)
            else:
                await message.channel.send("Unsupported language. Use `!code help` for supported languages.")
        else:
            await message.channel.send("Please provide a code block with the language specified. See `!code help`.")

# Warning: Python and JavaScript execute locally; use a sandboxed environment for safety
keep_alive()
bot.run(BOT_TOKEN)