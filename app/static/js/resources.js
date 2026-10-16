const rs = document.getElementById("resourceSearch"),
  rt = document.getElementById("resourceType");
async function filterResources() {
  try {
    const p = new URLSearchParams({ search: rs.value, type: rt.value });
    const data = await api("/api/resources?" + p);
    document.getElementById("resourcesGrid").innerHTML = data.length
      ? data
          .map(
            (r) =>
              `<a class="resource-card" href="${r.url}" target="_blank" rel="noopener"><span class="chip">${r.resource_type}</span><h3>${r.title}</h3><p>${r.description}</p><small>${r.subject}</small></a>`,
          )
          .join("")
      : '<div class="card empty">No resources match.</div>';
  } catch (e) {
    toast(e.message, "error");
  }
}
rs.addEventListener("input", filterResources);
const clearBtn = document.getElementById("clearResourceSearch");

clearBtn.addEventListener("click", () => {
  rs.value = "";
  rt.value = "all";
  filterResources();
});
rt.addEventListener("change", filterResources);
