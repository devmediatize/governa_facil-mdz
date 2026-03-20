// relatorios.js - Graficos modernos e profissionais com Chart.js
// Versao melhorada com cores consistentes, gradientes, animacoes e hover effects

let charts = {};
let relatoriosCarregados = false;

// ============================================
// PALETA DE CORES MODERNA E CONSISTENTE
// ============================================
const modernColors = {
    primary: '#6366f1',    // Indigo
    success: '#22c55e',    // Verde
    danger: '#ef4444',     // Vermelho
    warning: '#f59e0b',    // Laranja
    purple: '#8b5cf6',     // Roxo
    pink: '#ec4899',       // Rosa
    cyan: '#06b6d4',       // Ciano
    slate: '#64748b'       // Cinza
};

// Array de cores para uso em graficos
const colorPalette = [
    modernColors.primary,
    modernColors.success,
    modernColors.danger,
    modernColors.warning,
    modernColors.purple,
    modernColors.pink,
    modernColors.cyan,
    modernColors.slate
];

// Funcao para criar gradiente vertical
function createGradient(ctx, color, height = 400) {
    const gradient = ctx.createLinearGradient(0, 0, 0, height);
    gradient.addColorStop(0, hexToRgba(color, 0.8));
    gradient.addColorStop(0.5, hexToRgba(color, 0.4));
    gradient.addColorStop(1, hexToRgba(color, 0.1));
    return gradient;
}

// Funcao para criar gradiente horizontal
function createHorizontalGradient(ctx, color, width = 400) {
    const gradient = ctx.createLinearGradient(0, 0, width, 0);
    gradient.addColorStop(0, hexToRgba(color, 0.8));
    gradient.addColorStop(1, hexToRgba(color, 0.4));
    return gradient;
}

// Converter hex para rgba
function hexToRgba(hex, alpha = 1) {
    const r = parseInt(hex.slice(1, 3), 16);
    const g = parseInt(hex.slice(3, 5), 16);
    const b = parseInt(hex.slice(5, 7), 16);
    return `rgba(${r}, ${g}, ${b}, ${alpha})`;
}

// ============================================
// CONFIGURACOES GLOBAIS DO CHART.JS
// ============================================
Chart.defaults.font.family = "'Inter', 'Segoe UI', 'Roboto', sans-serif";
Chart.defaults.font.size = 12;
Chart.defaults.color = '#64748b';
Chart.defaults.plugins.legend.labels.usePointStyle = true;
Chart.defaults.plugins.legend.labels.padding = 20;
Chart.defaults.plugins.tooltip.backgroundColor = 'rgba(15, 23, 42, 0.9)';
Chart.defaults.plugins.tooltip.titleFont = { size: 14, weight: 'bold' };
Chart.defaults.plugins.tooltip.bodyFont = { size: 13 };
Chart.defaults.plugins.tooltip.padding = 12;
Chart.defaults.plugins.tooltip.cornerRadius = 8;
Chart.defaults.plugins.tooltip.displayColors = true;
Chart.defaults.plugins.tooltip.boxPadding = 6;

// ============================================
// OPCOES COMUNS PARA GRAFICOS
// ============================================
const commonOptions = {
    responsive: true,
    maintainAspectRatio: true,
    animation: {
        duration: 1000,
        easing: 'easeOutQuart'
    },
    interaction: {
        intersect: false,
        mode: 'index'
    },
    plugins: {
        legend: {
            position: 'top',
            align: 'end',
            labels: {
                boxWidth: 12,
                boxHeight: 12,
                borderRadius: 3,
                useBorderRadius: true,
                font: {
                    size: 12,
                    weight: '500'
                }
            }
        },
        tooltip: {
            enabled: true,
            callbacks: {
                labelColor: function(context) {
                    return {
                        borderColor: context.dataset.borderColor || colorPalette[context.dataIndex % colorPalette.length],
                        backgroundColor: context.dataset.backgroundColor || colorPalette[context.dataIndex % colorPalette.length],
                        borderWidth: 2,
                        borderRadius: 4
                    };
                }
            }
        }
    }
};

// Opcoes para graficos de barras
const barChartOptions = {
    ...commonOptions,
    scales: {
        x: {
            grid: {
                display: false
            },
            ticks: {
                font: {
                    size: 11,
                    weight: '500'
                }
            }
        },
        y: {
            beginAtZero: true,
            grid: {
                color: 'rgba(148, 163, 184, 0.1)',
                drawBorder: false
            },
            ticks: {
                font: {
                    size: 11
                },
                padding: 10
            }
        }
    }
};

// Opcoes para graficos de linha
const lineChartOptions = {
    ...commonOptions,
    scales: {
        x: {
            grid: {
                display: false
            },
            ticks: {
                font: {
                    size: 11,
                    weight: '500'
                }
            }
        },
        y: {
            beginAtZero: true,
            grid: {
                color: 'rgba(148, 163, 184, 0.1)',
                drawBorder: false
            },
            ticks: {
                font: {
                    size: 11
                },
                padding: 10
            }
        }
    }
};

// Opcoes para graficos de pizza/donut
const pieChartOptions = {
    ...commonOptions,
    cutout: '0%',
    plugins: {
        ...commonOptions.plugins,
        legend: {
            position: 'right',
            align: 'center',
            labels: {
                boxWidth: 14,
                boxHeight: 14,
                borderRadius: 4,
                useBorderRadius: true,
                padding: 16,
                font: {
                    size: 12,
                    weight: '500'
                },
                generateLabels: function(chart) {
                    const data = chart.data;
                    if (data.labels.length && data.datasets.length) {
                        return data.labels.map((label, i) => {
                            const value = data.datasets[0].data[i];
                            const total = data.datasets[0].data.reduce((a, b) => a + b, 0);
                            const percentage = ((value / total) * 100).toFixed(1);
                            return {
                                text: `${label} (${percentage}%)`,
                                fillStyle: data.datasets[0].backgroundColor[i],
                                strokeStyle: data.datasets[0].borderColor[i],
                                lineWidth: 2,
                                hidden: false,
                                index: i
                            };
                        });
                    }
                    return [];
                }
            }
        }
    }
};

// Opcoes para graficos donut
const doughnutChartOptions = {
    ...pieChartOptions,
    cutout: '65%',
    plugins: {
        ...pieChartOptions.plugins,
        legend: {
            ...pieChartOptions.plugins.legend
        }
    }
};

// ============================================
// FUNCOES DE CARREGAMENTO DOS GRAFICOS
// ============================================

async function carregarVolume() {
    try {
        const params = new URLSearchParams({
            periodo: document.getElementById('periodo').value,
            data_inicio: document.getElementById('dataInicio').value,
            data_fim: document.getElementById('dataFim').value
        });

        const response = await fetch(`/api/relatorios/volume-periodo?${params}`);
        const data = await response.json();

        if (charts.volumeChart) {
            charts.volumeChart.destroy();
        }

        const canvas = document.getElementById('volumeChart');
        const ctx = canvas.getContext('2d');

        // Criar gradiente para area
        const gradient = createGradient(ctx, modernColors.primary, canvas.height);

        charts.volumeChart = new Chart(ctx, {
            type: 'line',
            data: {
                labels: data.labels,
                datasets: [{
                    label: 'Volume de Incidencias',
                    data: data.values,
                    borderColor: modernColors.primary,
                    backgroundColor: gradient,
                    borderWidth: 3,
                    fill: true,
                    tension: 0.4,
                    pointRadius: 4,
                    pointHoverRadius: 8,
                    pointBackgroundColor: '#ffffff',
                    pointBorderColor: modernColors.primary,
                    pointBorderWidth: 2,
                    pointHoverBackgroundColor: modernColors.primary,
                    pointHoverBorderColor: '#ffffff',
                    pointHoverBorderWidth: 3
                }]
            },
            options: {
                ...lineChartOptions,
                plugins: {
                    ...lineChartOptions.plugins,
                    title: {
                        display: true,
                        text: 'Volume de Incidencias por Periodo',
                        font: {
                            size: 16,
                            weight: '600'
                        },
                        padding: {
                            bottom: 20
                        }
                    }
                }
            }
        });
    } catch (error) {
        console.error('Erro ao carregar volume:', error);
        throw error;
    }
}

async function carregarPerformance() {
    try {
        const response = await fetch('/api/relatorios/performance');
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        const data = await response.json();
        const tempoMedio = data?.tempo_medio_por_categoria || {};
        const labels = Object.keys(tempoMedio);
        const values = Object.values(tempoMedio);

        if (charts.performanceChart) {
            charts.performanceChart.destroy();
        }

        const canvas = document.getElementById('performanceChart');
        if (!canvas) {
            throw new Error('Elemento performanceChart nao encontrado');
        }

        const ctx = canvas.getContext('2d');

        // Criar gradientes para cada barra
        const backgroundColors = labels.map((_, index) => {
            return createGradient(ctx, colorPalette[index % colorPalette.length], canvas.height);
        });

        charts.performanceChart = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: labels.length ? labels : ['Sem dados'],
                datasets: [{
                    label: 'Tempo Medio (horas)',
                    data: values.length ? values : [0],
                    backgroundColor: backgroundColors.length ? backgroundColors : [hexToRgba(modernColors.primary, 0.6)],
                    borderColor: labels.map((_, index) => colorPalette[index % colorPalette.length]),
                    borderWidth: 2,
                    borderRadius: 8,
                    borderSkipped: false,
                    hoverBackgroundColor: labels.map((_, index) => hexToRgba(colorPalette[index % colorPalette.length], 0.9)),
                    hoverBorderWidth: 3
                }]
            },
            options: {
                ...barChartOptions,
                plugins: {
                    ...barChartOptions.plugins,
                    title: {
                        display: true,
                        text: `Taxa de Resolucao: ${data?.taxa_resolucao || 0}%`,
                        font: {
                            size: 16,
                            weight: '600'
                        },
                        color: modernColors.success,
                        padding: {
                            bottom: 20
                        }
                    },
                    tooltip: {
                        ...barChartOptions.plugins.tooltip,
                        callbacks: {
                            label: function(context) {
                                return `${context.dataset.label}: ${context.raw.toFixed(1)} horas`;
                            }
                        }
                    }
                },
                scales: {
                    ...barChartOptions.scales,
                    y: {
                        ...barChartOptions.scales.y,
                        title: {
                            display: true,
                            text: 'Horas',
                            font: {
                                size: 12,
                                weight: '600'
                            }
                        }
                    }
                }
            }
        });
    } catch (error) {
        console.error('Erro ao carregar performance:', error);
        const ctx = document.getElementById('performanceChart');
        if (ctx) {
            const div = document.createElement('div');
            div.className = 'alert alert-danger';
            div.textContent = 'Erro ao carregar dados de performance';
            ctx.parentNode.insertBefore(div, ctx);
        }
    }
}

async function carregarDistribuicaoStatus() {
    try {
        const response = await fetch('/api/relatorios/status');
        const data = await response.json();

        if (charts.statusChart) {
            charts.statusChart.destroy();
        }

        const canvas = document.getElementById('statusChart');
        const ctx = canvas.getContext('2d');

        const labels = Object.keys(data.distribuicao);
        const values = Object.values(data.distribuicao);

        // Mapear cores para status
        const statusColors = {
            'Aberta': modernColors.warning,
            'Em Andamento': modernColors.primary,
            'Resolvida': modernColors.success,
            'Fechada': modernColors.slate,
            'Cancelada': modernColors.danger
        };

        const backgroundColors = labels.map(label =>
            statusColors[label] || colorPalette[labels.indexOf(label) % colorPalette.length]
        );

        charts.statusChart = new Chart(ctx, {
            type: 'doughnut',
            data: {
                labels: labels,
                datasets: [{
                    data: values,
                    backgroundColor: backgroundColors.map(color => hexToRgba(color, 0.85)),
                    borderColor: backgroundColors,
                    borderWidth: 3,
                    hoverBackgroundColor: backgroundColors,
                    hoverBorderColor: '#ffffff',
                    hoverBorderWidth: 4,
                    hoverOffset: 10
                }]
            },
            options: {
                ...doughnutChartOptions,
                plugins: {
                    ...doughnutChartOptions.plugins,
                    title: {
                        display: true,
                        text: 'Distribuicao por Status',
                        font: {
                            size: 16,
                            weight: '600'
                        },
                        padding: {
                            bottom: 10
                        }
                    },
                    tooltip: {
                        callbacks: {
                            label: function(context) {
                                const total = context.dataset.data.reduce((a, b) => a + b, 0);
                                const percentage = ((context.raw / total) * 100).toFixed(1);
                                return `${context.label}: ${context.raw} (${percentage}%)`;
                            }
                        }
                    }
                }
            }
        });
    } catch (error) {
        console.error('Erro ao carregar status:', error);
        throw error;
    }
}

async function carregarDistribuicaoCategorias() {
    try {
        const response = await fetch('/api/relatorios/tendencias-categoria');
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        const data = await response.json();

        if (!data || !data.categorias || !data.dados) {
            throw new Error('Dados invalidos recebidos da API');
        }

        if (charts.categoriaChart) {
            charts.categoriaChart.destroy();
        }

        const canvas = document.getElementById('categoriaChart');
        if (!canvas) {
            throw new Error('Elemento canvas nao encontrado');
        }

        const ctx = canvas.getContext('2d');

        // Usar paleta de cores moderna
        const backgroundColors = data.categorias.map((_, index) =>
            hexToRgba(colorPalette[index % colorPalette.length], 0.85)
        );
        const borderColors = data.categorias.map((_, index) =>
            colorPalette[index % colorPalette.length]
        );

        charts.categoriaChart = new Chart(ctx, {
            type: 'pie',
            data: {
                labels: data.categorias,
                datasets: [{
                    data: data.dados,
                    backgroundColor: backgroundColors,
                    borderColor: borderColors,
                    borderWidth: 3,
                    hoverBackgroundColor: borderColors,
                    hoverBorderColor: '#ffffff',
                    hoverBorderWidth: 4,
                    hoverOffset: 15
                }]
            },
            options: {
                ...pieChartOptions,
                plugins: {
                    ...pieChartOptions.plugins,
                    title: {
                        display: true,
                        text: 'Distribuicao por Categoria',
                        font: {
                            size: 16,
                            weight: '600'
                        },
                        padding: {
                            bottom: 10
                        }
                    },
                    tooltip: {
                        callbacks: {
                            label: function(context) {
                                const total = context.dataset.data.reduce((a, b) => a + b, 0);
                                const percentage = ((context.raw / total) * 100).toFixed(1);
                                return `${context.label}: ${context.raw} (${percentage}%)`;
                            }
                        }
                    }
                }
            }
        });
    } catch (error) {
        console.error('Erro ao carregar categorias:', error);
        const ctx = document.getElementById('categoriaChart');
        if (ctx) {
            const div = document.createElement('div');
            div.className = 'alert alert-danger';
            div.textContent = 'Erro ao carregar dados das categorias';
            ctx.parentNode.insertBefore(div, ctx);
        }
    }
}

async function carregarDistribuicaoGeografica() {
    try {
        const response = await fetch('/api/relatorios/geografico');
        const data = await response.json();

        const canvas = document.getElementById('geograficoChart');
        if (!canvas) {
            return;
        }

        if (charts.geograficoChart) {
            charts.geograficoChart.destroy();
            delete charts.geograficoChart;
        }

        const ctx = canvas.getContext('2d');
        const labels = Object.keys(data.por_estado);
        const valores = Object.values(data.por_estado);

        // Criar gradientes para cada barra
        const backgroundColors = labels.map((_, index) => {
            return createGradient(ctx, colorPalette[index % colorPalette.length], canvas.height);
        });

        charts.geograficoChart = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: labels,
                datasets: [{
                    label: 'Quantidade de Incidencias',
                    data: valores,
                    backgroundColor: backgroundColors,
                    borderColor: labels.map((_, index) => colorPalette[index % colorPalette.length]),
                    borderWidth: 2,
                    borderRadius: 8,
                    borderSkipped: false,
                    hoverBackgroundColor: labels.map((_, index) => hexToRgba(colorPalette[index % colorPalette.length], 0.9)),
                    hoverBorderWidth: 3
                }]
            },
            options: {
                ...barChartOptions,
                plugins: {
                    ...barChartOptions.plugins,
                    title: {
                        display: true,
                        text: 'Distribuicao Geografica',
                        font: {
                            size: 16,
                            weight: '600'
                        },
                        padding: {
                            bottom: 20
                        }
                    }
                }
            }
        });

    } catch (error) {
        console.error('Erro ao carregar grafico geografico:', error);
    }
}

async function carregarTempoResolucao() {
    try {
        const response = await fetch('/api/relatorios/performance');
        const data = await response.json();

        if (charts.tempoChart) {
            charts.tempoChart.destroy();
        }

        const canvas = document.getElementById('tempoChart');
        const ctx = canvas.getContext('2d');

        const labels = Object.keys(data.tempo_medio_por_categoria);
        const values = Object.values(data.tempo_medio_por_categoria);

        // Gradiente horizontal para grafico de tempo
        const gradient = createHorizontalGradient(ctx, modernColors.purple, canvas.width);

        charts.tempoChart = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: labels,
                datasets: [{
                    label: 'Tempo Medio (horas)',
                    data: values,
                    backgroundColor: labels.map((_, index) => {
                        return createGradient(ctx, colorPalette[(index + 4) % colorPalette.length], canvas.height);
                    }),
                    borderColor: labels.map((_, index) => colorPalette[(index + 4) % colorPalette.length]),
                    borderWidth: 2,
                    borderRadius: 10,
                    borderSkipped: false,
                    hoverBackgroundColor: labels.map((_, index) => hexToRgba(colorPalette[(index + 4) % colorPalette.length], 0.9)),
                    hoverBorderWidth: 3
                }]
            },
            options: {
                ...barChartOptions,
                plugins: {
                    ...barChartOptions.plugins,
                    title: {
                        display: true,
                        text: 'Tempo Medio de Resolucao por Categoria',
                        font: {
                            size: 16,
                            weight: '600'
                        },
                        padding: {
                            bottom: 20
                        }
                    },
                    tooltip: {
                        callbacks: {
                            label: function(context) {
                                const hours = context.raw;
                                if (hours >= 24) {
                                    const days = Math.floor(hours / 24);
                                    const remainingHours = (hours % 24).toFixed(1);
                                    return `${context.dataset.label}: ${days}d ${remainingHours}h`;
                                }
                                return `${context.dataset.label}: ${hours.toFixed(1)} horas`;
                            }
                        }
                    }
                },
                scales: {
                    ...barChartOptions.scales,
                    y: {
                        ...barChartOptions.scales.y,
                        title: {
                            display: true,
                            text: 'Horas',
                            font: {
                                size: 12,
                                weight: '600'
                            }
                        }
                    }
                }
            }
        });
    } catch (error) {
        console.error('Erro ao carregar tempo de resolucao:', error);
        throw error;
    }
}

// ============================================
// FUNCAO PRINCIPAL DE ATUALIZACAO
// ============================================

async function atualizarTodosRelatorios() {
    if (relatoriosCarregados) {
        return;
    }
    relatoriosCarregados = true;
    setTimeout(() => { relatoriosCarregados = false; }, 1000);

    try {
        await Promise.all([
            carregarVolume(),
            carregarPerformance(),
            carregarDistribuicaoStatus(),
            carregarDistribuicaoCategorias(),
            carregarDistribuicaoGeografica(),
            carregarTempoResolucao()
        ]);
    } catch (error) {
        console.error('Erro na atualizacao:', error);
    }
}

// ============================================
// INICIALIZACAO
// ============================================

let relatoriosTimeout = null;

function atualizarRelatoriosDebounced() {
    if (relatoriosTimeout) {
        clearTimeout(relatoriosTimeout);
    }
    relatoriosTimeout = setTimeout(function() {
        relatoriosCarregados = false;
        atualizarTodosRelatorios();
    }, 500);
}

document.addEventListener('DOMContentLoaded', function () {
    // Definir datas padrao
    const hoje = new Date();
    const mesPassado = new Date();
    mesPassado.setMonth(hoje.getMonth() - 1);

    const dataFimEl = document.getElementById('dataFim');
    const dataInicioEl = document.getElementById('dataInicio');

    if (dataFimEl) dataFimEl.valueAsDate = hoje;
    if (dataInicioEl) dataInicioEl.valueAsDate = mesPassado;

    // Carregar relatorios iniciais
    atualizarTodosRelatorios();

    // Adicionar listeners com debounce
    ['dataInicio', 'dataFim', 'periodo'].forEach(id => {
        const element = document.getElementById(id);
        if (element) {
            element.addEventListener('change', atualizarRelatoriosDebounced);
        }
    });
});

// ============================================
// EXPORTAR GRAFICO (disponivel globalmente)
// ============================================
window.exportarGrafico = function(chartId) {
    try {
        const chart = charts[chartId];
        if (!chart) {
            console.error(`Grafico ${chartId} nao encontrado`);
            return;
        }

        const link = document.createElement('a');
        link.download = `grafico-${chartId}-${new Date().toISOString().slice(0, 10)}.png`;
        link.href = chart.toBase64Image('image/png', 1.0);

        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);

    } catch (error) {
        console.error('Erro ao exportar grafico:', error);
        alert('Erro ao exportar grafico. Por favor, tente novamente.');
    }
};
