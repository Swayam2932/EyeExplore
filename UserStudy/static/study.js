(() => {
  const timer = document.querySelector("[data-deadline-ms]");
  const display = document.getElementById("study-timer-display");
  const message = document.getElementById("study-timer-message");
  if (!timer || !display) return;

  const deadline = Number(timer.dataset.deadlineMs);
  const update = () => {
    const remaining = Math.max(0, Math.ceil((deadline - Date.now()) / 1000));
    const minutes = Math.floor(remaining / 60);
    const seconds = remaining % 60;
    display.textContent = `${String(minutes).padStart(2, "0")}:${String(seconds).padStart(2, "0")}`;
    timer.classList.toggle("timer-warning", remaining <= 5 * 60 && remaining > 0);
    timer.classList.toggle("timer-expired", remaining === 0);
    if (remaining === 0 && message) message.hidden = false;
  };

  update();
  window.setInterval(update, 1000);
})();
