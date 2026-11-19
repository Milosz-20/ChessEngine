import { api } from "./common.js";

let mode = "login";
const form = document.getElementById("auth-form");
const error = document.getElementById("error");
const submit = document.getElementById("submit");
const password2Field = document.getElementById("password2-field");

function nextUrl() {
  const next = new URLSearchParams(location.search).get("next");
  // only allow same-site paths
  return next && next.startsWith("/") && !next.startsWith("//") ? next : "/";
}

// Already logged in? Go straight on.
api("/api/me").then(() => location.replace(nextUrl())).catch(() => {});

document.querySelectorAll(".tabs button").forEach(btn => {
  btn.onclick = () => {
    mode = btn.dataset.mode;
    document.querySelectorAll(".tabs button").forEach(b => b.classList.toggle("active", b === btn));
    password2Field.hidden = mode !== "register";
    submit.textContent = mode === "login" ? "Zaloguj się" : "Załóż konto";
    document.getElementById("password").autocomplete = mode === "login" ? "current-password" : "new-password";
    error.textContent = "";
  };
});

form.onsubmit = async e => {
  e.preventDefault();
  error.textContent = "";
  const username = form.username.value.trim();
  const password = form.password.value;
  if (!username || !password) {
    error.textContent = "Uzupełnij nazwę użytkownika i hasło.";
    return;
  }
  if (mode === "register" && password !== form.password2.value) {
    error.textContent = "Hasła nie są takie same.";
    return;
  }
  submit.disabled = true;
  try {
    await api(mode === "login" ? "/api/login" : "/api/register", { method: "POST", body: { username, password } });
    location.replace(nextUrl());
  } catch (err) {
    error.textContent = err.message;
  } finally {
    submit.disabled = false;
  }
};
