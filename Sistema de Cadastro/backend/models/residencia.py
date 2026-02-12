import uuid
from datetime import datetime, timezone

class Residencia:
    def __init__(
        self,
        cep=None,
        logradouro=None,
        numero=None,
        bairro=None,
        cidade=None,
        estado=None,
        id_residencia=None,
        data_criacao=None,
        data_atualizacao=None
    ):
        self.id = id_residencia or str(uuid.uuid4())
        self.cep = self._normalizar_str(cep)
        self.logradouro = self._normalizar_str(logradouro)
        self.numero = self._normalizar_str(numero)
        self.bairro = self._normalizar_str(bairro)
        self.cidade = self._normalizar_str(cidade)
        self.estado = self._normalizar_str(estado)
        
        # Auditoria
        agora = datetime.now(timezone.utc).isoformat()
        self.data_criacao = data_criacao or agora
        self.data_atualizacao = data_atualizacao or agora

    def get_chave_identificadora(self):
        return f"{self.cep}|{self.logradouro}|{self.numero}".upper()

    @staticmethod
    def _normalizar_str(valor):
        if valor is None:
            return None
        return str(valor).strip()

    def to_dict(self):
        return {
            "id": self.id,
            "cep": self.cep,
            "logradouro": self.logradouro,
            "numero": self.numero,
            "bairro": self.bairro,
            "cidade": self.cidade,
            "estado": self.estado,
            "data_criacao": self.data_criacao,
            "data_atualizacao": self.data_atualizacao
        }

    @staticmethod
    def from_dict(dados):
        if not dados:
            return None
        return Residencia(
            id_residencia=dados.get("id"),
            cep=dados.get("cep"),
            logradouro=dados.get("logradouro"),
            numero=dados.get("numero"),
            bairro=dados.get("bairro"),
            cidade=dados.get("cidade"),
            estado=dados.get("estado"),
            data_criacao=dados.get("data_criacao"),
            data_atualizacao=dados.get("data_atualizacao")
        )

    def __eq__(self, other):
        if not isinstance(other, Residencia):
            return False
        return self.get_chave_identificadora() == other.get_chave_identificadora()

    def __repr__(self):
        return f"<Residencia {self.logradouro} | Criado em: {self.data_criacao}>"