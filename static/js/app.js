document.addEventListener("DOMContentLoaded", () => {
  const els = {
    createButton: document.getElementById("create-button"),
    clearChatButton: document.getElementById("clear-chat-btn"),
    outputVideo: document.getElementById("output-video"),
    statusMessage: document.getElementById("status-message"),
    statusText: document.getElementById("status-text"),
    statusContainer: document.getElementById("status-container"),
    manimPrompt: document.getElementById("manim-prompt"),
    createSpinner: document.getElementById("create-spinner"),
    videoOverlay: document.getElementById("video-overlay"),
    chatContainer: document.getElementById("chat-container"),
  };

  // State variables
  let generatedCode = "";
  let statusCheckInterval = null;

  // UI utility functions
  const toggleLoading = (state) => {
    els.createSpinner.classList.toggle("d-none", !state);
    els.videoOverlay.classList.toggle("d-none", !state);
    els.videoOverlay.classList.toggle("d-flex", state);
    els.createButton.disabled = state;
  };

  const showStatus = (type, message, timeout = 3000) => {
    els.statusContainer.className = `px-3 py-2 rounded border border-${
      type === "primary" ? "secondary" : type
    }`;
    els.statusText.textContent = message;
    els.statusMessage.classList.remove("d-none");
    if (timeout)
      setTimeout(() => els.statusMessage.classList.add("d-none"), timeout);
  };

  const addChatMessage = (message, role) => {
    const messageDiv = document.createElement("div");
    messageDiv.className = `${
      role === "user" ? "user" : "assistant"
    }-message p-2 mb-2`;
    messageDiv.textContent = message;

    const emptyState = els.chatContainer.querySelector(".text-center.py-4");
    if (emptyState) els.chatContainer.removeChild(emptyState);

    els.chatContainer.appendChild(messageDiv);
    els.chatContainer.scrollTop = els.chatContainer.scrollHeight;
  };

  // API interactions
  const fetchChatHistory = async () => {
    try {
      const response = await fetch("/get_chat_history");
      const data = await response.json();

      if (data.chat_history?.length > 0) {
        els.chatContainer.innerHTML = "";
        data.chat_history.forEach((message) => {
          if (
            message.role === "user" ||
            (message.role === "assistant" &&
              !message.content.includes("class MainScene"))
          ) {
            addChatMessage(message.content, message.role);
          }
        });
      }
    } catch (error) {
      console.error("Failed to fetch chat history:", error);
    }
  };

  const clearChatHistory = async () => {
    try {
      const response = await fetch("/clear_chat_history", { method: "POST" });
      if (response.ok) {
        els.chatContainer.innerHTML = `
          <div class="text-center py-4 opacity-50">
            <p class="mb-0">Start a conversation with AutoManim</p>
          </div>`;
        generatedCode = "";
      }
    } catch (error) {
      console.error("Failed to clear chat history:", error);
    }
  };

  // Status polling
  const checkAnimationStatus = async () => {
    try {
      const response = await fetch("/check_manim_status");
      const data = await response.json();
      const processingStep = document.getElementById("processing-step");

      if (data.status === "success") {
        if (processingStep)
          processingStep.textContent = "Animation ready to view!";

        if (data.video_url) {
          els.outputVideo.querySelector("source").src = `${
            data.video_url
          }?t=${Date.now()}`;
          els.outputVideo.load();
          els.outputVideo.play();
        }

        toggleLoading(false);
        showStatus("success", "Animation generated successfully!");
        clearInterval(statusCheckInterval);
        statusCheckInterval = null;
      } else if (data.status === "error") {
        if (processingStep)
          processingStep.textContent = "Failed. Please try again.";

        showStatus(
          "danger",
          "Animation creation failed. Please try again.",
          false
        );
        toggleLoading(false);
        clearInterval(statusCheckInterval);
        statusCheckInterval = null;
      } else if (data.status === "processing" && processingStep) {
        processingStep.textContent = "Rendering your animation...";
      }
    } catch (error) {
      console.error("Failed to check animation status:", error);
    }
  };

  // Main animation creation function
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
      // Generate the code
      const genRes = await fetch("/generate_manim_code", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ manimPrompt: promptText }),
      });

      if (!genRes.ok) throw new Error("Failed to generate animation code");
      const genData = await genRes.json();
      generatedCode = genData.code;

      const processingStep = document.getElementById("processing-step");
      if (processingStep)
        processingStep.textContent = "Creating animation frames...";

      addChatMessage("Generating your animation...", "assistant");

      // Execute the code
      const execRes = await fetch("/execute_manim", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ code: generatedCode }),
      });

      if (!execRes.ok) throw new Error("Failed to create animation");

      if (statusCheckInterval) clearInterval(statusCheckInterval);
      statusCheckInterval = setInterval(checkAnimationStatus, 2000);

      if (processingStep)
        processingStep.textContent = "Rendering your animation...";
    } catch (error) {
      console.error("Animation creation failed:", error);
      showStatus(
        "danger",
        "Animation creation failed. Please try again.",
        false
      );
      toggleLoading(false);

      const processingStep = document.getElementById("processing-step");
      if (processingStep)
        processingStep.textContent = "Failed. Please try again.";
    }
  }

  // Setup and initialization
  const init = () => {
    fetchChatHistory();
    els.createButton.addEventListener("click", createAnimation);
    els.manimPrompt.addEventListener("keypress", (e) => {
      if (e.key === "Enter" && !e.shiftKey) {
        e.preventDefault();
        createAnimation();
      }
    });
    els.clearChatButton.addEventListener("click", clearChatHistory);
  };

  init();
});
