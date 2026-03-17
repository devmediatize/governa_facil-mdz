// relatorios.js - Implementação completa

let charts = {};
document.addEventListener('DOMContentLoaded', function () {
    console.log('Página carregada!');
    atualizarTodosRelatorios(); // Verifique se esta linha existe
});

// Modifique a função atualizarTodosRelatorios
async function atualizarTodosRelatorios() {
    alert('teste');
    console.log('Iniciando atualização dos relatórios');
    try {
        // Um por um para identificar qual está falhando
        await carregarVolume();
        console.log('Volume carregado');

        await carregarPerformance();
        console.log('Performance carregada');

        await carregarDistribuicaoStatus();
        console.log('Status carregado');

        await carregarDistribuicaoCategorias();
        console.log('Categorias carregadas');

        await carregarDistribuicaoGeografica();
        console.log('Geografia carregada');

        await carregarTempoResolucao();
        console.log('Tempo carregado');
    } catch (error) {
        console.error('Erro na atualização:', error);
    }
}

// Função para carregar volume
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

        const ctx = document.getElementById('volumeChart');
        charts.volumeChart = new Chart(ctx, {
            type: 'line',
            data: {
                labels: data.labels,
                datasets: [{
                    label: 'Volume de Incidências',
                    data: data.values,
                    borderColor: chartColors.border[0],
                    backgroundColor: chartColors.background[0],
                    tension: 0.1
                }]
            },
            options: {
                responsive: true,
                plugins: {
                    title: {
                        display: true,
                        text: 'Volume de Incidências por Período'
                    }
                }
            }
        });
    } catch (error) {
        console.error('Erro ao carregar volume:', error);
        throw error;
    }
}

// Função para carregar performance
async function carregarPerformance() {
    try {
        const response = await fetch('/api/relatorios/performance');
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        const data = await response.json();
        console.log('Dados de performance:', data);  // Debug

        // Verificar se os dados estão presentes
        const tempoMedio = data?.tempo_medio_por_categoria || {};
        const labels = Object.keys(tempoMedio);
        const values = Object.values(tempoMedio);

        if (charts.performanceChart) {
            charts.performanceChart.destroy();
        }

        const ctx = document.getElementById('performanceChart');
        if (!ctx) {
            throw new Error('Elemento performanceChart não encontrado');
        }

        charts.performanceChart = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: labels.length ? labels : ['Sem dados'],
                datasets: [{
                    label: 'Tempo Médio (horas)',
                    data: values.length ? values : [0],
                    backgroundColor: chartColors.background,
                    borderColor: chartColors.border,
                    borderWidth: 1
                }]
            },
            options: {
                responsive: true,
                plugins: {
                    title: {
                        display: true,
                        text: `Taxa de Resolução: ${data?.taxa_resolucao || 0}%`
                    }
                },
                scales: {
                    y: {
                        beginAtZero: true,
                        title: {
                            display: true,
                            text: 'Horas'
                        }
                    }
                }
            }
        });
    } catch (error) {
        console.error('Erro ao carregar performance:', error);
        // Mostrar mensagem de erro no gráfico
        const ctx = document.getElementById('performanceChart');
        if (ctx) {
            const div = document.createElement('div');
            div.className = 'alert alert-danger';
            div.textContent = 'Erro ao carregar dados de performance';
            ctx.parentNode.insertBefore(div, ctx);
        }
    }
}

// Inicialização quando a página carregar
document.addEventListener('DOMContentLoaded', function () {
    // Definir datas padrão
    const hoje = new Date();
    const mesPassado = new Date();
    mesPassado.setMonth(hoje.getMonth() - 1);

    document.getElementById('dataFim').valueAsDate = hoje;
    document.getElementById('dataInicio').valueAsDate = mesPassado;

    // Carregar relatórios iniciais
    atualizarTodosRelatorios();

    // Adicionar listeners para atualização automática
    ['dataInicio', 'dataFim', 'periodo'].forEach(id => {
        document.getElementById(id).addEventListener('change', atualizarTodosRelatorios);
    });
});

async function carregarDistribuicaoStatus() {
    try {
        const response = await fetch('/api/relatorios/status');
        const data = await response.json();

        if (charts.statusChart) {
            charts.statusChart.destroy();
        }

        const ctx = document.getElementById('statusChart');
        charts.statusChart = new Chart(ctx, {
            type: 'doughnut',
            data: {
                labels: Object.keys(data.distribuicao),
                datasets: [{
                    data: Object.values(data.distribuicao),
                    backgroundColor: chartColors.background,
                    borderColor: chartColors.border,
                    borderWidth: 1
                }]
            }
        });
    } catch (error) {
        console.error('Erro ao carregar status:', error);
        throw error;
    }
}

async function carregarDistribuicaoCategorias() {
    try {
        console.log('Iniciando carregamento de categorias...'); // Debug

        const response = await fetch('/api/relatorios/tendencias-categoria');
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        const data = await response.json();
        console.log('Dados recebidos:', data); // Debug

        if (!data || !data.categorias || !data.dados) {
            throw new Error('Dados inválidos recebidos da API');
        }

        if (charts.categoriaChart) {
            charts.categoriaChart.destroy();
        }

        const ctx = document.getElementById('categoriaChart');
        if (!ctx) {
            throw new Error('Elemento canvas não encontrado');
        }

        // Criar cores dinâmicas baseadas no número de categorias
        const cores = data.categorias.map((_, index) => {
            const hue = (index * 360) / data.categorias.length;
            return `hsla(${hue}, 70%, 60%, 0.8)`;
        });

        charts.categoriaChart = new Chart(ctx, {
            type: 'pie',
            data: {
                labels: data.categorias,
                datasets: [{
                    data: data.dados,
                    backgroundColor: cores,
                    borderColor: cores.map(cor => cor.replace('0.8', '1')),
                    borderWidth: 1
                }]
            },
            options: {
                responsive: true,
                plugins: {
                    legend: {
                        position: 'right',
                        labels: {
                            padding: 20,
                            font: {
                                size: 12
                            }
                        }
                    },
                    title: {
                        display: true,
                        text: 'Distribuição por Categoria',
                        font: {
                            size: 16
                        }
                    },
                    tooltip: {
                        callbacks: {
                            label: function (context) {
                                const value = context.raw;
                                const total = context.dataset.data.reduce((a, b) => a + b, 0);
                                const percentage = ((value * 100) / total).toFixed(1);
                                return `${context.label}: ${value} (${percentage}%)`;
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
        console.log('Carregando dados geográficos...');
        const response = await fetch('/api/relatorios/geografico');
        const data = await response.json();
        console.log('Dados geográficos recebidos:', data);

        // Garantir que o elemento canvas existe
        const canvas = document.getElementById('geograficoChart');
        if (!canvas) {
            console.error('Canvas não encontrado');
            return;
        }

        // Limpar gráfico existente se houver
        if (charts.geograficoChart) {
            charts.geograficoChart.destroy();
            delete charts.geograficoChart;
        }

        // Transformar os dados
        const labels = Object.keys(data.por_estado);
        const valores = Object.values(data.por_estado);

        // Criar novo gráfico
        const ctx = canvas.getContext('2d');
        charts.geograficoChart = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: labels,
                datasets: [{
                    label: 'Quantidade de Incidências',
                    data: valores,
                    backgroundColor: 'rgba(54, 162, 235, 0.5)',
                    borderColor: 'rgba(54, 162, 235, 1)',
                    borderWidth: 1
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: true,
                plugins: {
                    legend: {
                        display: true,
                        position: 'top'
                    }
                },
                scales: {
                    y: {
                        beginAtZero: true
                    }
                }
            }
        });

    } catch (error) {
        console.error('Erro ao carregar gráfico geográfico:', error);
    }
}

async function carregarTempoResolucao() {
    try {
        const response = await fetch('/api/relatorios/performance');
        const data = await response.json();

        if (charts.tempoChart) {
            charts.tempoChart.destroy();
        }

        const ctx = document.getElementById('tempoChart');
        charts.tempoChart = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: Object.keys(data.tempo_medio_por_categoria),
                datasets: [{
                    label: 'Tempo Médio (horas)',
                    data: Object.values(data.tempo_medio_por_categoria),
                    backgroundColor: chartColors.background,
                    borderColor: chartColors.border,
                    borderWidth: 1
                }]
            }
        });
    } catch (error) {
        console.error('Erro ao carregar tempo de resolução:', error);
        throw error;
    }
}

// function exportarGrafico(chartId) {
//     try {
//         const chart = charts[chartId];
//         if (!chart) {
//             console.error(`Gráfico ${chartId} não encontrado`);
//             return;
//         }

//         // Criar link temporário para download
//         const link = document.createElement('a');
//         link.download = `grafico-${chartId}-${new Date().toISOString().slice(0, 10)}.png`;

//         // Converter o gráfico para imagem
//         link.href = chart.toBase64Image('image/png', 1.0);

//         // Simular clique para iniciar download
//         document.body.appendChild(link);
//         link.click();
//         document.body.removeChild(link);

//     } catch (error) {
//         console.error('Erro ao exportar gráfico:', error);
//         alert('Erro ao exportar gráfico. Por favor, tente novamente.');
//     }
// }

// Cores para os gráficos
const chartColors = {
    background: [
        'rgba(255, 99, 132, 0.2)',
        'rgba(54, 162, 235, 0.2)',
        'rgba(255, 206, 86, 0.2)',
        'rgba(75, 192, 192, 0.2)',
        'rgba(153, 102, 255, 0.2)'
    ],
    border: [
        'rgba(255, 99, 132, 1)',
        'rgba(54, 162, 235, 1)',
        'rgba(255, 206, 86, 1)',
        'rgba(75, 192, 192, 1)',
        'rgba(153, 102, 255, 1)'
    ]
};
