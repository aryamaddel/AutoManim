# AutoManim

AutoManim is a web application that automates the creation and execution of mathematical animations using Manim, a Python library for creating precise, beautiful animations. This tool allows users to generate Manim code from natural language descriptions and instantly render the animations.

## Features

- **AI-Powered Code Generation**: Convert natural language descriptions into executable Manim code using the Groq API
- **Real-Time Execution**: Execute Manim code directly from the browser interface
- **Video Playback**: View generated animations directly in the web interface

## Prerequisites

- Python
- Manim
- Flask
- Groq

## Installation

1. Clone the repository:

   ```
   git clone https://github.com/yourusername/AutoManim.git
   cd AutoManim
   ```

2. Install required Python packages:

   ```
   pip install flask groq manim
   ```

3. Set up your Groq API key as an environment variable

4. Open your browser and navigate to `http://127.0.0.1:5000`

## Usage

1. **Generate Manim Code**:

   - Type a description of the animation you want in the input field at the bottom
   - Click the "Generate" button
   - The AI will convert your description into Manim code

2. **Execute the Code**:

   - Review and optionally modify the generated code
   - Click the "Execute" button
   - Wait for the animation to render (status will be displayed)

3. **Watch the Animation**:
   - The rendered animation will appear in the "Generated Video" section
   - You can play, pause, and replay the animation using the video controls

## Example Prompts

- "Create a circle that transforms into a square"
- "Show a 3D rotating cube with different colors on each face"
- "Animate the Pythagorean theorem with squares on each side of a right triangle"
- "Create a visual proof of the sum of first n odd numbers equals n squared"

## Project Structure

- `app.py`: Flask application with routes for the web interface and API endpoints
- `templates/index.html`: Main web interface
- `static/`: Directory for static files and generated videos

## Troubleshooting

If you encounter issues with video generation:

- Check that Manim is properly installed with all dependencies
- Ensure you have FFmpeg installed for video rendering
- Check permissions for writing to the static directory

## License

This project is open source and available under the MIT License.
