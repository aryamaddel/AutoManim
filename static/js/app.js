document.addEventListener("DOMContentLoaded", () => {
  // Gather DOM elements
  const els = {
    createButton: document.getElementById("create-button"),
    clearChatButton: document.getElementById("clear-chat-btn"),
    outputVideo: document.getElementById("output-video"),
    statusMessage: document.getElementById("status-message"),
    statusText: document.getElementById("status-text"),
    statusContainer: document.getElementById("status-container"),
    manimPrompt: document.getElementById("manim-prompt"),
    createSpinner: document.getElementById("create-spinner"),
    generatePromptSpinner: document.getElementById("generate-prompt-spinner"),
    videoOverlay: document.getElementById("video-overlay"),
    chatContainer: document.getElementById("chat-container"),
    logDisplay: document.getElementById("log-display"),
    logLines: document.getElementById("log-lines"),
    processingStep: document.getElementById("processing-step"),
    // Progress steps
    step1: document.getElementById("step-1"),
    step2: document.getElementById("step-2"),
    step3: document.getElementById("step-3"),
    label1: document.getElementById("label-1"),
    label2: document.getElementById("label-2"),
    label3: document.getElementById("label-3"),
  };

  // Generated code storage - hidden from user but needed for execution
  let generatedCode = "";

  // UI utility functions
  const toggleLoading = (state) => {
    if (state) {
      els.createSpinner.classList.remove("d-none");
      els.videoOverlay.classList.remove("d-none");
      els.videoOverlay.classList.add("d-flex");
    } else {
      els.createSpinner.classList.add("d-none");
      els.videoOverlay.classList.add("d-none");
      els.videoOverlay.classList.remove("d-flex");
    }
    els.createButton.disabled = state;
  };

  const showStatus = (type, message, timeout = 3000) => {
    els.statusContainer.className = `px-3 py-2 rounded bg-${type}-custom`;
    els.statusText.className = `small mb-0`;
    els.statusText.textContent = message;
    els.statusMessage.classList.remove("d-none");
    if (timeout)
      setTimeout(() => els.statusMessage.classList.add("d-none"), timeout);
  };

  // Update progress display
  const updateProgress = (step, status) => {
    // Reset all steps first
    [els.step1, els.step2, els.step3].forEach((el) => {
      el.classList.remove("active", "complete");
      el.innerHTML = el.id.split("-")[1]; // Reset to number
    });

    [els.label1, els.label2, els.label3].forEach((el) => {
      el.classList.remove("active", "complete");
    });

    // Set appropriate status for each step
    for (let i = 1; i <= 3; i++) {
      const stepEl = els[`step${i}`];
      const labelEl = els[`label${i}`];

      if (i < step) {
        // Previous steps are complete
        stepEl.classList.add("complete");
        stepEl.innerHTML = ""; // Will show checkmark via CSS
        labelEl.classList.add("complete");
      } else if (i === step) {
        // Current step is active
        stepEl.classList.add("active");
        labelEl.classList.add("active");
      }
      // Future steps remain default
    }

    // Update processing message
    if (status) {
      els.processingStep.textContent = status;
    }
  };

  // Chat functions
  const addChatMessage = (message, role) => {
    const messageDiv = document.createElement("div");
    messageDiv.className =
      role === "user" ? "user-message p-3" : "assistant-message p-3";
    messageDiv.textContent = message;

    // Remove the empty state if it exists
    const emptyState = els.chatContainer.querySelector(".text-center.py-4");
    if (emptyState) {
      els.chatContainer.removeChild(emptyState);
    }

    els.chatContainer.appendChild(messageDiv);
    els.chatContainer.scrollTop = els.chatContainer.scrollHeight;
  };

  // API interactions
  const fetchChatHistory = async () => {
    try {
      const response = await fetch("/get_chat_history");
      if (response.ok) {
        const data = await response.json();
        if (data.chat_history && data.chat_history.length > 0) {
          els.chatContainer.innerHTML = "";
          data.chat_history.forEach((message) => {
            // Don't display code in the chat, only user messages and system responses
            if (
              message.role === "user" ||
              (message.role === "assistant" &&
                !message.content.includes("class MainScene"))
            ) {
              addChatMessage(message.content, message.role);
            }
          });
        }
      }
    } catch (error) {
      console.error("Failed to fetch chat history:", error);
    }
  };

  const clearChatHistory = async () => {
    try {
      const response = await fetch("/clear_chat_history", {
        method: "POST",
      });
      if (response.ok) {
        els.chatContainer.innerHTML = `
          <div class="text-center py-4 opacity-50">
            <svg class="mb-2" width="32" height="32" viewBox="0 0 20 20">
              <path fill-rule="evenodd" d="M18 10c0 3.866-3.582 7-8 7a8.841 8.841 0 01-4.083-.98L2 17l1.338-3.123C2.493 12.767 2 11.434 2 10c0-3.866 3.582-7 8-7s8 3.134 8 7zM7 9H5v2h2V9zm8 0h-2v2h2V9zM9 9h2v2H9V9z" clip-rule="evenodd" />
            </svg>
            <span class="text-secondary small">Start a conversation with AutoManim</span>
          </div>
        `;
        generatedCode = "";
      }
    } catch (error) {
      console.error("Failed to clear chat history:", error);
    }
  };

  // Log display management
  let logEventSource = null;
  const maxLogLines = 8; // Increased to show more important logs

  const addLogLine = (text, type = "info") => {
    // Skip unimportant logs
    if (
      text === "Animation frame rendered" &&
      document.querySelectorAll(
        '.log-line:contains("Animation frame rendered")'
      ).length > 0
    ) {
      // Just update the last "Animation frame rendered" line instead of adding a new one
      const renderingLines = document.querySelectorAll(
        ".log-line.rendering-progress"
      );
      if (renderingLines.length > 0) {
        renderingLines[renderingLines.length - 1].textContent += ".";
        return;
      }
    }

    // Create a new log line element
    const logLine = document.createElement("div");
    logLine.className = `log-line ${type}`;

    // Add special class for rendering progress
    if (text === "Animation frame rendered") {
      logLine.classList.add("rendering-progress");
    }

    logLine.textContent = text;

    // Add the new line
    els.logLines.appendChild(logLine);

    // Scroll to bottom
    els.logLines.scrollTop = els.logLines.scrollHeight;

    // Check if we need to remove old lines
    const lines = els.logLines.querySelectorAll(".log-line");
    if (lines.length > maxLogLines) {
      // Add fade-out class to the oldest line
      lines[0].classList.add("fade-out");

      // Remove after animation completes
      setTimeout(() => {
        if (lines[0].parentNode === els.logLines) {
          els.logLines.removeChild(lines[0]);
        }
      }, 500); // Match the CSS transition duration
    }
  };

  const startLogStream = () => {
    // Close any existing stream
    if (logEventSource) {
      logEventSource.close();
    }

    // Clear existing log lines
    els.logLines.innerHTML = "";

    // Show the log display
    els.logDisplay.classList.add("active");

    // Connect to SSE endpoint
    logEventSource = new EventSource("/stream_logs");

    logEventSource.onmessage = (event) => {
      if (event.data === "HEARTBEAT") {
        return; // Ignore heartbeats
      }

      if (event.data === "STREAM_END") {
        endLogStream();
        return;
      }

      if (event.data.startsWith("VIDEO_READY:")) {
        const videoUrl = event.data.substring("VIDEO_READY:".length);
        // Update video source and play
        els.outputVideo.querySelector("source").src =
          videoUrl + "?t=" + Date.now();
        els.outputVideo.load();
        els.outputVideo.play();

        // Add success message
        addLogLine("Animation rendered successfully!", "success");

        // Update progress step
        updateProgress(4, "Animation ready to view!");

        // Turn off loading state in UI
        toggleLoading(false);
        showStatus("success", "Animation generated successfully!");

        // Keep log display visible
        return;
      }

      if (event.data.startsWith("ERROR:")) {
        // Handle errors
        const errorMessage = event.data.substring("ERROR:".length);
        addLogLine(errorMessage.trim(), "error");
        showStatus("danger", errorMessage.trim(), false);
        toggleLoading(false);
        return;
      }

      // Regular log line
      addLogLine(event.data);
    };

    logEventSource.onerror = () => {
      console.error("Log stream error");
      addLogLine("Connection lost. Check server status.", "error");
      endLogStream();
      toggleLoading(false);
    };
  };

  const endLogStream = () => {
    if (logEventSource) {
      logEventSource.close();
      logEventSource = null;
    }

    setTimeout(() => {
      addLogLine("Execution complete", "success");
    }, 500);
  };

  // Combined function to generate and execute Manim animation
  async function createAnimation() {
    const promptText = els.manimPrompt.value.trim();
    if (!promptText) {
      return showStatus(
        "danger",
        "Please describe the animation you want to create",
        false
      );
    }

    toggleLoading(true);
    showStatus("primary", "Processing your animation request...", false);
    addChatMessage(promptText, "user");
    els.manimPrompt.value = "";

    // Step 1: Generating code
    updateProgress(1, "Generating code from your description...");

    try {
      // First generate the code
      const genRes = await fetch("/generate_manim_code", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ manimPrompt: promptText }),
      });

      const genData = await genRes.json();
      if (!genRes.ok) {
        throw new Error(genData.error || "Failed to generate animation code");
      }

      // Store the generated code but don't display it
      generatedCode = genData.code;

      // Step 2: Creating animation
      updateProgress(2, "Creating animation frames...");
      addChatMessage("Generating your animation...", "assistant");

      // Now execute the code to create the animation
      startLogStream();
      const execRes = await fetch("/execute_manim", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ code: generatedCode }),
      });

      const execData = await execRes.json();
      if (!execRes.ok) {
        throw new Error(execData.error || "Failed to create animation");
      }

      // Step 3: Rendering (handled by log stream events)
      updateProgress(3, "Rendering your animation...");
    } catch (error) {
      console.error("Animation creation failed:", error);
      showStatus("danger", error.message || "Animation creation failed", false);
      addLogLine(error.message, "error");
      toggleLoading(false);
      updateProgress(1, "Failed. Please try again.");
    }
  }

  // Event listeners
  const setupListeners = () => {
    els.createButton.addEventListener("click", createAnimation);
    els.manimPrompt.addEventListener("keypress", (e) => {
      if (e.key === "Enter" && !e.shiftKey) {
        e.preventDefault();
        createAnimation();
      }
    });
    els.clearChatButton.addEventListener("click", clearChatHistory);
  };

  // Initialization
  const init = () => {
    fetchChatHistory();
    setupListeners();
  };

  init();
});
