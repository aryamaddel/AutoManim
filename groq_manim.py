from groq import Groq
import subprocess
import os
import tempfile
import re


def generate_manim_code(animation_description: str, error_message=None) -> str:
    """Generate runnable Manim code using Groq API"""
    groq = Groq()

    # Base prompt for generating code
    system_content = """You are a Manim code generator. Create complete, runnable Manim Python code based on the description.
    
    Rules:
    1. Include all necessary imports at the top
    2. Create a well-structured Scene class with proper construct method
    3. Do NOT include a main block, as the code will be executed programmatically
    4. Ensure the code is syntactically correct and follows Manim conventions
    5. Return only the Python code with NO markdown formatting or code fences
    6. Name your main scene class 'MainScene'
    7. DO NOT use triple backticks (```) anywhere in your response
    """

    # If there's an error message, add it to the system content
    if error_message:
        system_content += f"""
        
        The previous code generated had errors. Here's the error message:
        {error_message}
        
        Please fix these errors and provide corrected code.
        """

    user_content = f"Generate Manim code for: {animation_description}"
    if error_message:
        user_content = f"Fix the Manim code for: {animation_description}"

    chat_completion = groq.chat.completions.create(
        messages=[
            {"role": "system", "content": system_content},
            {
                "role": "user",
                "content": user_content,
            },
        ],
        model="llama3-70b-8192",
        temperature=0.2,
        stream=False,
    )

    code = chat_completion.choices[0].message.content

    # Remove any code fence markers that might still be present
    code = re.sub(r"^```python\s*", "", code)
    code = re.sub(r"^```\s*", "", code)
    code = re.sub(r"\s*```$", "", code)

    return code


def save_and_run_manim(code: str, flags="-pql"):
    """Save the generated code to a temporary file and run it"""
    # Create a temporary file
    fd, temp_path = tempfile.mkstemp(suffix=".py")

    try:
        # Write the code to the file
        with os.fdopen(fd, "w") as f:
            f.write(code)

        print(f"Manim code has been saved to temporary file: {temp_path}")

        # Run the manim command
        cmd = f"manim {flags} {temp_path} MainScene"
        print(f"Running: {cmd}")

        # Execute the command
        result = subprocess.run(cmd, shell=True, text=True, capture_output=True)

        # Print the output
        print("Output:")
        print(result.stdout)

        # Capture any errors
        error_output = ""
        if result.stderr:
            print("Errors:")
            print(result.stderr)
            error_output = result.stderr

        # Return the success status, file path, and error output
        return result.returncode == 0, temp_path, error_output

    except Exception as e:
        error_message = f"Error running Manim code: {e}"
        print(error_message)
        return False, temp_path, error_message


def generate_and_run_manim(animation_description: str, max_attempts=3):
    """Generate Manim code, run it, and fix errors if needed"""
    attempt = 1
    error_message = None

    while attempt <= max_attempts:
        print(f"\nAttempt {attempt} of {max_attempts}")

        # Generate or fix code
        code = generate_manim_code(animation_description, error_message)

        print("\nGenerated Code Preview:")
        print("----------------------")
        print(code)

        # Run the code
        success, file_path, error_output = save_and_run_manim(code)

        if success:
            print(f"Manim animation completed successfully on attempt {attempt}!")
            return True, file_path, code
        else:
            print(f"Attempt {attempt} failed. Sending error to LLM for correction.")
            error_message = error_output
            attempt += 1

    print(f"Failed to generate working Manim code after {max_attempts} attempts.")
    return False, None, code


# Example usage
if __name__ == "__main__":
    description = "Create an animation showing a pyramid with a square base and an equilateral triangle on top."
    success, file_path, final_code = generate_and_run_manim(description)

    if success:
        print(f"Final working code saved to: {file_path}")
    else:
        print("Could not generate working code within the maximum attempts.")
