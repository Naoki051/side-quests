// frontend/static/js/renderer.js
export const renderer = {
    /**
     * Transforma o JSON de Temas em uma árvore de <details> e checkboxes
     */
    renderizarHierarquia(dados) {
        let html = '';
        for (const [categoria, assuntos] of Object.entries(dados)) {
            html += `<details class="tree-categoria">
                    <summary><strong>${categoria}</strong></summary>
                    <div class="tree-content">`;

            for (const [assunto, info] of Object.entries(assuntos)) {
                html += `<details class="tree-assunto">
                        <summary>${assunto}</summary>
                        <ul class="tree-motivos-list">`;

                const motivos = info.Motivos || {};
                for (const motivo in motivos) {
                    html += `<li>
                            <label class="tree-motivo-label">
                                <input type="checkbox" name="motivo_selecionado" 
                                       data-categoria="${categoria}"  data-assunto="${assunto}" 
                                       value="${motivo}">
                                <span>${motivo}</span>
                            </label>
                         </li>`;
                }
                html += `</ul></details>`;
            }
            html += `</div></details>`;
        }
        return html;
    },
    /**
     * Renderiza o container de flags (switches) para um motivo selecionado
     */
    renderizarContainerFlags(tema, assunto, motivoNome, flags) {
        const containerFlags = document.createElement('div');
        containerFlags.className = 'motivo-flags';

        containerFlags.innerHTML = flags.map(flagRaw => {
            const nomeLimpo = flagRaw.replace(/[()]/g, '');
            return `
                <label class="flag-label">
                    <span class="switch">
                        <input type="checkbox" class="flag-toggle" 
                               data-categoria="${tema}" 
                               data-assunto="${assunto}" 
                               data-motivo="${motivoNome}" 
                               data-flag="${nomeLimpo}">
                        <span class="slider"></span>
                    </span>
                    ${nomeLimpo}
                </label>
            `;
        }).join('');

        return containerFlags;
    },

    /**
     * Renderiza as recomendações nos painéis de exibição (Obrigatórias/Específicas)
     */
    renderRecomendacoesPainel(container, lista) {
        if (!container) return;
        container.innerHTML = lista.length
            ? lista.map(t => `<div class="rec-item">${t}</div>`).join('')
            : '<em style="color:#ccc;font-size:.8rem;">Nenhuma recomendação aplicável.</em>';
    },

    /**
     * Renderiza a lista de Recomendações Adicionais com suporte a estado (checked)
     */
    renderListaAdicionais(container, lista, selecionadas) {
        if (!container) return;
        container.innerHTML = lista.map((rec, i) => `
            <div class="rec-item-add">
                <input 
                    type="checkbox" 
                    name="rec_adicional" 
                    id="add_${i}" 
                    value="${rec}"
                    ${selecionadas.has(rec) ? 'checked' : ''}
                >
                <label for="add_${i}">${rec}</label>
            </div>
        `).join('');
    },
    /**
     * Gera o HTML para a tabela de visualização no modal
     */
    renderizarConteudoModalTabela(tipo, dadosFiltrados, configColunas) {
        if (dadosFiltrados.length === 0) {
            return `<p class="error-box">Nenhum dado histórico encontrado para este município.</p>`;
        }

        if (tipo === 'iegm') {
            return this._renderIEGMTransposto(dadosFiltrados, configColunas);
        } else {
            return this._renderTabelaPadrao(dadosFiltrados, configColunas);
        }
    },

    _renderIEGMTransposto(dados, colunas) {
        const indicadores = colunas.filter(c => c !== 'EXERCÍCIO');
        let html = `<table class="table-transposed"><thead><tr><th>Indicador</th>`;

        dados.forEach(row => {
            const ano = row['EXERCÍCIO'];
            html += `<th><label><input type="checkbox" class="check-ano" value="${ano}" checked> Incluir ${ano}</label></th>`;
        });

        html += `</tr></thead><tbody>`;
        indicadores.forEach(ind => {
            html += `<tr><td><strong>${ind.toUpperCase()}</strong></td>`;
            dados.forEach(row => {
                const notaClass = (row[ind] || '').replace('+', 'plus').toLowerCase();
                html += `<td class="nota-${notaClass}">${row[ind] || '-'}</td>`;
            });
            html += `</tr>`;
        });
        return html + `</tbody></table>`;
    },

    _renderTabelaPadrao(dados, colunas) {
        let html = `<table><thead><tr><th>Incluir</th>${colunas.map(c => `<th>${c}</th>`).join('')}</tr></thead><tbody>`;

        dados.forEach(row => {
            html += `<tr>
                <td><input type="checkbox" class="check-ano" value="${row['EXERCÍCIO']}" checked></td>
                ${colunas.map(col => {
                const val = row[col];
                const formatado = (col.toLowerCase().includes('receita') || col.toLowerCase().includes('resultado'))
                    ? `R$ ${Number(val).toLocaleString('pt-BR', { minimumFractionDigits: 2 })}`
                    : (val || '-');
                return `<td>${formatado}</td>`;
            }).join('')}
            </tr>`;
        });
        return html + `</tbody></table>`;
    }
};