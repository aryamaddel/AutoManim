document.addEventListener("DOMContentLoaded", () => {
  // Elements, state, and utility functions
  const els = {
    createButton: document.getElementById("create-button"),
    clearChatButton: document.getElementById("clear-chat-btn"),
    outputVideo: document.getElementById("output-video"),
    statusMessage: document.getElementById("status-message"),
    statusText: document.getElementById("status-text"),
    statusContainer: document.getElementById("status-container"),
    manimPrompt: document.getElementById("manim-prompt"),
    createSpinner: document.getElementById("create-spinner"),
    chatContainer: document.getElementById("chat-container"),
  };

  let generatedCode = "";

  const toggleLoading = (state) => {
    els.createSpinner.classList.toggle("d-none", !state);
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

  // API functions
  const fetchChatHistory = async () => {
    try {
      const { chat_history } = await (await fetch("/get_chat_history")).json();
      if (chat_history?.length) {
        els.chatContainer.innerHTML = "";
        chat_history.forEach((msg) => {
          if (
            msg.role === "user" ||
            (msg.role === "assistant" &&
              !msg.content.includes("class MainScene"))
          )
            addChatMessage(msg.content, msg.role);
        });
      }
    } catch (e) {
      console.error("Failed to fetch chat history:", e);
    }
  };

  const clearChatHistory = async () => {
    try {
      if ((await fetch("/clear_chat_history", { method: "POST" })).ok) {
        els.chatContainer.innerHTML = `<div class="text-center py-4 opacity-50"><p class="mb-0">Start a conversation with AutoManim</p></div>`;
        generatedCode = "";
      }
    } catch (e) {
      console.error("Failed to clear chat history:", e);
    }
  };

  // Main function
  async function createAnimation() {
    const promptText = els.manimPrompt.value.trim();
    if (!promptText)
      return showStatus(
        "danger",
        "Please describe the animation you want to create",
        false
      );

    toggleLoading(true);
    showStatus("primary", "Processing your animation request...", false);
    addChatMessage(promptText, "user");
    els.manimPrompt.value = "";

    try {
      // Generate code
      const genRes = await fetch("/generate_manim_code", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ manimPrompt: promptText }),
      });

      if (!genRes.ok) throw new Error();
      generatedCode = (await genRes.json()).code;

      addChatMessage("Generating your animation...", "assistant");

      // Execute code and get results directly
      const execRes = await fetch("/execute_manim", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ code: generatedCode }),
      });

      if (!execRes.ok) throw new Error();
      const result = await execRes.json();

      // Update UI based on response
      if (result.status === "success") {
        if (result.video_url) {
          els.outputVideo.querySelector("source").src = `${
            result.video_url
          }?t=${Date.now()}`;
          els.outputVideo.load();
          els.outputVideo.play();
        }
        showStatus("success", "Animation generated successfully!");
      } else {
        showStatus(
          "danger",
          result.message || "Animation creation failed. Please try again.",
          false
        );
      }

      toggleLoading(false);
    } catch (e) {
      console.error("Animation creation failed:", e);
      showStatus(
        "danger",
        "Animation creation failed. Please try again.",
        false
      );
      toggleLoading(false);
    }
  }

  // Initialize
  fetchChatHistory();
  els.createButton.addEventListener("click", createAnimation);
  els.manimPrompt.addEventListener("keypress", (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      createAnimation();
    }
  });
  els.clearChatButton.addEventListener("click", clearChatHistory);
});
