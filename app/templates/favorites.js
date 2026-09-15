const FAV_KEY = "favoriteBlogs";

function getFavorites() {
  try {
    const raw = localStorage.getItem(FAV_KEY);
    return raw ? JSON.parse(raw) : [];
  } catch (e) {
    return [];
  }
}

function toggleFavorite(btn) {
  const name = btn.dataset.name;
  let favs = getFavorites();

  if (favs.includes(name)) {
    favs = favs.filter(f => f !== name);
    btn.classList.remove("active");
    btn.innerHTML = "&#9734;";
  } else {
    favs.push(name);
    btn.classList.add("active");
    btn.innerHTML = "&#9733;";
  }

  localStorage.setItem(FAV_KEY, JSON.stringify(favs));
}

// Inicializar estrellas al cargar
document.addEventListener("DOMContentLoaded", function() {
  const favs = getFavorites();
  document.querySelectorAll(".source-star").forEach(btn => {
    if (favs.includes(btn.dataset.name)) {
      btn.classList.add("active");
      btn.innerHTML = "&#9733;";
    }
  });
});