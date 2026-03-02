/**
 * Estado Global da Aplicação
 * Centraliza todos os dados carregados e as seleções do usuário.
 */
export const AppState = {
    // --- Dados Brutos (Cache das APIs) ---
    temas: {},                 // Estrutura completa do temas.json
    dadosMunicipais: [],       // Lista de objetos do relatorio_municipal.csv
    adicionais: [],            // Lista de strings de recomendacoes_adicionais.csv
    // --- Seleções do Usuário (O que irá para a Minuta) ---
    /** * Estrutura: { "Tema": { "Assunto": { "Motivo": { flags: Set() } } } }
     */
    motivosSelecionados: {},   
    /**
     * Estrutura: { "iegm": { anos: [], dados: [] }, "creches": { ... } }
     */
    tabelasSelecionadas: {},   
    /**
     * Set de Strings com as recomendações extras escolhidas no buscador
     */
    selecionadasAdicionais: new Set(),
    /**
     * Reinicia as seleções (útil se o usuário trocar de município)
     */
    reset() {
        this.motivosSelecionados = {};
        this.tabelasSelecionadas = {};
        this.selecionadasAdicionais.clear();
        console.log("♻️ Estado de seleção reiniciado.");
    }
};