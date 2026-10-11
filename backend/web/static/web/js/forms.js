/*
 * Client-side form validation for CampusFix student pages.
 * It gives instant feedback before the form is sent.
 * The server (Django) still validates everything again, because
 * JavaScript checks can be bypassed.
 */

// Error messages in the page's language. Django writes them into base.html
// (<script id="i18n-messages">); English is the fallback.
const MESSAGES = Object.assign(
  {
    required: "This field is required.",
    email: "Enter a valid email address.",
    username: "Use only letters, numbers and @ . + - _",
    password: "Password must be at least 8 characters.",
    minlength10: "Please describe the problem in at least 10 characters.",
    mismatch: "Passwords do not match.",
  },
  JSON.parse(document.getElementById("i18n-messages")?.textContent || "{}")
);

// Each rule returns an error message, or "" if the value is fine.
const rules = {
  required: (value) => (value.trim() === "" ? MESSAGES.required : ""),
  email: (value) => (/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(value.trim()) ? "" : MESSAGES.email),
  username: (value) => (/^[\w.@+-]+$/.test(value) ? "" : MESSAGES.username),
  password: (value) => (value.length >= 8 ? "" : MESSAGES.password),
  minlength10: (value) => (value.trim().length >= 10 ? "" : MESSAGES.minlength10),
};

// Which checks to run for each field name, per form type.
const formRules = {
  register: {
    username: ["required", "username"],
    first_name: ["required"],
    email: ["required", "email"],
    password1: ["required", "password"],
    password2: ["required"],
  },
  login: {
    username: ["required"],
    password: ["required"],
  },
  complaint: {
    title: ["required"],
    description: ["required", "minlength10"],
  },
};

// Show (or clear) the error message under one input.
function showError(form, input, message) {
  const box = form.querySelector(`.js-error[data-for="${input.name}"]`);
  if (box) box.textContent = message;
  input.classList.toggle("invalid", message !== "");
}

// Run all checks for one field. Returns true if valid.
function validateField(form, input, checks) {
  for (const name of checks) {
    const message = rules[name](input.value);
    if (message) {
      showError(form, input, message);
      return false;
    }
  }
  // Extra check on the register form: both passwords must match.
  if (input.name === "password2") {
    const first = form.querySelector('[name="password1"]');
    if (first && first.value !== input.value) {
      showError(form, input, MESSAGES.mismatch);
      return false;
    }
  }
  showError(form, input, "");
  return true;
}

// Attach validation to every form that has data-validate="...".
function setupForm(form) {
  const fieldChecks = formRules[form.dataset.validate] || {};

  // Validate a field when the user leaves it.
  for (const [fieldName, checks] of Object.entries(fieldChecks)) {
    const input = form.querySelector(`[name="${fieldName}"]`);
    if (input) input.addEventListener("blur", () => validateField(form, input, checks));
  }

  // Validate all fields on submit; stop the submit if anything is wrong.
  form.addEventListener("submit", (event) => {
    let allValid = true;
    for (const [fieldName, checks] of Object.entries(fieldChecks)) {
      const input = form.querySelector(`[name="${fieldName}"]`);
      if (input && !validateField(form, input, checks)) allValid = false;
    }
    if (!allValid) {
      event.preventDefault();
      const firstBad = form.querySelector(".invalid");
      if (firstBad) firstBad.focus();
    }
  });
}

document.addEventListener("DOMContentLoaded", () => {
  document.querySelectorAll("form[data-validate]").forEach(setupForm);

  // Language switcher: change the language as soon as a new one is picked.
  document.querySelectorAll("select[data-autosubmit]").forEach((select) => {
    select.addEventListener("change", () => select.form.submit());
  });
});
