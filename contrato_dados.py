"""
contrato_dados.py

CONTRATO DE DADOS entre o módulo de CAPTURA (bloco A) e o módulo de
INDICADORES (bloco B).

Um contrato de dados é um acordo sobre a FORMA dos dados que passam de um
módulo para outro. O módulo de captura traduz o formato da fonte (yfinance)
para este formato padrão; o módulo de indicadores só conhece este formato.
Assim, se a fonte mudar, só a captura precisa ser alterada.

Regras do contrato:
  1. Cada empresa é um dicionário com: ticker, nome, setor e anos.
  2. "anos" é um dicionário {ano: {conta: valor}}.
  3. Todos os valores monetários estão em reais (valor bruto, sem milhares
     ou milhões), para nunca misturar unidades entre módulos.
  4. Conta ausente na fonte = None (NUNCA 0). Zero é um valor real
     (uma empresa pode ter estoque zero); None significa "sem dado".
"""

# Contas que TODO ano de TODA empresa deve ter como chave.
# O valor pode ser um número ou None, mas a chave tem de existir.
CONTAS_OBRIGATORIAS = (
    # Balanço patrimonial
    "ativo_circulante",
    "passivo_circulante",
    "estoque",
    "contas_a_receber",
    "fornecedores",
    "ativo_total",
    "passivo_total",    # total de obrigações, SEM o patrimônio líquido
                        # (ativo_total ≈ passivo_total + patrimonio_liquido;
                        # a pequena diferença, quando existe, é a participação
                        # de não controladores, que fica fora das duas contas)
    "patrimonio_liquido",  # patrimônio dos controladores
    # DRE (Demonstração do Resultado do Exercício)
    "receita_liquida",
    "cmv",              # custo da mercadoria vendida
    "lucro_liquido",
)

CAMPOS_EMPRESA = ("ticker", "nome", "setor", "anos")


def validar_empresa(empresa):
    """
    Confere se o dicionário 'empresa' respeita o contrato.

    Levanta ValueError com uma mensagem clara no primeiro problema
    encontrado. Se não levantar nada, o formato está correto.
    """
    # 1) Campos principais da empresa
    for campo in CAMPOS_EMPRESA:
        if campo not in empresa:
            raise ValueError(f"Campo ausente na empresa: '{campo}'")

    # 2) Precisa haver pelo menos um ano de dados
    if not empresa["anos"]:
        raise ValueError("A empresa não tem nenhum ano de dados")

    # 3) Cada ano deve ter todas as contas obrigatórias
    for ano, contas in empresa["anos"].items():
        for conta in CONTAS_OBRIGATORIAS:
            if conta not in contas:
                raise ValueError(f"Ano {ano}: conta ausente '{conta}'")

            valor = contas[conta]
            # Valor válido: número (int/float) ou None.
            # bool é subclasse de int em Python, então é barrado à parte.
            eh_numero = isinstance(valor, (int, float)) and not isinstance(valor, bool)
            if valor is not None and not eh_numero:
                raise ValueError(
                    f"Ano {ano}, conta '{conta}': esperado número ou None, "
                    f"veio {type(valor).__name__}"
                )


# ----------------------------------------------------------------------
# Empresa FICTÍCIA de exemplo, no formato do contrato.
# O bloco B pode usá-la para programar os indicadores sem esperar a
# captura ficar pronta.
# Os números são inventados, mas coerentes:
#   ativo_total = passivo_total + patrimonio_liquido
#   ativo_circulante < ativo_total
# ----------------------------------------------------------------------
EMPRESA_EXEMPLO = {
    "ticker": "EXMP3.SA",
    "nome": "Empresa Exemplo S.A.",
    "setor": "Varejo",
    "anos": {
        2024: {
            # Balanço patrimonial
            "ativo_circulante": 500_000.0,
            "passivo_circulante": 300_000.0,
            "estoque": 120_000.0,
            "contas_a_receber": 90_000.0,
            "fornecedores": 80_000.0,
            "ativo_total": 1_500_000.0,
            "passivo_total": 900_000.0,
            "patrimonio_liquido": 600_000.0,
            # DRE
            "receita_liquida": 2_000_000.0,
            "cmv": 1_200_000.0,
            "lucro_liquido": 150_000.0,
        },
        2023: {
            # Balanço patrimonial
            "ativo_circulante": 460_000.0,
            "passivo_circulante": 290_000.0,
            "estoque": None,  # conta ausente neste ano: None, nunca 0
            "contas_a_receber": 85_000.0,
            "fornecedores": 75_000.0,
            "ativo_total": 1_400_000.0,
            "passivo_total": 880_000.0,
            "patrimonio_liquido": 520_000.0,
            # DRE
            "receita_liquida": 1_800_000.0,
            "cmv": 1_100_000.0,
            "lucro_liquido": 120_000.0,
        },
    },
}


# Teste rápido: python contrato_dados.py
if __name__ == "__main__":
    validar_empresa(EMPRESA_EXEMPLO)
    print("Empresa de exemplo respeita o contrato.")

    # Mostra que um dado fora do contrato é barrado
    quebrada = {"ticker": "X", "nome": "X", "setor": "X",
                "anos": {2024: {"ativo_total": "mil"}}}
    try:
        validar_empresa(quebrada)
    except ValueError as erro:
        print("Erro detectado, como esperado:", erro)
