import { api } from './api.js';
import { renderer } from './renderer.js';
import { handlers } from './handlers.js';
import { AppState } from './appState.js';

export async function inicializarMunicipios() {
    const select = document.getElementById('municipio');
    if (!select) return;

    try {
        // Assume que api.js tem getMunicipios ou extraímos do Relatório
        const municipios = await api.getMunicipios(); 
        
        municipios.forEach(m => {
            const opt = document.createElement('option');
            opt.value = m['COD. MUNIC'];
            opt.textContent = m['Município'];
            select.appendChild(opt);
        });
    } catch (error) {
        console.error('Erro ao carregar municípios:', error);
    }
}

export async function inicializarRecAdicionais() {
    const container = document.getElementById('lista-rec-adicionais');
    const inputBusca = document.getElementById('search-rec');
    
    if (!container || !inputBusca) return;

    try {
        const dados = await api.getRecomendacoes();
        AppState.adicionais = dados; // Salva no estado global
        // Renderização Inicial
        renderer.renderListaAdicionais(container, AppState.adicionais, AppState.selecionadasAdicionais);
        
        // Listeners delegados aos handlers
        inputBusca.addEventListener('input', handlers.handleBuscaAdicionais);
        container.addEventListener('change', handlers.handleToggleAdicional);
    } catch (error) {
        console.error('Erro ao inicializar recomendações adicionais:', error);
    }
}

export async function inicializarArvoreTemas() {
    const container = document.getElementById('container-arvore');
    if (!container) return;

    try {
        const dados = await api.getTemas();
        AppState.temas = dados; // ESSENCIAL: salva para uso posterior nos handlers
        // Renderiza a estrutura
        container.innerHTML = renderer.renderizarHierarquia(dados);
        
        // Delegação de Evento: o container escuta mudanças nos checkboxes filhos
        container.addEventListener('change', handlers.handleSelecaoMotivo);
    } catch (error) {
        console.error('Erro ao carregar árvore de temas:', error);
    }
}

export async function inicializarTabelas() {
    const checks = document.querySelectorAll('input[name="tabelas"]');
    const modal = document.getElementById('modal-tabelas');
    const btnFechar = document.querySelector('.close-modal');
    const btnConfirmar = document.getElementById('btn-confirmar-tabela');

    if (!checks.length || !modal) return;

    try {
        // Carrega o CSV consolidado para o AppState (usado para popular o modal)
        AppState.dadosMunicipais = await api.getRelatorioConsolidado();
        // 1. Eventos nas checkboxes da tela principal
        checks.forEach(check => {
            check.addEventListener('change', handlers.handleTabelaCheckboxChange);
        });
        // 2. Eventos de fechamento do modal
        if (btnFechar) btnFechar.onclick = handlers.fecharModalTabela;
        
        // Fecha ao clicar fora do conteúdo do modal
        window.addEventListener('click', (e) => {
            if (e.target === modal) handlers.fecharModalTabela();
        });
        // 3. Evento de confirmação de seleção de anos
        if (btnConfirmar) btnConfirmar.onclick = handlers.confirmarSelecaoTabela;

    } catch (e) {
        console.error("❌ Erro ao inicializar tabelas:", e);
    }
}