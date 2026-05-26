/* Helpers for the prediction pages: preset fillers + submit spinner. */
(function () {
  "use strict";

  // Preset buttons: copy their data-* attributes into the matching inputs.
  document.querySelectorAll(".preset").forEach(function (btn) {
    btn.addEventListener("click", function () {
      Object.keys(btn.dataset).forEach(function (key) {
        const input = document.querySelector('[name="' + key + '"]');
        if (input) {
          input.value = btn.dataset[key];
        }
      });
    });
  });

  // Show a spinner and disable the button while the form submits.
  document.querySelectorAll("form.js-predict-form").forEach(function (form) {
    form.addEventListener("submit", function () {
      const spinner = form.querySelector(".js-spinner");
      if (spinner) {
        spinner.classList.remove("hidden");
      }
      const submit = form.querySelector('[type="submit"]');
      if (submit) {
        submit.classList.add("opacity-60");
      }
    });
  });
})();
