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
  };

  // Generated code storage - hidden from user but needed for execution
  let generatedCode = "";
  // Status polling interval ID
  let statusCheckInterval = null;

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
    els.statusContainer.className = `px-3 py-2 rounded border border-${
      type === "primary" ? "secondary" : type
    }`;
    els.statusText.className = `small mb-0`;
    els.statusText.textContent = message;
    els.statusMessage.classList.remove("d-none");
    if (timeout)
      setTimeout(() => els.statusMessage.classList.add("d-none"), timeout);
  };

  // Chat functions
  const addChatMessage = (message, role) => {
    const messageDiv = document.createElement("div");
    messageDiv.className =
      role === "user" ? "user-message p-2 mb-2" : "assistant-message p-2 mb-2";
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
            <p class="mb-0">Start a conversation with AutoManim</p>
          </div>
        `;
        generatedCode = "";
      }
    } catch (error) {
      console.error("Failed to clear chat history:", error);
    }
  };

  // Simple polling to check animation status
  const checkAnimationStatus = async () => {
    try {
      const response = await fetch("/check_manim_status");
      if (response.ok) {
        const data = await response.json();

        // Update processing step message
        const processingStep = document.getElementById("processing-step");

        if (data.status === "success") {
          if (processingStep) {
            processingStep.textContent = "Animation ready to view!";
          }

          // Update video source and play
          if (data.video_url) {
            els.outputVideo.querySelector("source").src =
              data.video_url + "?t=" + Date.now();
            els.outputVideo.load();
            els.outputVideo.play();
          }

          // Turn off loading state in UI
          toggleLoading(false);
          showStatus("success", "Animation generated successfully!");

          // Stop polling
          clearInterval(statusCheckInterval);
          statusCheckInterval = null;
        } else if (data.status === "error") {
          if (processingStep) {
            processingStep.textContent = "Failed. Please try again.";
          }

          // Show error message
          showStatus(
            "danger",
            data.message || "Animation creation failed",
            false
          );

          // Turn off loading state in UI
          toggleLoading(false);

          // Stop polling
          clearInterval(statusCheckInterval);
          statusCheckInterval = null;
        } else if (data.status === "processing") {
          if (processingStep) {
            processingStep.textContent = "Rendering your animation...";
          }
          // Continue polling - animation is still in progress
        }
      }
    } catch (error) {
      console.error("Failed to check animation status:", error);
    }
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

      // Update processing message
      if (els.videoOverlay) {
        const processingStep = document.getElementById("processing-step");
        if (processingStep) {
          processingStep.textContent = "Creating animation frames...";
        }
      }

      addChatMessage("Generating your animation...", "assistant");

      // Now execute the code to create the animation
      const execRes = await fetch("/execute_manim", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ code: generatedCode }),
      });

      const execData = await execRes.json();
      if (!execRes.ok) {
        throw new Error(execData.error || "Failed to create animation");
      }

      // Start polling for status updates
      if (statusCheckInterval) {
        clearInterval(statusCheckInterval);
      }
      statusCheckInterval = setInterval(checkAnimationStatus, 2000); // Check every 2 seconds

      // Update processing message
      if (els.videoOverlay) {
        const processingStep = document.getElementById("processing-step");
        if (processingStep) {
          processingStep.textContent = "Rendering your animation...";
        }
      }
    } catch (error) {
      console.error("Animation creation failed:", error);
      showStatus("danger", error.message || "Animation creation failed", false);
      toggleLoading(false);

      // Update processing message on error
      if (els.videoOverlay) {
        const processingStep = document.getElementById("processing-step");
        if (processingStep) {
          processingStep.textContent = "Failed. Please try again.";
        }
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
