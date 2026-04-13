const navToggle = document.getElementById("navToggle");
const navLinks = document.getElementById("navLinks");

if (navToggle && navLinks) {
    navToggle.addEventListener("click", () => {
        const isOpen = navLinks.classList.toggle("open");
        navToggle.setAttribute("aria-expanded", isOpen ? "true" : "false");
    });
}

document.querySelectorAll(".image-input").forEach((input) => {
    input.addEventListener("change", (event) => {
        const file = event.target.files && event.target.files[0];
        const preview = event.target.closest("form").querySelector(".preview");
        if (!file || !preview) return;
        preview.src = URL.createObjectURL(file);
        preview.style.display = "block";
    });
});

document.querySelectorAll(".confirm-delete-form").forEach((form) => {
    form.addEventListener("submit", (event) => {
        const confirmed = window.confirm("Are you sure you want to delete this report?");
        if (!confirmed) {
            event.preventDefault();
        }
    });
});

setTimeout(() => {
    document.querySelectorAll(".toast").forEach((el) => el.remove());
}, 3500);

