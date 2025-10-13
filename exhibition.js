import { Calendar } from 'https://cdn.jsdelivr.net/npm/fullcalendar@6.1.8/main.esm.js';
import jaLocale from 'https://cdn.jsdelivr.net/npm/fullcalendar@6.1.8/locales/ja.js';

document.addEventListener("DOMContentLoaded", async () => {
  const res = await fetch("data/exhibition.json");
  const exhibitions = await res.json();

  const calendarEl = document.getElementById("calendar");
  const calendar = new Calendar(calendarEl, {
    initialView: "dayGridMonth",
    locale: jaLocale,
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
