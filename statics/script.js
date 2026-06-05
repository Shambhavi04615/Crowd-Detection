function uploadVideo() {
  const input = document.getElementById('videoInput');
  const file = input.files[0];
  if (!file) return alert("Please select an MP4 file");

  const formData = new FormData();
  formData.append("file", file);

  document.getElementById("loading").style.display = "block";
  document.getElementById("resultSection").style.display = "none";

  fetch("/analyze/", {
    method: "POST",
    body: formData
  })
  .then(response => response.json())
  .then(data => {
    document.getElementById("loading").style.display = "none";
    showResults(data);
  })
  .catch(err => {
    alert("Error during analysis.");
    console.error(err);
    document.getElementById("loading").style.display = "none";
  });
}

function showResults(data) {
  const table = document.getElementById("resultTable");
  table.innerHTML = "";

  for (const key in data) {
    const row = `<tr><th>${key}</th><td>${data[key]}</td></tr>`;
    table.innerHTML += row;
  }

  document.getElementById("resultSection").style.display = "block";

  // Generate chart if relevant keys exist
  if (data["Max Live Count"] && data["Crowd Duration (sec)"] && data["Crowd Events"]) {
    const ctx = document.getElementById('chartCanvas').getContext('2d');
    new Chart(ctx, {
      type: 'bar',
      data: {
        labels: ["Peak Count", "Crowd Duration (s)", "Crowd Events"],
        datasets: [{
          label: 'Crowd Metrics',
          data: [data["Max Live Count"], data["Crowd Duration (sec)"], data["Crowd Events"]],
          backgroundColor: ['#007bff', '#28a745', '#ffc107']
        }]
      }
    });
  }
}
