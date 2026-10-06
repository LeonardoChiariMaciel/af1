"""
indicadores.py

MÓDULO DE INDICADORES (bloco B).

Recebe os dados no formato do CONTRATO (ver contrato_dados.py) e calcula
os indicadores financeiros de cada ano.

Regras herdadas do contrato:
  - Conta ausente = None. Se uma conta necessária é None, o indicador do
    ano é None ("não disponível"). Nunca se trata None como zero.
  - Divisão por zero também resulta em None.

Famílias de indicadores previstas:
  1. Liquidez           <- implementada neste arquivo
  2. Endividamento      <- implementada neste arquivo
  3. Rentabilidade      <- implementada neste arquivo
  4. Atividade (prazos) <- implementada neste arquivo
"""


def dividir_seguro(numerador, denominador):
    """
    Divide numerador por denominador respeitando as regras do contrato.

    Devolve None se qualquer um dos valores for None (conta ausente)
    ou se o denominador for zero. Todas as fórmulas passam por aqui,
    para que a regra fique em um único lugar.
    """
    if numerador is None or denominador is None:
        return None
    if denominador == 0:
        return None
    return numerador / denominador


# ----------------------------------------------------------------------
# FAMÍLIA 1: LIQUIDEZ
# Pergunta: a empresa consegue pagar as contas de curto prazo?
# ----------------------------------------------------------------------

def liquidez_corrente(contas):
    """
    Liquidez corrente = ativo circulante / passivo circulante.

    Quantos reais de ativo de curto prazo a empresa tem para cada
    R$ 1,00 de dívida de curto prazo. Acima de 1 indica folga.
    """
    return dividir_seguro(contas["ativo_circulante"], contas["passivo_circulante"])


def liquidez_seca(contas):
    """
    Liquidez seca = (ativo circulante - estoque) / passivo circulante.

    Versão mais exigente: desconsidera o estoque, que é o ativo
    circulante mais difícil de converter em dinheiro.
    """
    ativo_circulante = contas["ativo_circulante"]
    estoque = contas["estoque"]

    # Se faltar qualquer uma das duas contas, não dá para calcular.
    # (Não podemos subtrair None, e não vamos assumir estoque = 0.)
    if ativo_circulante is None or estoque is None:
        return None

    return dividir_seguro(ativo_circulante - estoque, contas["passivo_circulante"])


# ----------------------------------------------------------------------
# FAMÍLIA 2: ENDIVIDAMENTO
# Pergunta: quem financia a empresa, ela mesma ou os credores?
# ----------------------------------------------------------------------

def endividamento_geral(contas):
    """
    Endividamento geral = passivo total / ativo total.

    Fração dos ativos da empresa financiada com capital de terceiros.
    Exemplo: 0,60 significa 60% dos ativos financiados por dívidas.
    """
    return dividir_seguro(contas["passivo_total"], contas["ativo_total"])


def divida_sobre_patrimonio(contas):
    """
    Dívida sobre patrimônio = passivo total / patrimônio líquido.

    Quantos reais de capital de terceiros existem para cada R$ 1,00 de
    capital próprio (grau de alavancagem).

    Atenção: se o patrimônio líquido for NEGATIVO, o resultado sai
    negativo. O valor é mantido (é um dado real); a interpretação
    (módulo 5) deverá tratar esse caso à parte.
    """
    return dividir_seguro(contas["passivo_total"], contas["patrimonio_liquido"])


# ----------------------------------------------------------------------
# FAMÍLIA 3: RENTABILIDADE
# Pergunta: quanto lucro a empresa gera?
#
# Os resultados são guardados em FRAÇÃO (0,075 = 7,5%). A conversão para
# porcentagem é feita só na exibição (ver INDICADORES_PERCENTUAIS).
#
# SIMPLIFICAÇÃO: ROA e ROE usam o saldo de FIM DE ANO. Na teoria, usa-se
# a média entre o saldo do início e do fim do ano, mas isso exigiria o
# ano anterior e faria o primeiro ano disponível ficar sem resultado.
# ----------------------------------------------------------------------

# Indicadores que devem ser exibidos como porcentagem no relatório
INDICADORES_PERCENTUAIS = ("margem_liquida", "roa", "roe")


def margem_liquida(contas):
    """
    Margem líquida = lucro líquido / receita líquida.

    De cada R$ 1,00 vendido, quanto sobra de lucro depois de todas as
    despesas. Pode ser negativa (prejuízo).
    """
    return dividir_seguro(contas["lucro_liquido"], contas["receita_liquida"])


def roa(contas):
    """
    ROA (retorno sobre o ativo) = lucro líquido / ativo total.

    Lucro gerado pelos bens e direitos da empresa, não importa se foram
    financiados por dívida ou por capital próprio.
    """
    return dividir_seguro(contas["lucro_liquido"], contas["ativo_total"])


def roe(contas):
    """
    ROE (retorno sobre o patrimônio líquido) = lucro líquido / patrimônio líquido.

    Retorno sobre o capital dos sócios.

    Se o patrimônio líquido for negativo ou zero, devolve None: com
    prejuízo e patrimônio negativos, os dois sinais se anulam e o ROE
    sairia positivo, parecendo um bom desempenho (resultado enganoso).
    """
    patrimonio = contas["patrimonio_liquido"]
    if patrimonio is not None and patrimonio <= 0:
        return None
    return dividir_seguro(contas["lucro_liquido"], patrimonio)


# ----------------------------------------------------------------------
# FAMÍLIA 4: ATIVIDADE (PRAZOS MÉDIOS)
# Pergunta: quantos dias o dinheiro fica parado em cada etapa do negócio?
#
# Simplificações (as mesmas de ROA/ROE, mais uma):
#   - Saldos de FIM DE ANO, não médias.
#   - O prazo de pagamento usa o CMV como base. Na teoria usaria-se as
#     COMPRAS do período, mas essa conta não está nas demonstrações.
# ----------------------------------------------------------------------

# Dias considerados em um ano. Alguns livros usam 360 (ano comercial);
# para trocar a convenção, basta alterar este número.
DIAS_NO_ANO = 365

# Indicadores que devem ser exibidos em dias no relatório
INDICADORES_EM_DIAS = ("pmr", "pme", "pmp", "ciclo_operacional", "ciclo_financeiro")


def _em_dias(razao):
    """Converte uma razão (saldo / base anual) em dias. None continua None."""
    if razao is None:
        return None
    return razao * DIAS_NO_ANO


def pmr(contas):
    """
    Prazo médio de recebimento = contas a receber / receita líquida * dias.

    Em quantos dias, em média, a empresa recebe dos clientes após a venda.
    """
    return _em_dias(dividir_seguro(contas["contas_a_receber"], contas["receita_liquida"]))


def pme(contas):
    """
    Prazo médio de estocagem = estoque / CMV * dias.

    Quantos dias, em média, o produto fica parado até ser vendido.
    """
    return _em_dias(dividir_seguro(contas["estoque"], contas["cmv"]))


def pmp(contas):
    """
    Prazo médio de pagamento = fornecedores / CMV * dias.

    Em quantos dias, em média, a empresa paga seus fornecedores.
    (Usa o CMV como aproximação das compras do período.)
    """
    return _em_dias(dividir_seguro(contas["fornecedores"], contas["cmv"]))


def ciclo_operacional(contas):
    """
    Ciclo operacional = PMR + PME.

    Dias entre comprar a mercadoria e receber pela venda.
    None se qualquer um dos dois prazos não estiver disponível.
    """
    prazo_recebimento = pmr(contas)
    prazo_estocagem = pme(contas)
    if prazo_recebimento is None or prazo_estocagem is None:
        return None
    return prazo_recebimento + prazo_estocagem


def ciclo_financeiro(contas):
    """
    Ciclo financeiro = ciclo operacional - PMP.

    Dias em que a empresa precisa financiar a operação: já pagou o
    fornecedor, mas ainda não recebeu do cliente. Quanto menor, melhor.
    None se qualquer parte não estiver disponível.
    """
    ciclo = ciclo_operacional(contas)
    prazo_pagamento = pmp(contas)
    if ciclo is None or prazo_pagamento is None:
        return None
    return ciclo - prazo_pagamento


# ----------------------------------------------------------------------
# Funções que reúnem os indicadores
# ----------------------------------------------------------------------

def calcular_indicadores_ano(contas):
    """Calcula todos os indicadores de UM ano. Devolve {nome: valor}."""
    return {
        "liquidez_corrente": liquidez_corrente(contas),
        "liquidez_seca": liquidez_seca(contas),
        "endividamento_geral": endividamento_geral(contas),
        "divida_sobre_patrimonio": divida_sobre_patrimonio(contas),
        "margem_liquida": margem_liquida(contas),
        "roa": roa(contas),
        "roe": roe(contas),
        "pmr": pmr(contas),
        "pme": pme(contas),
        "pmp": pmp(contas),
        "ciclo_operacional": ciclo_operacional(contas),
        "ciclo_financeiro": ciclo_financeiro(contas),
    }


def calcular_indicadores(empresa):
    """
    Calcula os indicadores de TODOS os anos da empresa (formato do contrato).

    Devolve {ano: {nome_do_indicador: valor}}, com os anos em ordem
    crescente, o que facilita montar os gráficos de evolução.
    """
    resultado = {}
    for ano in sorted(empresa["anos"]):
        resultado[ano] = calcular_indicadores_ano(empresa["anos"][ano])
    return resultado


def formatar_indicador(nome, valor):
    """
    Devolve o indicador como texto pronto para exibir.

    None vira "não disponível"; percentuais viram "7,5%"-style (ponto
    decimal do Python); prazos viram "36.5 dias"; o resto fica com 2 casas.
    """
    if valor is None:
        return "não disponível"
    if nome in INDICADORES_PERCENTUAIS:
        return f"{valor:.1%}"        # fração -> porcentagem
    if nome in INDICADORES_EM_DIAS:
        return f"{valor:.1f} dias"
    return f"{valor:.2f}"


# Teste rápido: python indicadores.py
if __name__ == "__main__":
    from contrato_dados import EMPRESA_EXEMPLO, validar_empresa

    # Confere o contrato antes de calcular
    validar_empresa(EMPRESA_EXEMPLO)

    for ano, indicadores in calcular_indicadores(EMPRESA_EXEMPLO).items():
        print(f"Ano {ano}:")
        for nome, valor in indicadores.items():
            print(f"  {nome}: {formatar_indicador(nome, valor)}")
