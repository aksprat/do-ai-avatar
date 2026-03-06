/* DO AI Avatar – client-side interactions */

(function () {
  "use strict";

  /* ---- Image upload / drag-and-drop ---- */
  const dropZone      = document.getElementById("dropZone");
  const photoInput    = document.getElementById("photo");
  const placeholder   = document.getElementById("uploadPlaceholder");
  const previewWrap   = document.getElementById("uploadPreview");
  const previewImg    = document.getElementById("previewImg");
  const previewName   = document.getElementById("previewFileName");

  if (dropZone && photoInput) {

    // Drag events
    ["dragenter", "dragover"].forEach(function (evt) {
      dropZone.addEventListener(evt, function (e) {
        e.preventDefault();
        dropZone.classList.add("dragover");
      });
    });

    ["dragleave", "drop"].forEach(function (evt) {
      dropZone.addEventListener(evt, function (e) {
        e.preventDefault();
        dropZone.classList.remove("dragover");
      });
    });

    dropZone.addEventListener("drop", function (e) {
      var file = e.dataTransfer.files[0];
      if (file) {
        applyFile(file);
        // Assign to the hidden input via DataTransfer
        try {
          var dt = new DataTransfer();
          dt.items.add(file);
          photoInput.files = dt.files;
        } catch (_) {
          // Some browsers don't support DataTransfer constructor – silently skip
        }
      }
    });

    photoInput.addEventListener("change", function () {
      if (photoInput.files && photoInput.files[0]) {
        applyFile(photoInput.files[0]);
      }
    });

    function applyFile(file) {
      if (!file.type.startsWith("image/")) return;
      var reader = new FileReader();
      reader.onload = function (e) {
        previewImg.src = e.target.result;
        previewName.textContent = file.name;
        placeholder.classList.add("d-none");
        previewWrap.classList.remove("d-none");
      };
      reader.readAsDataURL(file);
    }
  }

  /* ---- Form submit – show loading state on button ---- */
  var avatarForm = document.getElementById("avatarForm");
  var submitBtn  = document.getElementById("submitBtn");

  if (avatarForm && submitBtn) {
    avatarForm.addEventListener("submit", function (e) {
      // Basic HTML5 validation
      if (!avatarForm.checkValidity()) {
        e.preventDefault();
        avatarForm.reportValidity();
        return;
      }

      submitBtn.disabled = true;
      submitBtn.innerHTML =
        '<span class="spinner-border spinner-border-sm me-2" role="status" aria-hidden="true"></span>' +
        "Generating…";
    });
  }

})();
