(function () {
  const cards = document.querySelectorAll(".chapter-card");
  for (const card of cards) {
    const link = card.querySelector("h2 a");
    if (!link) {
      continue;
    }
    card.addEventListener("dblclick", () => {
      window.location.href = link.href;
    });
  }
})();
