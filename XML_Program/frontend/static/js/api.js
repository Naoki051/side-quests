export const api = {
    /**
     * Busca a lista de todos os municípios (para popular o select inicial)
     */
    async getMunicipios() {
        try {
            const res = await fetch('/api/municipios');
            return await res.json();
        } catch (error) {
            console.error("Erro ao buscar lista de municípios:", error);
            return [];
        }
    },

    /**
     * Busca dados da Procuradoria (CSV) vinculados a um município
     */
    async getProcuradoria(codMunic) {
        try {
            const res = await fetch(`/api/procuradoria/${codMunic}`);
            return await res.json();
        } catch (error) {
            console.error("Erro ao buscar procuradoria:", error);
            return null;
        }
    },

    /**
     * Busca o histórico completo de indicadores (CSV) para o AppState
     * Usado para alimentar os filtros do modal de tabelas.
     */
    async getRelatorioConsolidado() {
        try {
            const res = await fetch(`/api/relatorio-consolidado`);
            return await res.json();
        } catch (error) {
            console.error("Erro ao buscar relatório consolidado:", error);
            return [];
        }
    },

    /**
     * Busca recomendações adicionais (CSV)
     */
    async getRecomendacoes() {
        try {
            const res = await fetch(`/api/recomendacoes`);
            return await res.json();
        } catch (error) {
            console.error("Erro ao buscar recomendações:", error);
            return [];
        }
    },

    /**
     * Busca população e receita de um ano específico (CSV)
     */
    async getDadosEconomicos(exercicio, codMunic) {
        try {
            const res = await fetch(`/api/economico/${exercicio}/${codMunic}`);
            return await res.json();
        } catch (error) {
            console.error("Erro ao buscar dados econômicos:", error);
            return null;
        }
    },

    /**
     * Busca a árvore completa de Temas, Assuntos e Motivos (JSON)
     */
    async getTemas() {
        try {
            const res = await fetch(`/api/temas`);
            return await res.json();
        } catch (error) {
            console.error("Erro ao buscar árvore de temas:", error);
            return {};
        }
    },
    /**
    * Envia o payload completo para o backend e recebe o arquivo .docx
    */
    async gerarDocumento(payload) {
        try {
            const res = await fetch('/api/gerar-minuta', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });
            if (!res.ok) throw new Error("Erro ao gerar documento no servidor.");
            // Retorna o arquivo como um Blob (Binary Large Object)
            return await res.blob();
        } catch (error) {
            console.error("Erro na geração:", error);
            return null;
        }
    }
};