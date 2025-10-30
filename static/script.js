document.addEventListener('DOMContentLoaded', () => {
    
    const board = document.getElementById('workflow-board');
    const uploadButton = document.getElementById('upload-button');
    const fileInput = document.getElementById('zip-upload');
    
    // Templates
    const grupoTemplate = document.getElementById('grupo-template');
    const rowTemplateStatus = document.getElementById('row-template-status');
    const rowTemplateProducao = document.getElementById('row-template-producao');
    const rowTemplateFinal = document.getElementById('row-template-final');
    const tarefaTemplate = document.getElementById('tarefa-producao-template');
    const arquivosCellTemplate = document.getElementById('arquivos-cell-template');

    // PONTO 2: Cabeçalhos atualizados
    const groupHeaders = {
        'Entrada de Orçamento': ['Orçamento', 'Arquivos', 'Status'],
        'Visitas e Medidas': ['Orçamento', 'Arquivos', 'Status', 'Data Visita', 'Responsável'],
        'Projetar': ['Orçamento', 'Arquivos', 'Status'],
        'Linha de Produção': ['Orçamento', 'Arquivos', 'Data Entrada', 'Data Limite', 'Tarefas de Produção'],
        'Prontos': ['Orçamento', 'Arquivos', 'Status', 'Data Pronto', 'Data Instalação', 'Responsável Inst.'],
        'StandBy': ['Orçamento', 'Arquivos', 'Status'],
        'Instalados': ['Orçamento', 'Arquivos', 'Status Final']
    };

    const statusOptionsByGroup = {
        'Entrada de Orçamento': ['Orçamento Aprovado', 'Agendar Visita', 'Visita Agendada', 'Desenhar', 'Produzir', 'Em Produção', 'Aguardando Cliente', 'Aguardando Arq/Eng', 'Aguardando Obra', 'Parado'],
        'Visitas e Medidas': ['Agendar Visita', 'Mandar para Produção', 'Em Produção', 'Instalado'],
        'Projetar': ['Em Desenho', 'Aprovado para Produção', 'StandBy'],
        'Linha de Produção': ['Não Iniciado', 'Iniciou a Produção', 'Fase de Acabamento', 'Aguardando Vidro / Pedra', 'Reforma em Andamento', 'StandBy'],
        'Prontos': ['Agendar Instalação/Entrega', 'Instalação Agendada', 'StandBy', 'Instalado'],
        'StandBy': ['Aguardando Cliente', 'Aguardando Arq/Eng', 'Aguardando Obra', 'Parado', 'Liberado'],
        'Instalados': ['Instalado']
    };
    
    const statusOptionClasses = {
        'Não Iniciado': 'status-option-nao-iniciado',
        'Iniciou a Produção': 'status-option-iniciou',
        'Fase de Acabamento': 'status-option-acabamento',
        'Produção Finalizada': 'status-option-finalizada',
        'Aguardando Vidro / Pedra': 'status-option-aguardando-vidro',
        'Reforma em Andamento': 'status-option-reforma',
        'StandBy': 'status-option-standby-tarefa',
    };

    // Elementos do Modal
    const modalOverlay = document.getElementById('modal-overlay');
    const modalVisita = document.getElementById('modal-visita');
    const modalInstalacao = document.getElementById('modal-instalacao');
    const modalInstalado = document.getElementById('modal-instalado');
    const modalProducao = document.getElementById('modal-producao'); // PONTO 2

    /**
     * Carrega todo o workflow da API e renderiza no quadro.
     */
    async function loadWorkflow() {
        try {
            const response = await fetch('/api/workflow');
            if (!response.ok) throw new Error('Falha ao carregar workflow');
            
            const grupos = await response.json();
            board.innerHTML = '';
            
            grupos.forEach(grupo => {
                const grupoElement = renderGrupo(grupo);
                const tbody = grupoElement.querySelector('.monday-tbody');
                
                grupo.orcamentos.forEach(orcamento => {
                    const rowElement = renderOrcamentoRow(orcamento);
                    if (rowElement) {
                        tbody.appendChild(rowElement);
                    }
                });
                
                board.appendChild(grupoElement);
            });
            
            initDragAndDrop();

        } catch (error) {
            console.error('Erro ao carregar workflow:', error);
        }
    }

    /**
     * Renderiza um único grupo (seção com tabela).
     */
    function renderGrupo(grupo) {
        const clone = grupoTemplate.content.cloneNode(true);
        const grupoSection = clone.querySelector('.monday-group');
        grupoSection.dataset.groupId = grupo.id;
        grupoSection.querySelector('.group-title').textContent = grupo.nome;
        
        const thead = clone.querySelector('.monday-thead');
        const headerRow = document.createElement('tr');
        const headers = groupHeaders[grupo.nome] || ['Orçamento', 'Detalhes'];
        
        headers.forEach(text => {
            const th = document.createElement('th');
            th.textContent = text;
            headerRow.appendChild(th);
        });
        thead.appendChild(headerRow);
        
        return grupoSection;
    }

    /**
     * Roteador: Escolhe qual template de LINHA (TR) usar.
     */
    function renderOrcamentoRow(orcamento) {
        const grupoNome = orcamento.grupo_nome;
        
        if (grupoNome === 'Linha de Produção') {
            return renderRowProducao(orcamento); // PONTO 2: Rota atualizada
        } else if (grupoNome === 'Instalados') {
            return renderRowFinal(orcamento);
        } else if (statusOptionsByGroup[grupoNome]) {
            return renderRowStatus(orcamento); 
        }
        
        console.warn('Nenhum template de linha encontrado para o grupo:', grupoNome);
        return null;
    }

    /**
     * Formata data (YYYY-MM-DD HH:MM ou YYYY-MM-DD) ou retorna '---'
     */
    function formatarData(dataISO, dateOnly = false) {
        if (!dataISO) return '---';
        try {
            const data = new Date(dataISO);
            // Corrige o fuso horário (ISO string é UTC, new Date() converte para local)
            const dataLocal = new Date(data.getUTCFullYear(), data.getUTCMonth(), data.getUTCDate(), data.getUTCHours(), data.getUTCMinutes());
            
            const dia = String(dataLocal.getDate()).padStart(2, '0');
            const mes = String(dataLocal.getMonth() + 1).padStart(2, '0');
            const ano = dataLocal.getFullYear();
            
            if (dateOnly) {
                return `${dia}/${mes}/${ano}`;
            }
            
            const hora = String(dataLocal.getHours()).padStart(2, '0');
            const min = String(dataLocal.getMinutes()).padStart(2, '0');
            return `${dia}/${mes}/${ano} ${hora}:${min}`;
        } catch (e) {
            console.warn("Erro ao formatar data:", dataISO, e);
            // Fallback para datas YYYY-MM-DD
            if (typeof dataISO === 'string' && dataISO.includes('T')) {
                 return dataISO.split('T')[0].split('-').reverse().join('/');
            }
            if (typeof dataISO === 'string' && dataISO.length === 10) {
                 return dataISO.split('-').reverse().join('/');
            }
            return 'Data inválida';
        }
    }
    
    /**
     * Renderiza a célula de arquivos (ÍCONES).
     */
    function renderArquivosCell(arquivos, orcamentoId) {
        const td = document.createElement('td');
        td.className = 'col-arquivos';
        const clone = arquivosCellTemplate.content.cloneNode(true);
        const iconList = clone.querySelector('.file-list-icons');
        
        arquivos.forEach(arquivo => {
            const a = document.createElement('a');
            a.href = arquivo.url;
            a.target = '_blank';
            a.title = arquivo.nome_arquivo;
            
            if (arquivo.nome_arquivo.toLowerCase().endsWith('.pdf')) {
                a.className = 'file-link file-link-pdf';
            } else {
                a.className = 'file-link file-link-other';
            }
            iconList.appendChild(a);
        });
        
        clone.querySelector('.manual-file-upload').dataset.orcamentoId = orcamentoId;
        td.appendChild(clone);
        return td;
    }
    
    /**
     * Renderiza a célula de orçamento (função helper).
     */
    function renderOrcamentoCell(orcamento) {
        const td = document.createElement('td');
        td.className = 'col-orcamento';
        td.innerHTML = `<span class="orc-numero">${orcamento.numero}</span> - <span class="orc-cliente">${orcamento.cliente}</span>`;
        return td;
    }

    /**
     * Renderiza a célula de status (função helper).
     */
    function renderStatusCell(orcamento) {
        const td = document.createElement('td');
        td.className = 'col-status';
        
        const select = document.createElement('select');
        select.className = 'status-select-orcamento';
        
        const options = statusOptionsByGroup[orcamento.grupo_nome] || [];
        options.forEach(optValue => {
            const option = document.createElement('option');
            option.value = optValue;
            option.textContent = optValue;
            if (statusOptionClasses[optValue]) {
                option.className = statusOptionClasses[optValue];
            }
            select.appendChild(option);
        });
        
        select.value = orcamento.status_atual;
        updateSelectColor(select);
        
        td.appendChild(select);
        return td;
    }
    
    /**
     * Renderiza a célula de dados (Data, Responsável, etc)
     */
    function renderDataCell(texto, isDateColumn = false) {
         const td = document.createElement('td');
         td.className = isDateColumn ? 'col-data-date' : 'col-data';
         td.textContent = texto || '---';
         return td;
    }
    
    /**
     * Renderiza a célula de "Data Instalação" (com botão Agendar).
     */
    function renderInstalacaoCell(orcamento) {
        const td = document.createElement('td');
        td.className = 'col-data';
        
        if (orcamento.data_instalacao) {
            td.textContent = formatarData(orcamento.data_instalacao);
        } else {
            const button = document.createElement('button');
            button.className = 'btn-agendar';
            button.textContent = 'Agendar';
            button.dataset.orcamentoId = orcamento.id;
            td.appendChild(button);
        }
        return td;
    }


    /**
     * Renderiza a linha genérica de STATUS (Entrada, Visitas, Projetar, Prontos, StandBy).
     */
    function renderRowStatus(orcamento) {
        const clone = rowTemplateStatus.content.cloneNode(true);
        const row = clone.querySelector('tr');
        row.dataset.orcamentoId = orcamento.id;

        row.appendChild(renderOrcamentoCell(orcamento));
        row.appendChild(renderArquivosCell(orcamento.arquivos, orcamento.id));
        row.appendChild(renderStatusCell(orcamento));
        
        if (orcamento.grupo_nome === 'Visitas e Medidas') {
            row.appendChild(renderDataCell(formatarData(orcamento.data_visita)));
            row.appendChild(renderDataCell(orcamento.responsavel_visita));
        } else if (orcamento.grupo_nome === 'Prontos') {
            row.appendChild(renderDataCell(formatarData(orcamento.data_pronto)));
            row.appendChild(renderInstalacaoCell(orcamento));
            row.appendChild(renderDataCell(orcamento.responsavel_instalacao));
        }
        
        return row;
    }
    
    /**
     * PONTO 2: Renderiza a linha para o grupo "Linha de Produção" (ATUALIZADO).
     */
    function renderRowProducao(orcamento) {
        const clone = rowTemplateProducao.content.cloneNode(true);
        const row = clone.querySelector('tr');
        row.dataset.orcamentoId = orcamento.id;
        
        // Adiciona colunas
        row.appendChild(renderOrcamentoCell(orcamento));
        row.appendChild(renderArquivosCell(orcamento.arquivos, orcamento.id));
        row.appendChild(renderDataCell(formatarData(orcamento.data_entrada_producao, true), true));
        row.appendChild(renderDataCell(formatarData(orcamento.data_limite_producao, true), true));

        // Adiciona a coluna de Tarefas
        const tarefasCell = document.createElement('td');
        tarefasCell.className = 'col-tarefas-producao';
        orcamento.tarefas.forEach(tarefa => {
            const tarefaEl = renderTarefa(tarefa);
            tarefasCell.appendChild(tarefaEl);
        });
        row.appendChild(tarefasCell);
        
        return row;
    }
    
    /**
     * Renderiza a linha para o grupo "Instalados".
     */
    function renderRowFinal(orcamento) {
        const clone = rowTemplateFinal.content.cloneNode(true);
        const row = clone.querySelector('tr');
        row.dataset.orcamentoId = orcamento.id;

        row.appendChild(renderOrcamentoCell(orcamento));
        row.appendChild(renderArquivosCell(orcamento.arquivos, orcamento.id));
        
        const statusCell = document.createElement('td');
        statusCell.className = 'col-status-final';
        statusCell.innerHTML = '<span class="status-final-text" style="color: var(--status-instalado);">Instalado</span>';
        row.appendChild(statusCell);
        
        return row;
    }

    /**
     * Renderiza uma sub-tarefa no cartão de Produção.
     */
    function renderTarefa(tarefa) {
        const clone = tarefaTemplate.content.cloneNode(true);
        const tarefaDiv = clone.querySelector('.tarefa-producao');
        tarefaDiv.dataset.tarefaId = tarefa.id;
        
        tarefaDiv.querySelector('.tarefa-colaborador').textContent = tarefa.colaborador;
        tarefaDiv.querySelector('.tarefa-item').textContent = tarefa.item_descricao;
        
        const selectStatus = tarefaDiv.querySelector('.status-select-tarefa');
        selectStatus.value = tarefa.status;
        
        Array.from(selectStatus.options).forEach(option => {
            if (statusOptionClasses[option.value]) {
                option.className = statusOptionClasses[option.value];
            }
        });
        
        updateSelectColor(selectStatus);
        
        return tarefaDiv;
    }
    
    /**
     * Cuida do upload do .zip inicial.
     */
    async function handleUpload() {
        const file = fileInput.files[0];
        if (!file) return alert('Por favor, selecione um arquivo .zip.');

        const formData = new FormData();
        formData.append('file', file);

        try {
            const response = await fetch('/api/upload', { method: 'POST', body: formData });
            const result = await response.json();
            if (!response.ok) throw new Error(result.error);
            
            await loadWorkflow();
            fileInput.value = ''; 

        } catch (error) {
            console.error('Erro no upload:', error);
            alert(`Erro no upload: ${error.message}`);
        }
    }

    /**
     * Cuida do upload de um arquivo manual em um orçamento existente.
     */
    async function handleManualFileUpload(e) {
        const input = e.target;
        const file = input.files[0];
        const orcamentoId = input.dataset.orcamentoId;
        
        if (!file || !orcamentoId) return;

        const formData = new FormData();
        formData.append('file', file);

        try {
            const response = await fetch(`/api/orcamento/${orcamentoId}/add_file`, {
                method: 'POST',
                body: formData
            });
            
            const result = await response.json();
            if (!response.ok) throw new Error(result.error);
            
            await loadWorkflow();

        } catch (error) {
            console.error('Erro ao anexar arquivo:', error);
            alert(`Erro ao anexar arquivo: ${error.message}`);
        }
    }


    /**
     * Atualiza a cor de fundo de um <select> com base no valor.
     */
    function updateSelectColor(selectElement) {
        selectElement.removeAttribute('value');
        selectElement.setAttribute('value', selectElement.value);
    }
    
    // --- LÓGICA DE MODAIS E ATUALIZAÇÃO DE STATUS ---
    
    // Converte uma data JS para o formato 'YYYY-MM-DD'
    function toInputDate(date) {
        return date.toISOString().split('T')[0];
    }
    
    function showModal(modal) {
        modalOverlay.classList.remove('hidden');
        modal.classList.remove('hidden');
    }
    
    function hideModals() {
        modalOverlay.classList.add('hidden');
        modalVisita.classList.add('hidden');
        modalInstalacao.classList.add('hidden');
        modalInstalado.classList.add('hidden');
        modalProducao.classList.add('hidden');
        
        // Limpa os campos
        document.getElementById('modal-visita-data').value = '';
        document.getElementById('modal-visita-responsavel').value = '';
        document.getElementById('modal-instalacao-data').value = '';
        document.getElementById('modal-instalacao-responsavel').value = '';
        document.getElementById('modal-producao-data-entrada').value = '';
        document.getElementById('modal-producao-data-limite').value = '';
        document.getElementById('modal-producao-dias-manual').value = '';
    }

    function openVisitaModal() {
        return new Promise((resolve, reject) => {
            showModal(modalVisita);
            
            document.getElementById('modal-visita-save').onclick = () => {
                const data = {
                    data_visita: document.getElementById('modal-visita-data').value,
                    responsavel_visita: document.getElementById('modal-visita-responsavel').value
                };
                if (!data.data_visita || !data.responsavel_visita) {
                    return alert('Por favor, preencha a data e o responsável.');
                }
                hideModals();
                resolve(data);
            };
            document.getElementById('modal-visita-cancel').onclick = () => {
                hideModals();
                reject(new Error('Cancelado pelo usuário'));
            };
        });
    }
    
    function openInstalacaoModal() {
         return new Promise((resolve, reject) => {
            showModal(modalInstalacao);
            
            document.getElementById('modal-instalacao-save').onclick = () => {
                const data = {
                    data_instalacao: document.getElementById('modal-instalacao-data').value,
                    responsavel_instalacao: document.getElementById('modal-instalacao-responsavel').value
                };
                 if (!data.data_instalacao || !data.responsavel_instalacao) {
                    return alert('Por favor, preencha a data e o responsável.');
                }
                hideModals();
                resolve(data);
            };
            document.getElementById('modal-instalacao-cancel').onclick = () => {
                hideModals();
                reject(new Error('Cancelado pelo usuário'));
            };
        });
    }
    
    function openInstaladoModal() {
        return new Promise((resolve, reject) => {
            showModal(modalInstalado);
            
            document.getElementById('modal-instalado-etapa1').onclick = () => {
                hideModals();
                resolve({ etapa_instalada: 'Etapa 1' });
            };
            document.getElementById('modal-instalado-etapa2').onclick = () => {
                hideModals();
                resolve({ etapa_instalada: 'Etapa 2' });
            };
            document.getElementById('modal-instalado-cancel').onclick = () => {
                hideModals();
                reject(new Error('Cancelado pelo usuário'));
            };
        });
    }

    /**
     * PONTO 2: Novo Modal para Datas de Produção
     */
    function openProducaoModal() {
        return new Promise((resolve, reject) => {
            showModal(modalProducao);

            const dataEntradaEl = document.getElementById('modal-producao-data-entrada');
            const dataLimiteEl = document.getElementById('modal-producao-data-limite');
            const diasManualEl = document.getElementById('modal-producao-dias-manual');
            const quickDayButtons = modalProducao.querySelectorAll('.modal-quick-days button');

            // Define a data de entrada como hoje
            const hoje = new Date();
            dataEntradaEl.value = toInputDate(hoje);

            // Função para calcular data limite
            const calcularLimite = (dias) => {
                if (!dataEntradaEl.value || !dias) return;
                const entrada = new Date(dataEntradaEl.value + "T00:00:00"); // Garante fuso local
                entrada.setDate(entrada.getDate() + parseInt(dias));
                dataLimiteEl.value = toInputDate(entrada);
            };

            // Listeners
            quickDayButtons.forEach(btn => {
                btn.onclick = () => {
                    diasManualEl.value = ''; // Limpa manual
                    calcularLimite(btn.dataset.dias);
                };
            });
            
            diasManualEl.oninput = () => {
                calcularLimite(diasManualEl.value);
            };
            
            dataEntradaEl.onchange = () => {
                 calcularLimite(diasManualEl.value || 30); // Recalcula se a entrada mudar
            };

            // Ações do Modal
            document.getElementById('modal-producao-save').onclick = () => {
                const data = {
                    data_entrada: dataEntradaEl.value,
                    data_limite: dataLimiteEl.value
                };
                if (!data.data_entrada || !data.data_limite) {
                    return alert('Por favor, defina a data de entrada e a data limite.');
                }
                hideModals();
                resolve(data);
            };
            document.getElementById('modal-producao-cancel').onclick = () => {
                hideModals();
                reject(new Error('Cancelado pelo usuário'));
            };
        });
    }


    /**
     * Envia a atualização de status para o backend.
     */
    async function updateStatus(orcamentoId, novoStatus, dados_adicionais = {}) {
        try {
            const response = await fetch(`/api/orcamento/${orcamentoId}/status`, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ 
                    novo_status: novoStatus,
                    dados_adicionais: dados_adicionais 
                })
            });
            
            const result = await response.json();
            if (!response.ok) throw new Error(result.error);
            
            await loadWorkflow();

        } catch (error) {
            console.error('Erro ao atualizar status:', error);
            alert(`Erro: ${error.message}`);
            await loadWorkflow();
        }
    }

    /**
     * Lida com a mudança de status de um ORÇAMENTO (via <select>).
     */
    async function handleOrcamentoStatusChange(e) {
        if (!e.target.classList.contains('status-select-orcamento')) return;
        
        const select = e.target;
        const novoStatus = select.value;
        const orcamentoId = select.closest('.monday-row').dataset.orcamentoId;

        updateSelectColor(select);
        
        try {
            let dados_adicionais = {};
            
            if (novoStatus === 'Visita Agendada') {
                dados_adicionais = await openVisitaModal();
            } else if (novoStatus === 'Instalação Agendada') {
                dados_adicionais = await openInstalacaoModal();
            } else if (novoStatus === 'Instalado') {
                dados_adicionais = await openInstaladoModal();
            } 
            // PONTO 2: Checa se está movendo para produção
            else if (['Em Produção', 'Aprovado para Produção'].includes(novoStatus)) {
                dados_adicionais = await openProducaoModal();
            }
            
            await updateStatus(orcamentoId, novoStatus, dados_adicionais);

        } catch (error) {
            if (error.message === 'Cancelado pelo usuário') {
                console.log('Operação cancelada.');
                loadWorkflow();
            } else {
                console.error('Erro no fluxo de atualização:', error);
            }
        }
    }
    
    /**
     * Lida com a mudança de status de uma TAREFA de Produção (via <select>).
     */
    async function handleTarefaStatusChange(e) {
        if (!e.target.classList.contains('status-select-tarefa')) return;
        
        const select = e.target;
        const novoStatus = select.value;
        const tarefaId = select.closest('.tarefa-producao').dataset.tarefaId;
        const grupoIdAtual = select.closest('.monday-group').dataset.groupId;

        updateSelectColor(select);

        try {
            const response = await fetch(`/api/tarefa/${tarefaId}/status`, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ status: novoStatus })
            });
            
            const result = await response.json();
            if (!response.ok) throw new Error(result.error);
            
            if (result.grupo_id != grupoIdAtual) {
                loadWorkflow();
            }
            
            if (novoStatus === 'StandBy') {
                 await updateStatus(result.id, 'StandBy');
            }

        } catch (error) {
            console.error('Erro ao atualizar status da tarefa:', error);
        }
    }
    
    
    // --- LÓGICA DE DRAG & DROP ---
    
    /**
     * Inicializa o Sortable.js em todos os TBODYs
     */
    function initDragAndDrop() {
        const tbodys = document.querySelectorAll('.monday-tbody');
        tbodys.forEach(tbody => {
            new Sortable(tbody, {
                group: 'workflow-board',
                animation: 150,
                handle: '.monday-row',
                ghostClass: 'sortable-ghost',
                chosenClass: 'sortable-chosen',
                onEnd: async (evt) => { // PONTO 2: Tornou-se async
                    const orcamentoId = evt.item.dataset.orcamentoId;
                    const novoGrupoId = evt.to.closest('.monday-group').dataset.groupId;
                    const grupoAntigoId = evt.from.closest('.monday-group').dataset.groupId;
                    
                    if (novoGrupoId !== grupoAntigoId) {
                        
                        let dados_adicionais = {};
                        
                        // PONTO 2: Checa se o destino é "Linha de Produção"
                        const grupoDestinoEl = evt.to.closest('.monday-group').querySelector('.group-title');
                        const grupoNome = grupoDestinoEl.textContent;

                        if (grupoNome === 'Linha de Produção') {
                            try {
                                dados_adicionais = await openProducaoModal();
                            } catch (e) {
                                // Cancelou o modal, reverte o drag
                                console.log('Movimentação cancelada.');
                                loadWorkflow(); // Recarrega para reverter
                                return;
                            }
                        }
                        
                         handleManualMove(orcamentoId, novoGrupoId, dados_adicionais);
                    }
                }
            });
        });
    }
    
    /**
     * PONTO 2: Atualizado para enviar dados adicionais (datas)
     */
    async function handleManualMove(orcamentoId, novoGrupoId, dados_adicionais = {}) {
        try {
            const body = { 
                novo_grupo_id: novoGrupoId, 
                ...dados_adicionais 
            };
            
            const response = await fetch(`/api/orcamento/${orcamentoId}/move`, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(body)
            });
            
            const result = await response.json();
            if (!response.ok) throw new Error(result.error);
            
            await loadWorkflow();
            
        } catch (error) {
             console.error('Erro ao mover orçamento:', error);
             alert(`Erro ao mover: ${error.message}`);
             loadWorkflow();
        }
    }


    // --- Inicialização e Event Listeners ---
    
    uploadButton.addEventListener('click', handleUpload);
    
    // Delegação de eventos
    board.addEventListener('change', (e) => {
        handleOrcamentoStatusChange(e);
        handleTarefaStatusChange(e);
        handleManualFileUpload(e);
    });
    
    board.addEventListener('click', async (e) => {
        if (e.target.classList.contains('btn-agendar')) {
            const orcamentoId = e.target.dataset.orcamentoId;
            try {
                const dados_adicionais = await openInstalacaoModal();
                await updateStatus(orcamentoId, 'Instalação Agendada', dados_adicionais);
            } catch (error) {
                 if (error.message === 'Cancelado pelo usuário') {
                    console.log('Agendamento cancelado.');
                 } else {
                    console.error('Erro no agendamento:', error);
                 }
            }
        }
    });

    modalOverlay.addEventListener('click', () => {
        // Não fecha
    });

    loadWorkflow();
});
