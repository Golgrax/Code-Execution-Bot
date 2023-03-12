# Code Execution Bot
Coded for Discord Bot that allows users to execute and beautify code in Python, JavaScript, HTML, CSS, Java, and Ruby.


This bot listens for messages in Discord. If a message starts with `!code`, it extracts the code from the message. It determines the programming language of the code based on the first line of the code. Depending on the language, the bot will either execute the code or beautify and highlight it before sending it back to the user.

## Supported languages

- Python
- JavaScript
- HTML/CSS
- Java
- Ruby

## Usage

1. Create a Discord bot and get its token.
2. Install the necessary Python libraries (`discord`, `jsbeautifier`, `js2py`, `pygments`, `requests`, `urllib`, `python-dotenv`, `keep_alive`).
3. Replace the placeholder values for `CLIENT_ID` and `CLIENT_SECRET` with your own values (if you want to use the Java feature).
4. Save the code as a Python file and run it.
5. The bot will start listening for messages in Discord. When a user types `!code`, followed by their code, the bot will execute or beautify the code based on its programming language, and send the output back to the user.

## Requirements

To run this bot, you will need:

- A Discord bot token
- Python 3.6 or higher
- The following Python libraries:
  - `discord`
  - `jsbeautifier`
  - `js2py`
  - `pygments`
  - `requests`
  - `urllib`
  - `python-dotenv`
  - `keep_alive`

## Configuration

The following configuration variables can be set in the `.env` file:

- `DISCORD_TOKEN`: Your Discord bot token.
- `CLIENT_ID`: Your JDoodle API client ID (for Java and Ruby).
- `CLIENT_SECRET`: Your JDoodle API client secret (for Java and Ruby).

## Examples

- `!code print("Hello, World!")` - Executes a Python code and prints "Hello, World!" to the console.
- `!code console.log("Hello, World!")` - Evaluates a JavaScript code and logs "Hello, World!" to the console.
- `!code <html><head><title>Test</title></head><body><h1>Hello, World!</h1></body></html>` - Beautifies and highlights an HTML code.
- `!code public class Main {public static void main(String[] args) {System.out.println("Hello, World!");}}` - Compiles a Java code and prints "Hello, World!" to the console.

## License

Code Execution Bot is licensed under the MIT License. See `LICENSE` for more information.
I hope 
