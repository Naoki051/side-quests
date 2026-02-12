import uuid
from datetime import datetime, timezone

class Pessoa:
    def __init__(
        self, 
        nome=None, 
        celular=None, 
        data_nascimento=None, 
        id_pessoa=None, 
        id_responsavel=None, 
        parentesco=None, 
        id_residencia=None,
        data_criacao=None,
        data_atualizacao=None
    ):
        self.id = id_pessoa or str(uuid.uuid4())
        self.nome = self._normalizar_str(nome)
        self.celular = self._normalizar_str(celular)
        self.data_nascimento = self._normalizar_str(data_nascimento)
        self.id_responsavel = id_responsavel
        self.parentesco = self._normalizar_str(parentesco)
        self.id_residencia = id_residencia
        
        # Auditoria: Se não houver data (novo cadastro), gera o timestamp atual
        agora = datetime.now(timezone.utc).isoformat()
        self.data_criacao = data_criacao or agora
        self.data_atualizacao = data_atualizacao or agora

    @staticmethod
    def _normalizar_str(valor):
        if valor is None:
            return None
        return str(valor).strip()

    def to_dict(self):
        return {
            "id": self.id,
            "nome": self.nome,
            "celular": self.celular,
            "data_nascimento": self.data_nascimento,
            "id_responsavel": self.id_responsavel,
            "parentesco": self.parentesco,
            "id_residencia": self.id_residencia,
            "data_criacao": self.data_criacao,
            "data_atualizacao": self.data_atualizacao
        }

    @staticmethod
    def from_dict(dados):
        if not dados:
            return None
        return Pessoa(
            id_pessoa=dados.get("id"),
            nome=dados.get("nome"),
            celular=dados.get("celular"),
            data_nascimento=dados.get("data_nascimento"),
            id_responsavel=dados.get("id_responsavel"),
            parentesco=dados.get("parentesco"),
            id_residencia=dados.get("id_residencia"),
            data_criacao=dados.get("data_criacao"),
            data_atualizacao=dados.get("data_atualizacao")
        )

    def __eq__(self, other):
        if not isinstance(other, Pessoa):
            return False
        return self.id == other.id

    def __repr__(self):
        return f"<Pessoa {self.nome} | Atualizado em: {self.data_atualizacao}>"