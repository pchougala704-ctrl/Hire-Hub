document.addEventListener("DOMContentLoaded", () => {
  const role = document.querySelector("#role");
  const companyField = document.querySelector(".recruiter-company");
  const companyInput = document.querySelector("#company_name");

  if (role && companyField && companyInput) {
    const toggleCompany = () => {
      const recruiter = role.value === "RECRUITER";
      companyField.classList.toggle("d-none", !recruiter);
      companyInput.required = recruiter;
    };
    role.addEventListener("change", toggleCompany);
    toggleCompany();
  }

  const chartCanvas = document.querySelector("#admin-chart");
  if (chartCanvas && window.hireHubAnalyticsUrl && window.Chart) {
    fetch(window.hireHubAnalyticsUrl, { credentials: "same-origin" })
      .then((response) => {
        if (!response.ok) throw new Error("Could not load analytics.");
        return response.json();
      })
      .then((result) => {
        const rows = result.data.applications_by_status || [];
        chartCanvas.parentElement.style.height = "320px";
        new Chart(chartCanvas, {
          type: "doughnut",
          data: {
            labels: rows.map((row) => row._id),
            datasets: [{ data: rows.map((row) => row.count), backgroundColor: ["#5dd6d1", "#4389d4", "#806bd1", "#f0b45d", "#e57878"] }],
          },
          options: { responsive: true, maintainAspectRatio: false, plugins: { legend: { position: "bottom" } } },
        });
      })
      .catch((error) => {
        chartCanvas.insertAdjacentText("afterend", error.message);
      });
  }
});
