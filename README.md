# Code Execution Bot

A Discord bot that allows users to execute and beautify code in Python, JavaScript, HTML/CSS, Java, and Ruby.

[View on GitHub](https://github.com/Golgrax/Code-Execution-Bot)

## Overview

This bot listens for messages in Discord. When a message starts with `!code`, it:

1. Extracts the code snippet from the message.  
2. Determines the programming language based on code block syntax or initial tokens.  
3. For executable languages (Python, JavaScript, Java, Ruby): runs the code via a sandboxed API (Judge0 CE) and returns the output.  
4. For markup languages (HTML/CSS): beautifies and highlights the code before sending it back.

## Supported Languages

- **Python**  
- **JavaScript**  
- **HTML/CSS**  
- **Java**  
- **Ruby**

## Installation

1. **Clone the repository**  
   ```bash
   git clone https://github.com/Golgrax/Code-Execution-Bot.git
   cd Code-Execution-Bot
```

2. **Create and activate a virtual environment** (optional but recommended)

   ```bash
   python3 -m venv venv
   source venv/bin/activate    # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**

   ```bash
   pip install -r requirements.txt
   ```

4. **Configure environment variables**
   Create a `.env` file in the project root and add:

   ```dotenv
   DISCORD_TOKEN=your_discord_bot_token
   JUDGE0_API_KEY=your_rapidapi_key
   ```

## Usage

Start the bot:

```bash
python main.py
```

In any channel the bot has access to, type `!code` followed by your code snippet. Use one of the supported patterns:

| Language   | Trigger Syntax                                      |
| ---------- | --------------------------------------------------- |
| Python     | `!code <whatever> python print("Hello!")`           |
| JavaScript | `!code <whatever> javascript console.log("Hello!")` |
| HTML       | `!code <whatever> html <h1>Hello!</h1>`             |
| CSS        | `!code <whatever> css body { color: red; }`         |
| Java       | `!code <whatever> java public class Main { ... }`   |
| Ruby       | `!code <whatever> ruby puts "Hello!"`               |

Or wrap your code in a fenced code block:

<pre>```python
print("Hello, World!")
```</pre>

### Example Commands

* **Python**:

  ```bash
  !code <whatever> python print("Hello, World!")
  ```
* **JavaScript**:

  ```bash
  !code <whatever> javascript console.log("Hello, World!")
  ```
* **HTML**:

  ```bash
  !code <whatever> html <h1>Hello, World!</h1>
  ```
* **CSS**:

  ```bash
  !code <whatever> css body { font-size: 16px; }
  ```
* **Java**:

  ```bash
  !code <whatever> java public class Main { public static void main(String[] args) { System.out.println("Hello, World!"); } }
  ```
* **Ruby**:

  ```bash
  !code <whatever> ruby puts "Hello, World!"
  ```

## Commands Summary

* `!code [snippet]` — Execute or beautify the provided code.
* `!help` — Display help information and list of supported languages.

## Requirements

* **Python 3.6+**
* **Discord bot token** (from the Discord Developer Portal)
* **RapidAPI account** subscribed to Judge0 CE (free tier)
* **Python libraries**:

  * `discord`
  * `requests`
  * `beautifulsoup4`
  * `jsbeautifier`
  * `js2py`
  * `pygments`
  * `python-dotenv`
  * `keep_alive` (optional)

Install all with:

```bash
pip install -r requirements.txt
```

## Configuration

Set the following environment variables in `.env`:

* `DISCORD_TOKEN`: Your Discord bot token.
* `JUDGE0_API_KEY`: Your RapidAPI key for Judge0 CE API.

## Troubleshooting

* **"You are not subscribed" error**: Ensure your RapidAPI key has an active subscription to Judge0 CE.
* **Missing DISCORD\_TOKEN**: Verify `.env` is loaded and the token is correct.
* **Execution errors**: Check the API quotas and inspect bot logs for details.

## License

This project is licensed under the MIT License. See [LICENSE](LICENSE) for details.
