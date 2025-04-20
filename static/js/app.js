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
    if (status && els.videoOverlay) {
      const processingStep = document.getElementById("processing-step");
      if (processingStep) {
        processingStep.textContent = status;
      }
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

  // Simplified log monitoring - just for updating video status
  let logEventSource = null;

  const startLogStream = () => {
    // Close any existing stream
    if (logEventSource) {
      logEventSource.close();
    }

    // Connect to SSE endpoint for essential updates only
    logEventSource = new EventSource("/stream_logs");

    logEventSource.onmessage = (event) => {
      if (event.data === "HEARTBEAT") {
        return; // Ignore heartbeats
      }

      if (event.data === "STREAM_END") {
        if (logEventSource) {
          logEventSource.close();
          logEventSource = null;
        }
        return;
      }

      // Handle video ready event
      if (event.data.startsWith("VIDEO_READY:")) {
        const videoUrl = event.data.substring("VIDEO_READY:".length);
        // Update video source and play
        els.outputVideo.querySelector("source").src =
          videoUrl + "?t=" + Date.now();
        els.outputVideo.load();
        els.outputVideo.play();

        // Update progress step
        updateProgress(4, "Animation ready to view!");

        // Turn off loading state in UI
        toggleLoading(false);
        showStatus("success", "Animation generated successfully!");

        // End the stream
        if (logEventSource) {
          logEventSource.close();
          logEventSource = null;
        }
        return;
      }

      // Handle errors
      if (event.data.startsWith("ERROR:")) {
        const errorMessage = event.data.substring("ERROR:".length);
        showStatus("danger", errorMessage.trim(), false);
        toggleLoading(false);

        // End the stream on error
        if (logEventSource) {
          logEventSource.close();
          logEventSource = null;
        }
        return;
      }

      // Other log events are ignored in the UI (will show in terminal only)
    };

    logEventSource.onerror = () => {
      console.error("Log stream error");
      showStatus("danger", "Connection lost. Check server status.", false);
      toggleLoading(false);

      if (logEventSource) {
        logEventSource.close();
        logEventSource = null;
      }
    };
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
      toggleLoading(false);
      updateProgress(1, "Failed. Please try again.");

      if (logEventSource) {
        logEventSource.close();
        logEventSource = null;
      }
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
