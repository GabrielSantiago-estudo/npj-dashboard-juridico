/* ==========================================================================
   NPJ - Dashboard analítico
   Consome /api/dashboard/dados e renderiza os 5 gráficos com Chart.js
   ========================================================================== */
(function () {
  'use strict';

  const CORES = {
    azul: '#1e5aa8',
    azulClaro: 'rgba(30, 90, 168, 0.15)',
    verde: '#2e9251',
    ambar: '#d4a012',
    vermelho: '#c0392b',
    cinza: '#94a2b3',
  };

  const PALETA_SERIES = [
    '#1e5aa8', '#2e9251', '#d4a012', '#c0392b',
    '#7c4dff', '#00897b', '#e64a19', '#3949ab',
  ];

  const CORES_SITUACAO = {
    'Ativo': '#1e5aa8',
    'Concluído': '#2e9251',
    'Arquivado': '#94a2b3',
    'Indeferido': '#c0392b',
  };

  const charts = {};

  Chart.defaults.font.family =
    'Inter, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif';
  Chart.defaults.color = '#4a5768';
  Chart.defaults.borderColor = 'rgba(221, 228, 237, 0.6)';

  function destruir(id) {
    if (charts[id]) { charts[id].destroy(); delete charts[id]; }
  }

  function chartLinha(id, dados) {
    destruir(id);
    const ctx = document.getElementById(id);
    if (!ctx) return;
    charts[id] = new Chart(ctx, {
      type: 'line',
      data: {
        labels: dados.labels,
        datasets: [{
          label: 'Atendimentos',
          data: dados.valores,
          borderColor: CORES.azul,
          backgroundColor: CORES.azulClaro,
          borderWidth: 2,
          tension: 0.3,
          fill: true,
          pointRadius: 4,
          pointBackgroundColor: CORES.azul,
        }],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: { legend: { display: false } },
        scales: {
          y: { beginAtZero: true, ticks: { precision: 0 } },
        },
      },
    });
  }

  function chartBarras(id, dados, cor) {
    destruir(id);
    const ctx = document.getElementById(id);
    if (!ctx) return;
    charts[id] = new Chart(ctx, {
      type: 'bar',
      data: {
        labels: dados.labels,
        datasets: [{
          label: 'Atendimentos',
          data: dados.valores,
          backgroundColor: cor || CORES.azul,
          borderRadius: 6,
          borderSkipped: false,
        }],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: { legend: { display: false } },
        scales: {
          y: { beginAtZero: true, ticks: { precision: 0 } },
        },
      },
    });
  }

  function chartBarrasH(id, dados) {
    destruir(id);
    const ctx = document.getElementById(id);
    if (!ctx) return;
    const cores = dados.labels.map((_, i) => PALETA_SERIES[i % PALETA_SERIES.length]);
    charts[id] = new Chart(ctx, {
      type: 'bar',
      data: {
        labels: dados.labels,
        datasets: [{
          label: 'Atendimentos',
          data: dados.valores,
          backgroundColor: cores,
          borderRadius: 6,
          borderSkipped: false,
        }],
      },
      options: {
        indexAxis: 'y',
        responsive: true,
        maintainAspectRatio: false,
        plugins: { legend: { display: false } },
        scales: {
          x: { beginAtZero: true, ticks: { precision: 0 } },
        },
      },
    });
  }

  function chartDoughnut(id, dados) {
    destruir(id);
    const ctx = document.getElementById(id);
    if (!ctx) return;
    const cores = dados.labels.map(l => CORES_SITUACAO[l] || CORES.cinza);
    charts[id] = new Chart(ctx, {
      type: 'doughnut',
      data: {
        labels: dados.labels,
        datasets: [{
          data: dados.valores,
          backgroundColor: cores,
          borderColor: '#ffffff',
          borderWidth: 2,
        }],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        cutout: '60%',
        plugins: {
          legend: { position: 'bottom', labels: { padding: 12, boxWidth: 12 } },
        },
      },
    });
  }

  function setKPI(id, valor) {
    const el = document.getElementById(id);
    if (el) el.textContent = valor;
  }

  async function carregar() {
    const ano = document.getElementById('filtro-ano').value;
    const semestre = document.getElementById('filtro-semestre').value;
    const area_id = document.getElementById('filtro-area').value;

    const params = new URLSearchParams();
    if (ano) params.set('ano', ano);
    if (semestre) params.set('semestre', semestre);
    if (area_id) params.set('area_id', area_id);

    const url = '/api/dashboard/dados' + (params.toString() ? '?' + params : '');
    try {
      const resp = await fetch(url);
      if (!resp.ok) throw new Error('HTTP ' + resp.status);
      const data = await resp.json();

      setKPI('kpi-total', data.kpis.total_atendimentos);
      setKPI('kpi-assistidos', data.kpis.total_assistidos);
      setKPI('kpi-media', data.kpis.media_por_mes);
      const arq = document.getElementById('kpi-arquivados');
      if (arq) arq.textContent = `Arquivados: ${data.kpis.total_arquivados}`;

      chartLinha('chart-ano', data.por_ano);
      chartBarras('chart-mes', data.por_mes, CORES.azul);
      chartBarrasH('chart-area', data.por_area);
      chartBarrasH('chart-equipe', data.por_equipe);
      chartDoughnut('chart-situacao', data.por_situacao);
    } catch (e) {
      console.error('Erro ao carregar dashboard:', e);
    }
  }

  document.addEventListener('DOMContentLoaded', () => {
    document.getElementById('btn-aplicar').addEventListener('click', carregar);
    document.getElementById('btn-limpar').addEventListener('click', () => {
      document.getElementById('filtro-ano').value = '';
      document.getElementById('filtro-semestre').value = '';
      document.getElementById('filtro-area').value = '';
      carregar();
    });
    carregar();
  });
})();