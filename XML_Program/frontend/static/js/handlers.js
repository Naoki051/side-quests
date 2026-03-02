// frontend/static/js/handlers.js
import { AppState } from './appState.js';
import { renderer } from './renderer.js';
import { MapTabelas } from './config.js';
import { api } from './api.js';

let ultimaCheckboxAberta = null;

export const handlers = {
    /**
     * Gerencia a seleção/desseleção de um motivo na árvore
     */
    handleSelecaoMotivo(e) {
        if (e.target.name !== 'motivo_selecionado') return;

        const { categoria, assunto } = e.target.dataset;
        const motivoNome = e.target.value;
        const label = e.target.closest('.tree-motivo-label');

        const proximoElemento = label.nextElementSibling;
        if (proximoElemento?.classList.contains('motivo-flags')) {
            proximoElemento.remove();
        }

        if (e.target.checked) {
            // Persiste no AppState
            if (!AppState.motivosSelecionados[categoria]) AppState.motivosSelecionados[categoria] = {};
            if (!AppState.motivosSelecionados[categoria][assunto]) AppState.motivosSelecionados[categoria][assunto] = {};

            AppState.motivosSelecionados[categoria][assunto][motivoNome] = {
                flags: new Set()
            };

            const dadosMotivo = AppState.temas[categoria]?.[assunto]?.Motivos?.[motivoNome];
            if (dadosMotivo?.Flags?.length > 0) {
                const containerFlags = renderer.renderizarContainerFlags(categoria, assunto, motivoNome, dadosMotivo.Flags);

                // Delegação de evento para as flags (usando a referência direta 'handlers')
                containerFlags.addEventListener('change', (event) => {
                    if (event.target.classList.contains('flag-toggle')) {
                        handlers.handleToggleFlag(event);
                    }
                });

                label.after(containerFlags);
            }
        } else {
            // Passamos 'categoria' para o parâmetro que o método chama de 'tema'
            handlers.removerMotivoDoEstado(categoria, assunto, motivoNome);
        }

        handlers.atualizarPainelRecomendacoes();
    },

    handleToggleFlag(e) {
        // Destruturação deve bater com os data-attributes do renderer
        const { categoria, assunto, motivo, flag } = e.target.dataset;

        // Verificando se o item existe no AppState
        const item = AppState.motivosSelecionados[categoria]?.[assunto]?.[motivo];

        if (item) {
            if (e.target.checked) {
                item.flags.add(flag);
                console.log(`✅ Flag [${flag}] adicionada ao motivo: ${motivo}`);
            } else {
                item.flags.delete(flag);
                console.log(`❌ Flag [${flag}] removida do motivo: ${motivo}`);
            }
        } else {
            console.error("⚠️ Erro: Motivo não encontrado no AppState para salvar a flag.", { categoria, assunto, motivo });
        }
    },

    removerMotivoDoEstado(categoria, assunto, motivoNome) {
        if (AppState.motivosSelecionados[categoria]?.[assunto]) {
            delete AppState.motivosSelecionados[categoria][assunto][motivoNome];

            if (Object.keys(AppState.motivosSelecionados[categoria][assunto]).length === 0) {
                delete AppState.motivosSelecionados[categoria][assunto];
            }
            if (Object.keys(AppState.motivosSelecionados[categoria]).length === 0) {
                delete AppState.motivosSelecionados[categoria];
            }
        }
    },

    atualizarPainelRecomendacoes() {
        const containerObrig = document.querySelector('#recomendacoes-obrigatorias .rec-content');
        const containerEsp = document.querySelector('#recomendacoes-especificas .rec-content');

        if (!containerObrig || !containerEsp) return;

        const gerais = new Set();
        const especificas = [];

        document.querySelectorAll('input[name="motivo_selecionado"]:checked').forEach(input => {
            const { categoria, assunto } = input.dataset;
            const motivoNome = input.value;

            const assuntoData = AppState.temas[categoria]?.[assunto];
            if (!assuntoData) return;

            assuntoData.Recomendacoes_Gerais?.forEach(r => gerais.add(r));

            const motivoData = assuntoData.Motivos?.[motivoNome];
            if (motivoData?.Recomendacao_Especifica) {
                especificas.push(motivoData.Recomendacao_Especifica);
            }
        });

        renderer.renderRecomendacoesPainel(containerObrig, [...gerais]);
        renderer.renderRecomendacoesPainel(containerEsp, especificas);
    },

    handleBuscaAdicionais(e) {
        const termo = e.target.value.toLowerCase();
        const container = document.getElementById('lista-rec-adicionais');

        const filtradas = AppState.adicionais.filter(r =>
            r.toLowerCase().includes(termo)
        );

        renderer.renderListaAdicionais(container, filtradas, AppState.selecionadasAdicionais);
    },

    handleToggleAdicional(e) {
        if (e.target.name !== 'rec_adicional') return;
        e.target.checked
            ? AppState.selecionadasAdicionais.add(e.target.value)
            : AppState.selecionadasAdicionais.delete(e.target.value);
    },

    handleTabelaCheckboxChange(e) {
        if (e.target.checked) {
            ultimaCheckboxAberta = e.target;
            handlers.abrirModalConfiguracao(e.target.value); // USAR 'handlers'
        } else {
            delete AppState.tabelasSelecionadas[e.target.value];
        }
    },

    abrirModalConfiguracao(tipo) {
        const codMunic = document.getElementById('municipio').value;
        const modal = document.getElementById('modal-tabelas');

        if (!codMunic) {
            alert("Selecione um município primeiro!");
            if (ultimaCheckboxAberta) ultimaCheckboxAberta.checked = false;
            return;
        }

        const container = document.getElementById('container-tabela-preview');
        const titulo = document.getElementById('modal-titulo');
        titulo.innerText = `Configurar Tabela: ${tipo.toUpperCase()}`;

        const dadosFiltrados = AppState.dadosMunicipais
            .filter(d => String(d['COD. MUNIC']) === String(codMunic))
            .sort((a, b) => parseInt(a['EXERCÍCIO']) - parseInt(b['EXERCÍCIO']));

        container.innerHTML = renderer.renderizarConteudoModalTabela(tipo, dadosFiltrados, MapTabelas[tipo]);
        modal.style.display = "block";
    },

    fecharModalTabela() {
        const modal = document.getElementById('modal-tabelas');
        modal.style.display = "none";
        if (ultimaCheckboxAberta && !AppState.tabelasSelecionadas[ultimaCheckboxAberta.value]) {
            ultimaCheckboxAberta.checked = false;
        }
        ultimaCheckboxAberta = null;
    },

    confirmarSelecaoTabela() {
        const tipo = ultimaCheckboxAberta?.value;
        const codMunic = document.getElementById('municipio').value;
        if (!tipo) return;

        const checksAnos = document.querySelectorAll('.check-ano:checked');
        const anosSelecionados = Array.from(checksAnos).map(i => i.value);

        if (anosSelecionados.length === 0) {
            alert("Selecione pelo menos um ano para incluir.");
            return;
        }

        const dadosSalvos = AppState.dadosMunicipais.filter(d =>
            String(d['COD. MUNIC']) === String(codMunic) &&
            anosSelecionados.includes(String(d['EXERCÍCIO']))
        );

        AppState.tabelasSelecionadas[tipo] = {
            anos: anosSelecionados,
            dados: dadosSalvos
        };

        document.getElementById('modal-tabelas').style.display = "none";
        ultimaCheckboxAberta = null;
    },

    async gerarPayload() {
        console.log("🚀 Iniciando geração da minuta...");
        try {
            // 1. Captura Dados Básicos
            const selectMunic = document.getElementById('municipio');
            const codMunic = selectMunic.value;
            const exercicio = document.getElementById('exercicio').value;
            const numProcesso = document.getElementById('processo_numero').value;

            if (!codMunic || !exercicio) {
                alert("Por favor, preencha o Município e o Exercício.");
                return;
            }

            // 2. Busca dados da Procuradoria (Fix para o erro 500)
            const dadosProcRaw = await api.getProcuradoria(codMunic);
            const dadosProc = dadosProcRaw || {}; // Garante objeto vazio se for null

            // 3. Formata Motivos
            const motivosLimpos = {};
            for (const [cat, assuntos] of Object.entries(AppState.motivosSelecionados)) {
                motivosLimpos[cat] = {};
                for (const [ass, motivos] of Object.entries(assuntos)) {
                    motivosLimpos[cat][ass] = {};
                    for (const [mot, info] of Object.entries(motivos)) {
                        motivosLimpos[cat][ass][mot] = {
                            flags: Array.from(info.flags)
                        };
                    }
                }
            }

            const payload = {
                dados_basicos: {
                    processo: numProcesso || "TC-XXXXXX.000.XX-X",
                    exercicio: exercicio,
                    municipio: selectMunic.options[selectMunic.selectedIndex].text,
                    cod_munic: codMunic
                },
                procuradoria: dadosProc,
                posicionamento: document.querySelector('input[name="posicionamento"]:checked')?.value || "favoravel",
                segue_dipe: document.querySelector('input[name="segue_dipe"]:checked')?.value || "sim",
                acompanhamento: document.querySelector('input[name="acompanhamento"]:checked')?.value || "nao_houve",
                motivos: motivosLimpos,
                recomendacoes_adicionais: Array.from(AppState.selecionadasAdicionais),
                tabelas: AppState.tabelasSelecionadas,
                oficios: Array.from(document.querySelectorAll('input[name="oficio"]:checked')).map(i => i.value)
            };

            // 5. Envia ao Backend e faz o download
            const blob = await api.gerarDocumento(payload);
            if (blob) {
                const url = window.URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.href = url;

                // --- NOVA LÓGICA DE NOME DE ARQUIVO ---
                const exercicio = payload.dados_basicos.exercicio;
                const municipio = payload.dados_basicos.municipio;
                const processo = payload.dados_basicos.processo.replace(/[.-]/g, ''); // Limpa pontos e traços
                const posicionamento = payload.posicionamento.charAt(0).toUpperCase() + payload.posicionamento.slice(1);
                const iniciais = payload.procuradoria['Iniciais Procurador'] || 'XXX';

                // "{exercicio} {municipio} PM {processo} {posicionamento} [{iniciais}].docx"
                const nomeFinal = `${exercicio} ${municipio} PM ${processo} ${posicionamento} [${iniciais}].docx`;

                a.download = nomeFinal;
                // --------------------------------------

                document.body.appendChild(a);
                a.click();
                a.remove();
                window.URL.revokeObjectURL(url);
                console.log(`✅ Download concluído: ${nomeFinal}`);
            }
        } catch (err) {
            console.error("💥 Falha ao gerar payload:", err);
            alert("Ocorreu um erro ao processar os dados da minuta.");
        }
    }
};