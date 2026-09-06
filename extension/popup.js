chrome.storage.local.get(['examSession'], (result) => {
  const statusEl = document.getElementById('sessionStatus');
  const valueEl = document.getElementById('sessionValue');
  if (result.examSession) {
    statusEl.className = 'status status--active';
    valueEl.textContent = 'Exam in progress';
  } else {
    statusEl.className = 'status status--inactive';
    valueEl.textContent = 'No active exam';
  }
});
