(() => {
  const caption = document.querySelector('.user-weather[data-weather-url]');
  if (!caption) return;

  let readings = [];
  let index = 0;
  let rotationStarted = false;
  const degrees = new Intl.NumberFormat('es-CL', {minimumFractionDigits: 1, maximumFractionDigits: 1});

  function showReading() {
    const {province, station, temperature, time} = readings[index];
    caption.textContent = `${province} · ${degrees.format(temperature)} °C`;
    caption.title = `${station} · Medición DMC a las ${time}`;
    caption.hidden = false;
  }

  async function refresh() {
    let nextRefresh = 60_000;
    try {
      const response = await fetch(caption.dataset.weatherUrl, {cache: 'no-store'});
      if (response.redirected || !response.ok) throw new Error();
      const data = await response.json();
      const available = data.readings.filter(item => Number.isFinite(item.temperature));
      if (!available.length) throw new Error();
      const province = readings[index]?.province;
      readings = available;
      index = Math.max(0, readings.findIndex(item => item.province === province));
      showReading();
      if (!rotationStarted) {
        rotationStarted = true;
        window.setInterval(() => {
          if (caption.hidden || readings.length < 2 || document.hidden) return;
          index = (index + 1) % readings.length;
          showReading();
        }, 5_000);
      }
      nextRefresh = 300_000;
    } catch {
      caption.hidden = true;
    }
    window.setTimeout(refresh, nextRefresh);
  }

  refresh();
})();
