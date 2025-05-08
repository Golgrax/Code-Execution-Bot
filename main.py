import discord
import os
import requests
import json
from bs4 import BeautifulSoup
import re
import asyncio

# Set up Discord intents
intents = discord.Intents.default()
intents.message_content = True
client = discord.Client(intents=intents)

# Expanded mapping of languages to Judge0 language IDs
LANGUAGE_IDS = {
    'python': 71,     # Python 3
    'javascript': 63, # Node.js
    'java': 62,       # Java 11
    'c': 50,          # C (GCC 9.2.0)
    'cpp': 54,        # C++ (GCC 9.2.0)
    'csharp': 51,     # C# (.NET Core 3.1.0)
    'php': 68,        # PHP 7.4.1
    'ruby': 72,       # Ruby 2.7.0
    'rust': 73,       # Rust 1.40.0
    'go': 60,         # Go 1.13.5
    'kotlin': 78,     # Kotlin 1.3.70
    'swift': 83,      # Swift 5.2.3
}

# Judge0 API configuration
JUDGE0_BASE_URL = "https://judge0-ce.p.rapidapi.com"  # RapidAPI endpoint
JUDGE0_API_KEY = os.getenv('JUDGE0_API_KEY')  # Store your RapidAPI key as an environment variable

def extract_code_blocks(content):
    """Extract code from Discord markdown code blocks."""
    # Match code blocks with or without language specification
    code_block_pattern = r"```(?:(\w+)\n)?([\s\S]+?)```"
    matches = re.findall(code_block_pattern, content)
    
    if matches:
        language, code = matches[0]
        language = language.lower() if language else "python"  # Default to Python if no language specified
        return language, code.strip()
    
    # If no code block found, try to extract code after language
    parts = content.split(' ', 2)
    if len(parts) >= 3:
        return parts[1].lower(), parts[2].strip()
    
    return None, None

def format_html(code):
    """Format and beautify HTML code."""
    try:
        soup = BeautifulSoup(code, 'html.parser')
        return soup.prettify()
    except Exception as e:
        return f"HTML formatting error: {str(e)}"

async def execute_code(language, code, stdin=""):
    """Execute code using Judge0 API and return the output."""
    if language not in LANGUAGE_IDS:
        return f'Unsupported language: {language}. Supported languages: {", ".join(LANGUAGE_IDS.keys())}'
    
    language_id = LANGUAGE_IDS[language]
    
    # Set up headers with API key
    headers = {
        "Content-Type": "application/json",
        "X-RapidAPI-Key": JUDGE0_API_KEY,
        "X-RapidAPI-Host": "judge0-ce.p.rapidapi.com"
    }
    
    # Prepare data for submission
    data = {
        "source_code": code,
        "language_id": language_id,
        "stdin": stdin,
        "cpu_time_limit": 5,  # 5 seconds time limit
        "memory_limit": 128000  # 128MB memory limit
    }
    
    try:
        # Create submission
        response = requests.post(
            f"{JUDGE0_BASE_URL}/submissions",
            headers=headers,
            json=data
        )
        
        if response.status_code != 201:
            return f"Error creating submission: {response.text}"
        
        # Get submission token
        token = response.json()["token"]
        
        # Poll for results (with timeout)
        max_tries = 10
        for _ in range(max_tries):
            await asyncio.sleep(1)  # Wait between polling attempts
            
            response = requests.get(
                f"{JUDGE0_BASE_URL}/submissions/{token}",
                headers=headers
            )
            
            if response.status_code != 200:
                return f"Error getting results: {response.text}"
            
            result = response.json()
            
            # Check if processing is complete
            if result["status"]["id"] not in [1, 2]:  # Not in queue or processing
                break
        
        # Process results
        status_id = result["status"]["id"]
        
        output = ""
        if "stdout" in result and result["stdout"]:
            output += result["stdout"]
        
        if status_id == 3:  # Accepted
            return output or "Code executed successfully (no output)"
        elif status_id == 4:  # Wrong Answer
            return output or "Code executed but produced wrong answer"
        elif status_id == 5:  # Time Limit Exceeded
            return "Execution time limit exceeded"
        elif status_id == 6:  # Compilation Error
            return f"Compilation Error:\n{result.get('compile_output', 'No details available')}"
        elif status_id == 7:  # Runtime Error (SIGSEGV)
            return f"Runtime Error (SIGSEGV):\n{result.get('stderr', 'No details available')}"
        elif status_id == 8:  # Runtime Error (SIGXFSZ)
            return "Runtime Error: File size limit exceeded"
        elif status_id == 9:  # Runtime Error (SIGFPE)
            return "Runtime Error: Floating point error"
        elif status_id == 10:  # Runtime Error (SIGABRT)
            return "Runtime Error: Aborted"
        elif status_id == 11:  # Runtime Error (NZEC)
            return "Runtime Error: Non-zero exit code"
        elif status_id == 12:  # Runtime Error (Other)
            return f"Runtime Error:\n{result.get('stderr', 'No details available')}"
        elif status_id == 13:  # Internal Error
            return "Judge0 Internal Error"
        elif status_id == 14:  # Exec Format Error
            return "Execution Format Error"
        else:
            return f"Unknown status (ID: {status_id}):\n{result.get('stderr', 'No details available')}"
            
    except Exception as e:
        return f"Error executing code: {str(e)}"

@client.event
async def on_ready():
    """Log when the bot is ready."""
    print(f'Bot is online as {client.user}')
    activity = discord.Activity(type=discord.ActivityType.watching, name="for !code commands")
    await client.change_presence(activity=activity)

@client.event
async def on_message(message):
    """Handle incoming messages."""
    if message.author == client.user:
        return
    
    # Process !code command
    if message.content.startswith('!code'):
        # Send typing indicator to show the bot is processing
        async with message.channel.typing():
            # Extract language and code
            content = message.content[len('!code'):].strip()
            
            # First try to extract from code blocks
            language, code = extract_code_blocks(content)
            
            # If extraction fails, show usage instructions
            if not language or not code:
                await message.channel.send(
                    "Usage: !code [language] [code]\n"
                    "Or use code blocks:\n"
                    "!code ```language\nyour code here\n```\n\n"
                    f"Supported languages: {', '.join(LANGUAGE_IDS.keys())}"
                )
                return
            
            # Process based on language
            if language in LANGUAGE_IDS:
                # Let user know we're processing
                processing_msg = await message.channel.send("Processing code, please wait...")
                
                # Execute code
                output = await execute_code(language, code)
                
                # Format and send response
                if len(output) > 1900:  # Discord message limit is 2000, leave buffer
                    output = output[:1900] + '\n... (truncated)'
                
                await processing_msg.delete()
                await message.channel.send(f'Output:\n```\n{output}\n```')
            
            elif language == 'html':
                formatted_html = format_html(code)
                if len(formatted_html) > 1900:
                    formatted_html = formatted_html[:1900] + '\n... (truncated)'
                await message.channel.send(f'Formatted HTML:\n```html\n{formatted_html}\n```')
            
            else:
                await message.channel.send(
                    f'Unsupported language: {language}\n'
                    f'Supported languages: {", ".join(LANGUAGE_IDS.keys())}'
                )

    # Process !help command
    elif message.content.startswith('!help'):
        help_text = (
            "**Code Execution Bot Commands:**\n\n"
            "`!code [language] [code]` - Execute code in the specified language\n"
            "`!code ```language\ncode\n```` - Execute code in a code block\n\n"
            f"**Supported Languages:** {', '.join(LANGUAGE_IDS.keys())}, html\n\n"
            "**Examples:**\n"
            "`!code python print('Hello, World!')`\n"
            "Or using code blocks:\n"
            "```\n!code ```python\nprint('Hello, World!')\n```\n```"
        )
        await message.channel.send(help_text)

print(os.getenv("JUDGE0_API_KEY"))

# Run the bot with the token from environment variable
if __name__ == "__main__":
    token = os.getenv('DISCORD_TOKEN')
    if not token:
        print("Error: DISCORD_TOKEN environment variable not set")
    else:
        client.run(token)


