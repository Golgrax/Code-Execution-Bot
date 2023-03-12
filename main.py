# https://discord.gg/developers

import discord
import io
import traceback
from contextlib import redirect_stdout

import subprocess
import jsbeautifier
import js2py
import pygments
import pygments.formatters
import pygments.lexers
import requests
import os
from dotenv import load_dotenv
from keep_alive import keep_alive


load_dotenv()

# JDoodle API Client Secret
CLIENT_SECRET = os.getenv("CLIENT_SECRET")

# JDoodle API Client ID
CLIENT_ID = os.getenv("CLIENT_ID")

# Discord Bot Token
BOT_TOKEN = os.getenv("BOT_TOKEN")

intents = discord.Intents.default()
intents.members = True
bot = discord.Client(intents=intents)

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user.name}")

@bot.event
async def on_message(message):
    if message.author.bot:
        return

    if message.content.startswith("!code"):
        code = message.content[6:].strip()
        language = code.split("\n")[0].strip()

        if language == "python":
            # Redirect output to buffer
            with io.StringIO() as buf, redirect_stdout(buf):
                try:
                    # Execute Python code
                    exec("\n".join(code.split("\n")[1:]))

                    # Get output from buffer
                    output = buf.getvalue().strip()

                    # Send output to user
                    output_block = f"```py\n{output}\n```"
                    await message.channel.send(f"Output:\n{output_block}")
                except Exception as e:
                    # Send error message and suggestion to user
                    error_message = f"```{traceback.format_exc()}```"
                    suggestion = f"Here's a suggestion to fix the error: {e}"
                    await message.channel.send(f"Error:\n{error_message}\n{suggestion}")

        elif language == "javascript":
            try:
                # Evaluate JavaScript code using js2py
                result = js2py.eval_js(code.split("\n")[1:].join("\n"))

                # Send output to user
                output_block = f"```js\n{result}\n```"
                await message.channel.send(f"Output:\n{output_block}")
            except Exception as e:
                # Send error message and suggestion to user
                error_message = f"```{traceback.format_exc()}```"
                suggestion = f"Here's a suggestion to fix the error: {e}"
                await message.channel.send(f"Error:\n{error_message}\n{suggestion}")

        elif language == "html":
            try:
                # Beautify HTML code using jsbeautifier
                beautified_html = jsbeautifier.beautify(code, {"indent_size": 2})

                # Highlight HTML code using Pygments
                lexer = pygments.lexers.get_lexer_by_name("html")
                formatter = pygments.formatters.get_formatter_by_name("html", style="colorful") 
                highlighted_html = pygments.highlight(beautified_html, lexer, formatter)

                # Send output to user
                output_block = f"```html\n{highlighted_html}\n```"
                await message.channel.send(f"Output:\n{output_block}")
            except Exception as e:
                # Send error message and suggestion to user
                error_message = f"```{traceback.format_exc()}```"
                suggestion = f"Here's a suggestion to fix the error: {e}"
                await message.channel.send(f"Error:\n{error_message}\n{suggestion}")

        elif language == "css":
            try:
                # Beautify CSS code using jsbeautifier
                beautified_css = jsbeautifier.beautify(code, {"indent_size": 2})

                # Highlight CSS code using Pygments
                lexer = pygments.lexers.get_lexer_by_name("css")
                formatter = pygments.formatters.get_formatter_by_name("html", style="colorful") 
                highlighted_css = pygments.highlight(beautified_css, lexer, formatter)

                # Send output to user
                output_block = f"```{highlighted_css}```"
                await message.channel.send(f"Output:\n{output_block}")
            except Exception as e:
                # Send error message and suggestion to user
                error_message = f"```{traceback.format_exc()}```"
                suggestion = f"Here's a suggestion to fix the error: {e}"
                await message.channel.send(f"Error:\n{error_message}\n{suggestion}")

        elif language == "java":
            try:
                # Compile Java code using JDoodle API
                url = "https://api.jdoodle.com/v1/execute"
                data = {
                    "clientId": CLIENT_ID,
                    "clientSecret": CLIENT_SECRET,
                    "script": code,
                    "language": "java",
                    "versionIndex": "3"
                }
                response = requests.post(url, json=data)
                response_data = response.json()

                # Check for compilation errors
                if "Compilation Error" in response_data["output"]:
                    output = response_data["output"]
                else:
                    # Get program output
                    output = response_data["output"].replace("\n", "\n")

                # Send output to user
                output_block = f"```{output}```"
                await message.channel.send(f"Output:\n{output_block}")
            except Exception as e:
                # Send error message and suggestion to user
                error_message = f"```{traceback.format_exc()}```"
                suggestion = f"Here's a suggestion to fix the error: {e}"
                await message.channel.send(f"Error:\n{error_message}\n{suggestion}")

        elif language == "ruby":
            try:
                # Highlight Ruby code using Pygments
                lexer = pygments.lexers.get_lexer_by_name("ruby")
                formatter = pygments.formatters.get_formatter_by_name("html", style="colorful") 
                highlighted_ruby = pygments.highlight(code, lexer, formatter)

                # Send output to user
                output_block = f"```{highlighted_ruby}```"
                await message.channel.send(f"Output:\n{output_block}")
            except Exception as e:
                # Send error message and suggestion to user
                error_message = f"```{traceback.format_exc()}```"
                suggestion = f"Here's a suggestion to fix the error: {e}"
                await message.channel.send(f"Error:\n{error_message}\n{suggestion}")

        elif language == "go":
            try:
                # Format Go code using gofmt
                p = subprocess.Popen(['gofmt'], stdout=subprocess.PIPE, stdin=subprocess.PIPE, stderr=subprocess.PIPE)
                formatted_code = p.communicate(input=bytes(code, encoding="utf-8"))[0].decode("utf-8")

                # Highlight Go code using Pygments
                lexer = pygments.lexers.get_lexer_by_name("go")
                formatter = pygments.formatters.get_formatter_by_name("html", style="colorful")
                highlighted_go = pygments.highlight(formatted_code, lexer, formatter)

                # Send output to user
                output_block = f"```{highlighted_go}```"
                await message.channel.send(f"Output:\n{output_block}")
            except Exception as e:
                # Send error message and suggestion to user
                error_message = f"```{traceback.format_exc()}```"
                suggestion = f"Here's a suggestion to fix the error: {e}"
                await message.channel.send(f"Error:\n{error_message}\n{suggestion}")

        elif language == "ruby":
            try:
                # Highlight Ruby code using Pygments
                lexer = pygments.lexers.get_lexer_by_name("ruby")
                formatter = pygments.formatters.get_formatter_by_name("html", style="colorful")
                highlighted_ruby = pygments.highlight(code, lexer, formatter)

                # Send output to user
                output_block = f"```{highlighted_ruby}```"
                await message.channel.send(f"Output:\n{output_block}")
            except Exception as e:
                # Send error message and suggestion to user
                error_message = f"```{traceback.format_exc()}```"
                suggestion = f"Here's a suggestion to fix the error: {e}"
                await message.channel.send(f"Error:\n{error_message}\n{suggestion}")

        else:
            await message.channel.send("Invalid language. Please enter one of the following languages: python, javascript, html, css, java, kotlin, go, ruby")


keep_alive()
bot.run(os.getenv("TOKEN"))
