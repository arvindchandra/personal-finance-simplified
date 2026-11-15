document.addEventListener("DOMContentLoaded", () => {
  const form = document.querySelector("[data-ajax-action]");
  if (!(form instanceof HTMLFormElement)) return;

  const submitButton = form.querySelector('button[type="submit"]');
  const status = form.querySelector(".contact-status");
  if (!(submitButton instanceof HTMLButtonElement) || !(status instanceof HTMLElement)) return;

  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    submitButton.disabled = true;
    status.textContent = "Sending your message…";
    status.dataset.state = "sending";

    try {
      const response = await fetch(form.dataset.ajaxAction, {
        method: "POST",
        headers: {
          Accept: "application/json",
          "Content-Type": "application/json",
        },
        body: JSON.stringify(Object.fromEntries(new FormData(form))),
      });

      const result = await response.json();
      if (!response.ok || (result.success !== true && result.success !== "true")) {
        throw new Error(result.message || "The message could not be sent.");
      }

      form.reset();
      status.textContent = "Thanks — your message has been sent.";
      status.dataset.state = "success";
    } catch (error) {
      status.textContent =
        error instanceof Error
          ? `${error.message} Please try again in a moment.`
          : "The message could not be sent. Please try again in a moment.";
      status.dataset.state = "error";
    } finally {
      submitButton.disabled = false;
    }
  });
});
