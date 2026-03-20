/**
 * Assistente IA - Gestão Interativa
 * Botão no header com chat panel lateral
 */

class AssistenteIA {
    constructor() {
        this.isOpen = false;
        this.isRecording = false;
        this.recognition = null;
        this.messages = [];
        this.sessionId = this.generateUUID();
        this.init();
    }

    generateUUID() {
        return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, function(c) {
            const r = Math.random() * 16 | 0;
            const v = c === 'x' ? r : (r & 0x3 | 0x8);
            return v.toString(16);
        });
    }

    async init() {
        // Verificar se o chat está habilitado nas configurações
        const chatHabilitado = await this.verificarChatHabilitado();
        if (!chatHabilitado) {
            console.log('[Assistente IA] Chat desabilitado nas configurações');
            return;
        }

        this.createHeaderButton();
        this.createChatPanel();
        this.initSpeechRecognition();
        this.attachEventListeners();
    }

    async verificarChatHabilitado() {
        try {
            const response = await fetch('/api/configuracao/ia/chat-status');
            if (response.ok) {
                const data = await response.json();
                console.log('[Assistente IA] Status do chat:', data);
                return data.chat_habilitado === true;
            }
            // Se endpoint nao responder, assume habilitado para teste
            console.log('[Assistente IA] Endpoint nao respondeu, assumindo habilitado');
            return true;
        } catch (error) {
            console.error('[Assistente IA] Erro ao verificar status do chat:', error);
            // Em caso de erro, assume habilitado para que o botao apareca
            return true;
        }
    }

    createHeaderButton() {
        const container = document.getElementById('assistente-ia-container');
        if (!container) {
            console.warn('[Assistente IA] Container não encontrado no header');
            return;
        }

        const button = document.createElement('button');
        button.id = 'assistente-ia-btn';
        button.className = 'assistente-ia-header-btn';
        button.innerHTML = `
            <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor" width="18" height="18">
                <path d="M20.7134 8.12811L20.4668 8.69379C20.2864 9.10792 19.7136 9.10792 19.5331 8.69379L19.2866 8.12811C18.8471 7.11947 18.0555 6.31641 17.0677 5.87708L16.308 5.53922C15.8973 5.35653 15.8973 4.75881 16.308 4.57612L17.0252 4.25714C18.0384 3.80651 18.8442 2.97373 19.2761 1.93083L19.5293 1.31953C19.7058 0.893489 20.2942 0.893489 20.4706 1.31953L20.7238 1.93083C21.1558 2.97373 21.9616 3.80651 22.9748 4.25714L23.6919 4.57612C24.1027 4.75881 24.1027 5.35653 23.6919 5.53922L22.9323 5.87708C21.9445 6.31641 21.1529 7.11947 20.7134 8.12811ZM12 2C6.47715 2 2 6.47715 2 12C2 13.7025 2.42544 15.3056 3.17581 16.7088L2 22L7.29117 20.8242C8.6944 21.5746 10.2975 22 12 22C17.5228 22 22 17.5228 22 12C22 11.5975 21.9762 11.2002 21.9298 10.8094L19.9437 11.0452C19.9809 11.3579 20 11.6765 20 12C20 16.4183 16.4183 20 12 20C10.6655 20 9.38248 19.6745 8.23428 19.0605L7.58075 18.711L4.63416 19.3658L5.28896 16.4192L4.93949 15.7657C4.32549 14.6175 4 13.3345 4 12C4 7.58172 7.58172 4 12 4C12.6919 4 13.3618 4.0876 14 4.25179L14.4983 2.31487C13.6987 2.10914 12.8614 2 12 2ZM9 12H7C7 14.7614 9.23858 17 12 17C14.7614 17 17 14.7614 17 12H15C15 13.6569 13.6569 15 12 15C10.3431 15 9 13.6569 9 12Z"></path>
            </svg>
            <span class="btn-text">Assistente IA</span>
        `;
        container.appendChild(button);
    }

    createChatPanel() {
        const panel = document.createElement('div');
        panel.id = 'assistente-ia-panel';
        panel.className = 'assistente-ia-panel';
        panel.innerHTML = `
            <div class="assistente-ia-header">
                <div class="assistente-ia-header-content">
                    <div class="assistente-ia-avatar">
                        <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor" width="20" height="20">
                            <path d="M20.7134 8.12811L20.4668 8.69379C20.2864 9.10792 19.7136 9.10792 19.5331 8.69379L19.2866 8.12811C18.8471 7.11947 18.0555 6.31641 17.0677 5.87708L16.308 5.53922C15.8973 5.35653 15.8973 4.75881 16.308 4.57612L17.0252 4.25714C18.0384 3.80651 18.8442 2.97373 19.2761 1.93083L19.5293 1.31953C19.7058 0.893489 20.2942 0.893489 20.4706 1.31953L20.7238 1.93083C21.1558 2.97373 21.9616 3.80651 22.9748 4.25714L23.6919 4.57612C24.1027 4.75881 24.1027 5.35653 23.6919 5.53922L22.9323 5.87708C21.9445 6.31641 21.1529 7.11947 20.7134 8.12811ZM12 2C6.47715 2 2 6.47715 2 12C2 13.7025 2.42544 15.3056 3.17581 16.7088L2 22L7.29117 20.8242C8.6944 21.5746 10.2975 22 12 22C17.5228 22 22 17.5228 22 12C22 11.5975 21.9762 11.2002 21.9298 10.8094L19.9437 11.0452C19.9809 11.3579 20 11.6765 20 12C20 16.4183 16.4183 20 12 20C10.6655 20 9.38248 19.6745 8.23428 19.0605L7.58075 18.711L4.63416 19.3658L5.28896 16.4192L4.93949 15.7657C4.32549 14.6175 4 13.3345 4 12C4 7.58172 7.58172 4 12 4C12.6919 4 13.3618 4.0876 14 4.25179L14.4983 2.31487C13.6987 2.10914 12.8614 2 12 2ZM9 12H7C7 14.7614 9.23858 17 12 17C14.7614 17 17 14.7614 17 12H15C15 13.6569 13.6569 15 12 15C10.3431 15 9 13.6569 9 12Z"></path>
                        </svg>
                    </div>
                    <div>
                        <h3>Assistente Inteligente</h3>
                        <p class="assistente-ia-status">Online - Pronto para ajudar</p>
                    </div>
                </div>
                <button class="assistente-ia-close" id="assistente-close-btn">
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <line x1="18" y1="6" x2="6" y2="18"></line>
                        <line x1="6" y1="6" x2="18" y2="18"></line>
                    </svg>
                </button>
            </div>

            <div class="assistente-ia-messages" id="assistente-messages">
                <div class="assistente-ia-welcome" id="assistente-welcome">
                    <div class="assistente-ia-welcome-icon">
                        <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="#667eea" width="48" height="48">
                            <path d="M20.7134 8.12811L20.4668 8.69379C20.2864 9.10792 19.7136 9.10792 19.5331 8.69379L19.2866 8.12811C18.8471 7.11947 18.0555 6.31641 17.0677 5.87708L16.308 5.53922C15.8973 5.35653 15.8973 4.75881 16.308 4.57612L17.0252 4.25714C18.0384 3.80651 18.8442 2.97373 19.2761 1.93083L19.5293 1.31953C19.7058 0.893489 20.2942 0.893489 20.4706 1.31953L20.7238 1.93083C21.1558 2.97373 21.9616 3.80651 22.9748 4.25714L23.6919 4.57612C24.1027 4.75881 24.1027 5.35653 23.6919 5.53922L22.9323 5.87708C21.9445 6.31641 21.1529 7.11947 20.7134 8.12811ZM12 2C6.47715 2 2 6.47715 2 12C2 13.7025 2.42544 15.3056 3.17581 16.7088L2 22L7.29117 20.8242C8.6944 21.5746 10.2975 22 12 22C17.5228 22 22 17.5228 22 12C22 11.5975 21.9762 11.2002 21.9298 10.8094L19.9437 11.0452C19.9809 11.3579 20 11.6765 20 12C20 16.4183 16.4183 20 12 20C10.6655 20 9.38248 19.6745 8.23428 19.0605L7.58075 18.711L4.63416 19.3658L5.28896 16.4192L4.93949 15.7657C4.32549 14.6175 4 13.3345 4 12C4 7.58172 7.58172 4 12 4C12.6919 4 13.3618 4.0876 14 4.25179L14.4983 2.31487C13.6987 2.10914 12.8614 2 12 2ZM9 12H7C7 14.7614 9.23858 17 12 17C14.7614 17 17 14.7614 17 12H15C15 13.6569 13.6569 15 12 15C10.3431 15 9 13.6569 9 12Z"></path>
                        </svg>
                    </div>
                    <h4>Assistente de Gestao Interativa</h4>
                    <p>Posso ajudar com incidencias, relatorios e estatisticas!</p>

                    <div class="assistente-ia-capabilities">
                        <div class="capability-group">
                            <span class="capability-title">Incidencias</span>
                            <span class="capability-items">Consultar, Estatisticas, Por bairro</span>
                        </div>
                        <div class="capability-group">
                            <span class="capability-title">Relatorios</span>
                            <span class="capability-items">Por categoria, Por status, Por periodo</span>
                        </div>
                        <div class="capability-group">
                            <span class="capability-title">Ajuda</span>
                            <span class="capability-items">Como usar o sistema, Duvidas gerais</span>
                        </div>
                    </div>

                    <div class="assistente-ia-quick-actions">
                        <button class="quick-action-btn" data-action="estatisticas">Estatisticas</button>
                        <button class="quick-action-btn" data-action="incidencias_hoje">Incidencias Hoje</button>
                        <button class="quick-action-btn" data-action="bairro_critico">Bairro Critico</button>
                        <button class="quick-action-btn" data-action="ajuda">Ajuda</button>
                    </div>
                </div>
            </div>

            <div class="assistente-ia-footer">
                <div class="assistente-ia-recording" id="assistente-recording" style="display: none;">
                    <div class="recording-animation">
                        <span></span>
                        <span></span>
                        <span></span>
                    </div>
                    <span>Escutando...</span>
                </div>
                <div class="assistente-ia-input-container">
                    <button class="assistente-ia-voice-btn" id="assistente-voice-btn" title="Clique para falar">
                        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                            <path d="M12 1a3 3 0 0 0-3 3v8a3 3 0 0 0 6 0V4a3 3 0 0 0-3-3z"></path>
                            <path d="M19 10v2a7 7 0 0 1-14 0v-2"></path>
                            <line x1="12" y1="19" x2="12" y2="23"></line>
                            <line x1="8" y1="23" x2="16" y2="23"></line>
                        </svg>
                    </button>
                    <input
                        type="text"
                        id="assistente-input"
                        placeholder="Digite ou clique no microfone para falar..."
                        autocomplete="off"
                    />
                    <button class="assistente-ia-send-btn" id="assistente-send-btn">
                        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                            <line x1="22" y1="2" x2="11" y2="13"></line>
                            <polygon points="22 2 15 22 11 13 2 9 22 2"></polygon>
                        </svg>
                    </button>
                </div>
            </div>
        `;
        document.body.appendChild(panel);
    }

    initSpeechRecognition() {
        if ('webkitSpeechRecognition' in window || 'SpeechRecognition' in window) {
            const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
            this.recognition = new SpeechRecognition();
            this.recognition.lang = 'pt-BR';
            this.recognition.continuous = false;
            this.recognition.interimResults = false;

            this.recognition.onresult = (event) => {
                const transcript = event.results[0][0].transcript;
                document.getElementById('assistente-input').value = transcript;
                this.stopRecording();
                this.sendMessage(transcript);
            };

            this.recognition.onerror = (event) => {
                console.error('Erro no reconhecimento de voz:', event.error);
                this.stopRecording();
            };

            this.recognition.onend = () => {
                this.stopRecording();
            };
        }
    }

    attachEventListeners() {
        const btn = document.getElementById('assistente-ia-btn');
        if (btn) {
            btn.addEventListener('click', () => {
                this.togglePanel();
            });
        }

        document.getElementById('assistente-close-btn').addEventListener('click', () => {
            this.closePanel();
        });

        document.getElementById('assistente-voice-btn').addEventListener('click', () => {
            this.toggleRecording();
        });

        document.getElementById('assistente-send-btn').addEventListener('click', () => {
            const input = document.getElementById('assistente-input');
            if (input.value.trim()) {
                this.sendMessage(input.value.trim());
                input.value = '';
            }
        });

        document.getElementById('assistente-input').addEventListener('keypress', (e) => {
            if (e.key === 'Enter' && e.target.value.trim()) {
                this.sendMessage(e.target.value.trim());
                e.target.value = '';
            }
        });

        document.querySelectorAll('.quick-action-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                const action = btn.dataset.action;
                this.handleQuickAction(action);
            });
        });
    }

    togglePanel() {
        this.isOpen = !this.isOpen;
        const panel = document.getElementById('assistente-ia-panel');

        if (this.isOpen) {
            panel.classList.add('open');
            setTimeout(() => {
                document.getElementById('assistente-input').focus();
            }, 300);
        } else {
            panel.classList.remove('open');
        }
    }

    closePanel() {
        this.isOpen = false;
        document.getElementById('assistente-ia-panel').classList.remove('open');
    }

    toggleRecording() {
        if (!this.recognition) {
            alert('Reconhecimento de voz nao disponivel neste navegador.');
            return;
        }

        if (this.isRecording) {
            this.recognition.stop();
        } else {
            this.startRecording();
        }
    }

    startRecording() {
        this.isRecording = true;
        document.getElementById('assistente-recording').style.display = 'flex';
        document.getElementById('assistente-voice-btn').classList.add('recording');

        try {
            this.recognition.start();
        } catch (error) {
            console.error('Erro ao iniciar gravacao:', error);
            this.stopRecording();
        }
    }

    stopRecording() {
        this.isRecording = false;
        document.getElementById('assistente-recording').style.display = 'none';
        document.getElementById('assistente-voice-btn').classList.remove('recording');
    }

    async sendMessage(message) {
        this.addMessage('user', message);
        this.showTypingIndicator();

        try {
            const token = localStorage.getItem('token');

            if (!token) {
                this.hideTypingIndicator();
                this.addMessage('assistant', 'Voce precisa estar autenticado. Faca login novamente.');
                return;
            }

            const response = await fetch('/api/assistente-ia/chat', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${token}`
                },
                body: JSON.stringify({
                    message: message,
                    session_id: this.sessionId
                })
            });

            this.hideTypingIndicator();

            if (response.status === 401) {
                this.addMessage('assistant', 'Sessao expirada. Faca login novamente.');
                return;
            }

            const data = await response.json();

            if (response.ok) {
                this.addMessage('assistant', data.message || data.resposta || 'Processado com sucesso.');
            } else {
                this.addMessage('assistant', data.detail || 'Desculpe, ocorreu um erro. Tente novamente.');
            }
        } catch (error) {
            this.hideTypingIndicator();
            console.error('Erro ao enviar mensagem:', error);
            this.addMessage('assistant', 'Erro de conexao. Verifique sua internet.');
        }
    }

    addMessage(role, content) {
        const messagesContainer = document.getElementById('assistente-messages');

        const welcome = messagesContainer?.querySelector('.assistente-ia-welcome');
        if (welcome) {
            welcome.remove();
        }

        this.messages.push({ role, content });

        const messageDiv = document.createElement('div');
        messageDiv.className = `assistente-ia-message ${role}`;
        messageDiv.innerHTML = `<div class="message-content">${this.formatMessage(content)}</div>`;

        messagesContainer.appendChild(messageDiv);
        this.scrollToBottom();
    }

    formatMessage(content) {
        // Primeiro, limpar o conteudo agressivamente
        let formatted = content.trim();

        // Remover TODOS os espacos e quebras de linha excessivos ANTES de qualquer processamento
        // Isso resolve o problema de muitas linhas vazias vindas do backend
        formatted = formatted
            // Remover linhas que contem apenas espacos
            .replace(/^\s*$/gm, '')
            // Reduzir multiplas quebras de linha para uma
            .replace(/\n{2,}/g, '\n')
            // Remover espacos no inicio de cada linha
            .replace(/^\s+/gm, '');

        // Verificar se contem tabela HTML
        const contemTabelaHTML = /<table/i.test(formatted);

        if (contemTabelaHTML) {
            // Para respostas com tabelas HTML, fazer limpeza especial
            // Remover TUDO antes da tabela exceto texto relevante
            formatted = formatted
                // Remover quebras de linha e espacos dentro e ao redor de tags de tabela
                .replace(/\n\s*(<table)/gi, '$1')
                .replace(/\n\s*(<thead)/gi, '$1')
                .replace(/\n\s*(<tbody)/gi, '$1')
                .replace(/\n\s*(<tr)/gi, '$1')
                .replace(/\n\s*(<th)/gi, '$1')
                .replace(/\n\s*(<td)/gi, '$1')
                .replace(/(<\/table>)\s*\n/gi, '$1')
                .replace(/(<\/thead>)\s*\n/gi, '$1')
                .replace(/(<\/tbody>)\s*\n/gi, '$1')
                .replace(/(<\/tr>)\s*\n/gi, '$1')
                .replace(/(<\/th>)\s*\n/gi, '$1')
                .replace(/(<\/td>)\s*\n/gi, '$1')
                // Remover espacos dentro das celulas
                .replace(/<td>\s+/gi, '<td>')
                .replace(/\s+<\/td>/gi, '</td>')
                .replace(/<th>\s+/gi, '<th>')
                .replace(/\s+<\/th>/gi, '</th>');
        }

        // Converter markdown bold para HTML
        formatted = formatted.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');

        // Converter quebras de linha para <br> EXCETO dentro de tabelas
        if (!contemTabelaHTML) {
            formatted = formatted.replace(/\n/g, '<br>');
        } else {
            // Para conteudo com tabela, processar cada parte separadamente
            const partes = formatted.split(/(<table[\s\S]*?<\/table>)/gi);
            formatted = partes.map(parte => {
                if (/<table/i.test(parte)) {
                    return parte; // Tabela - nao mexer
                } else {
                    // Texto fora da tabela
                    return parte.trim().replace(/\n/g, '<br>');
                }
            }).join('');
        }

        // Limpeza final agressiva de <br> excessivos
        formatted = formatted
            // Qualquer sequencia de 2+ <br> vira apenas 1
            .replace(/(<br\s*\/?>\s*){2,}/gi, '<br>')
            // Remover <br> no inicio
            .replace(/^(<br\s*\/?>)+/i, '')
            // Remover <br> no final
            .replace(/(<br\s*\/?>)+$/i, '')
            // Remover <br> imediatamente antes de tabelas
            .replace(/(<br\s*\/?>\s*)+(<table)/gi, '$2')
            // Remover <br> imediatamente depois de tabelas
            .replace(/(<\/table>)(\s*<br\s*\/?>)+/gi, '$1')
            // Remover espacos entre tags
            .replace(/>\s+</g, '><');

        // Verificar se contem tabela para adicionar links de exportacao
        const contemTabela = this.detectarTabela(content);
        if (contemTabela) {
            formatted += this.gerarLinksExportacao();
        }

        return formatted;
    }

    detectarTabela(content) {
        // Detectar tabelas markdown (linhas com |) ou tabelas HTML
        const temTabelaMarkdown = (content.match(/\|/g) || []).length >= 3;
        const temTabelaHTML = content.includes('<table') || content.includes('<TABLE');
        const temLinhasComTabs = content.split('\n').filter(linha => (linha.match(/\t/g) || []).length >= 2).length >= 2;

        return temTabelaMarkdown || temTabelaHTML || temLinhasComTabs;
    }

    gerarLinksExportacao() {
        return `
            <div class="export-links mt-2">
                <a href="#" onclick="window.assistenteIA.exportarTabelaPDF(this); return false;" class="btn btn-sm btn-outline-primary me-2">
                    <i class="bi bi-file-pdf"></i> Exportar PDF
                </a>
                <a href="#" onclick="window.assistenteIA.exportarTabelaExcel(this); return false;" class="btn btn-sm btn-outline-success">
                    <i class="bi bi-file-excel"></i> Exportar Excel
                </a>
            </div>
        `;
    }

    exportarTabelaPDF(element) {
        // Encontrar a mensagem que contem a tabela
        const messageDiv = element.closest('.assistente-ia-message');
        if (!messageDiv) return;

        const messageContent = messageDiv.querySelector('.message-content');
        if (!messageContent) return;

        // Clonar conteudo sem os botoes de exportacao
        const contentClone = messageContent.cloneNode(true);
        const exportLinks = contentClone.querySelector('.export-links');
        if (exportLinks) exportLinks.remove();

        // Criar janela de impressao
        const printWindow = window.open('', '_blank');
        printWindow.document.write(`
            <!DOCTYPE html>
            <html>
            <head>
                <title>Relatorio - Assistente IA</title>
                <style>
                    body { font-family: Arial, sans-serif; padding: 20px; }
                    table { border-collapse: collapse; width: 100%; margin: 10px 0; }
                    th, td { border: 1px solid #ddd; padding: 8px; text-align: left; }
                    th { background-color: #4a5568; color: white; }
                    tr:nth-child(even) { background-color: #f9f9f9; }
                    h1 { color: #333; font-size: 18px; margin-bottom: 20px; }
                    .header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px; border-bottom: 2px solid #4a5568; padding-bottom: 10px; }
                    .data { color: #666; font-size: 12px; }
                    @media print {
                        body { -webkit-print-color-adjust: exact; print-color-adjust: exact; }
                    }
                </style>
            </head>
            <body>
                <div class="header">
                    <h1>Relatorio - Assistente IA Governa Facil</h1>
                    <span class="data">${new Date().toLocaleString('pt-BR')}</span>
                </div>
                <div class="content">
                    ${contentClone.innerHTML}
                </div>
            </body>
            </html>
        `);
        printWindow.document.close();

        // Esperar carregar e imprimir
        printWindow.onload = function() {
            printWindow.print();
        };
    }

    exportarTabelaExcel(element) {
        // Encontrar a mensagem que contem a tabela
        const messageDiv = element.closest('.assistente-ia-message');
        if (!messageDiv) return;

        const messageContent = messageDiv.querySelector('.message-content');
        if (!messageContent) return;

        // Clonar conteudo sem os botoes de exportacao
        const contentClone = messageContent.cloneNode(true);
        const exportLinks = contentClone.querySelector('.export-links');
        if (exportLinks) exportLinks.remove();

        // Extrair tabela se existir
        let tableHtml = '';
        const table = contentClone.querySelector('table');
        if (table) {
            tableHtml = table.outerHTML;
        } else {
            // Tentar converter texto com | em tabela
            const text = contentClone.innerText;
            tableHtml = this.converterTextoParaTabela(text);
        }

        // Criar arquivo Excel via HTML
        const excelContent = `
            <html xmlns:o="urn:schemas-microsoft-com:office:office" xmlns:x="urn:schemas-microsoft-com:office:excel" xmlns="http://www.w3.org/TR/REC-html40">
            <head>
                <meta charset="UTF-8">
                <!--[if gte mso 9]>
                <xml>
                    <x:ExcelWorkbook>
                        <x:ExcelWorksheets>
                            <x:ExcelWorksheet>
                                <x:Name>Relatorio</x:Name>
                                <x:WorksheetOptions>
                                    <x:DisplayGridlines/>
                                </x:WorksheetOptions>
                            </x:ExcelWorksheet>
                        </x:ExcelWorksheets>
                    </x:ExcelWorkbook>
                </xml>
                <![endif]-->
                <style>
                    table { border-collapse: collapse; }
                    th, td { border: 1px solid #000; padding: 5px; }
                    th { background-color: #4a5568; color: white; font-weight: bold; }
                </style>
            </head>
            <body>
                ${tableHtml || contentClone.innerHTML}
            </body>
            </html>
        `;

        // Download
        const blob = new Blob([excelContent], { type: 'application/vnd.ms-excel;charset=utf-8' });
        const url = URL.createObjectURL(blob);
        const link = document.createElement('a');
        link.href = url;
        link.download = `relatorio_assistente_ia_${new Date().toISOString().split('T')[0]}.xls`;
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        URL.revokeObjectURL(url);
    }

    converterTextoParaTabela(text) {
        const linhas = text.split('\n').filter(l => l.includes('|') || l.includes('\t'));
        if (linhas.length < 2) return '';

        let html = '<table><tbody>';
        linhas.forEach((linha, idx) => {
            const colunas = linha.includes('|') ? linha.split('|').filter(c => c.trim()) : linha.split('\t');
            const tag = idx === 0 ? 'th' : 'td';
            if (idx === 0) html += '<thead><tr>';
            else if (idx === 1 && linhas[0].includes('|')) html += '</thead><tbody><tr>';
            else html += '<tr>';

            colunas.forEach(col => {
                html += `<${tag}>${col.trim()}</${tag}>`;
            });

            html += '</tr>';
        });
        html += '</tbody></table>';
        return html;
    }

    showTypingIndicator() {
        const messagesContainer = document.getElementById('assistente-messages');
        const typingDiv = document.createElement('div');
        typingDiv.className = 'assistente-ia-message assistant typing-indicator';
        typingDiv.id = 'typing-indicator';
        typingDiv.innerHTML = `
            <div class="message-content">
                <div class="typing-dots">
                    <span></span>
                    <span></span>
                    <span></span>
                </div>
            </div>
        `;
        messagesContainer.appendChild(typingDiv);
        this.scrollToBottom();
    }

    hideTypingIndicator() {
        const indicator = document.getElementById('typing-indicator');
        if (indicator) {
            indicator.remove();
        }
    }

    scrollToBottom() {
        const messagesContainer = document.getElementById('assistente-messages');
        messagesContainer.scrollTop = messagesContainer.scrollHeight;
    }

    handleQuickAction(action) {
        const messages = {
            'estatisticas': 'Mostre as estatisticas gerais do sistema',
            'incidencias_hoje': 'Quantas incidencias foram registradas hoje?',
            'bairro_critico': 'Qual o bairro com mais incidencias?',
            'ajuda': 'Como voce pode me ajudar?'
        };

        if (messages[action]) {
            this.sendMessage(messages[action]);
        }
    }
}

// Inicializar quando o DOM estiver pronto
document.addEventListener('DOMContentLoaded', () => {
    window.assistenteIA = new AssistenteIA();
});
