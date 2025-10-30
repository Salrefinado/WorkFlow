document.addEventListener('DOMContentLoaded', () => {
    
    const board = document.getElementById('workflow-board');
    const uploadButton = document.getElementById('upload-button');
    const fileInput = document.getElementById('zip-upload');
    
    // Templates
    const grupoTemplate = document.getElementById('grupo-template');
    const rowEntradaTemplate = document.getElementById('row-template-entrada');
    const rowProducaoTemplate = document.getElementById('row-template-producao');
    const rowDefaultTemplate = document.getElementById('row-template-default');
    const tarefaTemplate = document.getElementById('tarefa-producao-template');
    const arquivosCellTemplate = document.getElementById('arquivos-cell-template');

    // Mapeamento de cabeçalhos das tabelas por grupo
    const groupHeaders = {
        'Entrada de Orçamentos': ['Orçamento', 'Arquivos', 'Etapa 1', 'Etapa 2'],
        'Visitas e Medidas': ['Orçamento', 'Arquivos', 'Etapa 1 (Visita)', 'Etapa 2 (Visita)'],
        'Linha de Produção': ['Orçamento', 'Arquivos', 'Tarefas de Produção'],
        'Prontos para Instalação': ['Orçamento', 'Arquivos', 'Status'],
        'Standby': ['Orçamento', 'Arquivos', 'Etapa 1', 'Etapa 2'],
        'Instalados': ['Orçamento', 'Arquivos', 'Status']
    };

    /**
     * Carrega todo o workflow da API e renderiza no quadro.
     */
    async function loadWorkflow() {
        try {
            const response = await fetch('/api/workflow');
            if (!response.ok) throw new Error('Falha ao carregar workflow');
            
            const grupos = await response.json();
            board.innerHTML = ''; // Limpa o quadro
            
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
        
        // Adiciona o cabeçalho da tabela
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
        
        if (grupoNome === 'Entrada de Orçamentos' || grupoNome === 'Visitas e Medidas' || grupoNome === 'Standby') {
            return renderRowEntrada(orcamento);
        } else if (grupoNome === 'Linha de Produção') {
            return renderRowProducao(orcamento);
        } else if (grupoNome === 'Prontos para Instalação' || grupoNome === 'Instalados') {
            return renderRowDefault(orcamento);
        }
        return null;
    }

    /**
     * Preenche dados comuns a todas as linhas (Nome, Cliente, Arquivos).
     */
    function preencherDadosComuns(row, orcamento) {
        row.dataset.orcamentoId = orcamento.id;
        row.querySelector('.orc-numero').textContent = orcamento.numero;
        row.querySelector('.orc-cliente').textContent = orcamento.cliente;
        
        // Renderiza a célula de arquivos
        const arquivosCell = row.querySelector('.col-arquivos');
        const arquivosContent = renderArquivosCell(orcamento.arquivos, orcamento.id);
        arquivosCell.appendChild(arquivosContent);
    }

    /**
     * Renderiza a linha para o grupo "Entrada", "Visitas", "Standby".
     */
    function renderRowEntrada(orcamento) {
        const clone = rowEntradaTemplate.content.cloneNode(true);
        const row = clone.querySelector('tr');
        preencherDadosComuns(row, orcamento);

        // Preenche Etapa 1
        row.querySelector('.col-etapa1 .etapa-desc').textContent = orcamento.etapa1_descricao;
        const selectEtapa1 = row.querySelector('.status-select[data-etapa="etapa1"]');
        selectEtapa1.value = orcamento.etapa1_status;
        updateSelectColor(selectEtapa1);
        
        // Preenche Etapa 2
        row.querySelector('.col-etapa2 .etapa-desc').textContent = orcamento.etapa2_descricao;
        const selectEtapa2 = row.querySelector('.status-select[data-etapa="etapa2"]');
        selectEtapa2.value = orcamento.etapa2_status;
        updateSelectColor(selectEtapa2);
        
        return row;
    }
    
    /**
     * Renderiza a linha para o grupo "Linha de Produção".
     */
    function renderRowProducao(orcamento) {
        const clone = rowProducaoTemplate.content.cloneNode(true);
        const row = clone.querySelector('tr');
        preencherDadosComuns(row, orcamento);
        
        // Preenche as tarefas
        const tarefasContainer = row.querySelector('.col-tarefas-producao');
        orcamento.tarefas.forEach(tarefa => {
            const tarefaEl = renderTarefa(tarefa);
            tarefasContainer.appendChild(tarefaEl);
        });
        
        return row;
    }
    
    /**
     * Renderiza a linha para os grupos "Prontos" e "Instalados".
     */
    function renderRowDefault(orcamento) {
        const clone = rowDefaultTemplate.content.cloneNode(true);
        const row = clone.querySelector('tr');
        preencherDadosComuns(row, orcamento);
        
        const statusFinal = row.querySelector('.status-final-text');
        statusFinal.textContent = orcamento.grupo_nome; // Ex: "Prontos para Instalação"
        if (orcamento.grupo_nome === 'Instalados') {
            statusFinal.style.color = 'var(--status-instalado)';
        } else {
            statusFinal.style.color = 'var(--status-producao)';
        }
        
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
        updateSelectColor(selectStatus);
        
        return tarefaDiv;
    }
    
    /**
     * Renderiza o conteúdo da célula de Arquivos (lista + botão de upload).
     */
    function renderArquivosCell(arquivos, orcamentoId) {
        const clone = arquivosCellTemplate.content.cloneNode(true);
        const fileList = clone.querySelector('.file-list');
        
        arquivos.forEach(arquivo => {
            const li = document.createElement('li');
            const a = document.createElement('a');
            a.href = arquivo.url;
            a.textContent = arquivo.nome_arquivo;
            a.target = '_blank';
            li.appendChild(a);
            fileList.appendChild(li);
        });
        
        // Adiciona listener para o upload manual
        const fileUploadInput = clone.querySelector('.manual-file-upload');
        fileUploadInput.dataset.orcamentoId = orcamentoId;
        
        return clone;
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
            if (!response.ok) throw new Error((await response.json()).error);
            
            await loadWorkflow(); // Recarrega o board
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
            
            if (!response.ok) throw new Error((await response.json()).error);
            
            // Recarrega o board para mostrar o novo arquivo
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
    
    /**
     * Lida com a mudança de status de uma Etapa (via <select>).
     */
    async function handleEtapaStatusChange(e) {
        if (!e.target.classList.contains('status-select')) return;
        
        const select = e.target;
        const novoStatus = select.value;
        const etapa = select.dataset.etapa;
        const orcamentoId = select.closest('.monday-row').dataset.orcamentoId;
        const grupoIdAtual = select.closest('.monday-group').dataset.groupId;

        updateSelectColor(select);

        try {
            const response = await fetch(`/api/orcamento/${orcamentoId}/etapa`, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ etapa: etapa, status: novoStatus })
            });
            
            if (!response.ok) throw new Error('Falha ao atualizar status');
            
            const orcamentoAtualizado = await response.json();
            
            // Se o grupo mudou, recarrega o board inteiro para mover o item
            if (orcamentoAtualizado.grupo_id != grupoIdAtual) {
                loadWorkflow();
            }

        } catch (error) {
            console.error('Erro ao atualizar status:', error);
        }
    }
    
    /**
     * Lida com a mudança de status de uma Tarefa de Produção (via <select>).
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
            
            if (!response.ok) throw new Error('Falha ao atualizar status da tarefa');
            
            // O backend agora retorna o Orçamento pai
            const orcamentoAtualizado = await response.json();

            // Se a automação moveu o orçamento para "Prontos", recarrega o board
            if (orcamentoAtualizado.grupo_id != grupoIdAtual) {
                loadWorkflow();
            }

        } catch (error) {
            console.error('Erro ao atualizar status da tarefa:', error);
        }
    }


    // --- Inicialização e Event Listeners ---
    
    uploadButton.addEventListener('click', handleUpload);
    
    // Delegação de eventos (mais eficiente)
    board.addEventListener('change', (e) => {
        handleEtapaStatusChange(e);
        handleTarefaStatusChange(e);
        handleManualFileUpload(e); // Listener para o upload manual
    });

    // Carrega o workflow inicial
    loadWorkflow();
});