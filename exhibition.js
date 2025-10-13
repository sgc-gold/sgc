document.addEventListener("DOMContentLoaded", async () => {
  const res = await fetch("data/exhibition.json");
  const exhibitions = await res.json();

  const calendarEl = document.getElementById("calendar");
  const calendar = new FullCalendar.Calendar(calendarEl, {
    initialView: "dayGridMonth",
    locale: "ja",
    events: exhibitions.map(e => ({
      title: e.title,
      start: e.start,
      end: e.end,
      extendedProps: e
    })),
    eventClick: function(info) {
      const { title, start, end, extendedProps } = info.event;
      document.getElementById("modalTitle").textContent = title;
      document.getElementById("modalDate").textContent = 
        `${start.toLocaleDateString()} 〜 ${end ? new Date(end).toLocaleDateString() : ""}`;
      document.getElementById("modalLocation").textContent = extendedProps.location;
      document.getElementById("modalNote").textContent = extendedProps.note || "";
      document.getElementById("eventModal").classList.remove("hidden");
    }
  });
  calendar.render();

  document.getElementById("closeModal").onclick = () =>
    document.getElementById("eventModal").classList.add("hidden");
});
