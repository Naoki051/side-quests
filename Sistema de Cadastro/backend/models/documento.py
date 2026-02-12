import uuid

class Documento:

    def __init__(
        self,
        tipo=None,
        valor=None,
        id_documento=None,
        id_pessoa=None # ID da pessoa a quem este documento pertence
    ):
        self.id = id_documento or str(uuid.uuid4())
        self.id_pessoa = id_pessoa # ATRIBUIÇÃO ADICIONADA
        
        # Normalização básica
        self.tipo = self._normalizar_str(tipo).upper() if tipo else None
        self.valor = self._normalizar_str(valor)

    # ==========================================================
    # MÉTODOS DE NEGÓCIO
    # ==========================================================

    def get_chave_identificadora(self):
        return f"{self.tipo}|{self.valor}".upper()

    # ==========================================================
    # UTILITÁRIOS INTERNOS
    # ==========================================================

    @staticmethod
    def _normalizar_str(valor):
        if valor is None:
            return None
        return str(valor).strip()

    # ==========================================================
    # SERIALIZAÇÃO
    # ==========================================================

    def to_dict(self):
        return {
            "id": self.id,
            "id_pessoa": self.id_pessoa, # INCLUÍDO NO DICIONÁRIO
            "tipo": self.tipo,
            "valor": self.valor,
        }

    @staticmethod
    def from_dict(dados):
        if not dados:
            return None

        return Documento(
            id_documento=dados.get("id"),
            id_pessoa=dados.get("id_pessoa"), # RECUPERADO DO DICIONÁRIO
            tipo=dados.get("tipo"),
            valor=dados.get("valor"),
        )

    # ==========================================================
    # COMPARAÇÃO E REPRESENTAÇÃO
    # ==========================================================

    def __eq__(self, other):
        """
        Dois documentos são iguais se tiverem o mesmo tipo e valor.
        """
        if not isinstance(other, Documento):
            return False
        return self.get_chave_identificadora() == other.get_chave_identificadora()

    def __repr__(self):
        return f"<Documento {self.tipo}: {self.valor}>"