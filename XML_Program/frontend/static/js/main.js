import * as init from './initializers.js';
import { handlers } from './handlers.js';

document.addEventListener('DOMContentLoaded', async () => {
    try {
        await Promise.all([
            init.inicializarMunicipios(),
            init.inicializarRecAdicionais(),
            init.inicializarArvoreTemas(),
            init.inicializarTabelas()
        ]);
        
        // Vínculo do Botão de Geração
        const btnGerar = document.getElementById('btn-gerar-payload');
        if (btnGerar) {
            btnGerar.addEventListener('click', handlers.gerarPayload);
        }

        console.log("✅ Interface inicializada com sucesso.");
    } catch (error) {
        console.error("❌ Erro na inicialização:", error);
    }
});